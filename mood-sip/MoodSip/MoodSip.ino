#include "camera.h"
#include "gc2145.h"
#include "lib_zant.h"
#include <Arduino.h>
#include <ArduinoBLE.h>
#include <Arduino_LSM6DSOX.h>
#include <math.h>
#include <stdint.h>
#include <string.h>

// ================= TIMER DINAMICO ==================
unsigned long baseTimer = 3600000UL;    // timer iniziale: 60 minuti
unsigned long dynamicTimer = baseTimer; // timer modificabile
unsigned long lastTimerUpdate = 0;      // tempo ultima modifica

bool gyroActive = false;
unsigned long gyroChangeStart = 0;

// ================= BLE ==================
BLEService grayService("12345678-1234-5678-1234-56789abcdef0");

BLECharacteristic grayChar("abcdef01-1234-5678-1234-56789abcdef0",
                           BLERead | BLENotify,
                           96 * 96); // frame grayscale

BLECharacteristic commandChar("abcdef02-1234-5678-1234-56789abcdef0",
                              BLEWrite | BLEWriteWithoutResponse,
                              1); // comando da PWA: 0 o 1

bool isBleConnected = false;

// ================= Temperatura ==================
unsigned long lastTempMillis = 0;
const unsigned long TEMP_INTERVAL = 3600000UL; // 60 minuti in millisecondi

// ================= Config ==================
#define BAUD 921600
#define THR 0.60f
#define RGB565_IS_MSB_FIRST 1 // 1: big-endian (MSB-first), 0: little-endian
#define STREAM_TO_PC                                                           \
  0 // 1: stream binario compatibile con viewer Python, 0: solo log

// ================= Modello (NCHW) ==================
static const uint32_t N = 1, C = 3, H = 96, W = 96; // input RGB channels-first
static const uint32_t CLASSES = 2;                  // COCO80
static uint32_t inputShape[4] = {N, C, H, W};       // NCHW

// ================= Buffers ==================
alignas(32) static float gInput[N * C * H * W]; // Input normalizzato 0..1
static uint8_t gGray8[W * H]; // anteprima in GRAY8 (non normalizzata)

// ================= Camera ==================
GC2145 sensor;
Camera cam(sensor);
FrameBuffer fb;

// ================= ZANT hooks (deboli) ==================
extern "C" void setLogFunction(void (*logger)(char *)) __attribute__((weak));
extern "C" void zant_free_result(float *) __attribute__((weak));
extern "C" void zant_init_weights_io(void) __attribute__((weak));
extern "C" void zant_set_weights_base_address(const uint8_t *)
    __attribute__((weak));
extern "C" void zant_register_weight_callback(int (*cb)(size_t, uint8_t *,
                                                        size_t))
    __attribute__((weak));
extern "C" __attribute__((used)) const uint8_t *flash_weights_base =
    (const uint8_t *)0x90000000u;

// ================= QSPI / HAL ==================
extern "C" {
#ifndef STM32H747xx
#define STM32H747xx
#endif
#ifndef HAL_QSPI_MODULE_ENABLED
#define HAL_QSPI_MODULE_ENABLED
#endif
#include "stm32h7xx_hal.h"
#include "stm32h7xx_hal_qspi.h"
}
static QSPI_HandleTypeDef hqspi;

// ================= Comandi NOR ==================
static const uint8_t CMD_RDSR1 = 0x05;
static const uint8_t CMD_RDSR2 = 0x35;
static const uint8_t CMD_WRSR = 0x01;
static const uint8_t CMD_WREN = 0x06;
static const uint8_t CMD_READ_QO = 0x6B; // Quad Output Fast Read

// ================= BLE global variables ==================
enum BleState {
  IDLE,    // no BLE command pending
  WAIT_CMD // waiting for a BLE command
};

BleState bleState = IDLE; // stato iniziale BLE
int clsWaiting = -1;      // classe in attesa

void onBleConnect(BLEDevice central) {
  isBleConnected = true;
  Serial.print("[BLE] Connesso a: ");
  Serial.println(central.address());

  // LED blu acceso per indicare connessione
  digitalWrite(LEDB, HIGH);
}

void onBleDisconnect(BLEDevice central) {
  isBleConnected = false;
  Serial.print("[BLE] Disconnesso da: ");
  Serial.println(central.address());

  // LED blu spento
  digitalWrite(LEDB, LOW);

  // Reset stato
  bleState = IDLE;
  clsWaiting = -1;
}

// ================= COCO80 ==================
static const char *COCO80[CLASSES] = {"background", "humans"};

// ================= Helper colore ==================
static inline uint16_t load_rgb565_BE(const uint8_t *S2, int idx) {
  return (uint16_t)((S2[2 * idx] << 8) | S2[2 * idx + 1]);
}
static inline uint16_t load_rgb565_LE(const uint8_t *S2, int idx) {
  return (uint16_t)((S2[2 * idx + 1] << 8) | S2[2 * idx]);
}
static inline void rgb565_to_rgb888_u16(uint16_t v, uint8_t &R, uint8_t &G,
                                        uint8_t &B) {
  uint8_t r5 = (v >> 11) & 0x1F, g6 = (v >> 5) & 0x3F, b5 = v & 0x1F;
  R = (uint8_t)((r5 << 3) | (r5 >> 2));
  G = (uint8_t)((g6 << 2) | (g6 >> 4));
  B = (uint8_t)((b5 << 3) | (b5 >> 2));
}
static inline uint8_t clamp_u8(float x) {
  if (x <= 0.f)
    return 0;
  if (x >= 255.f)
    return 255;
  return (uint8_t)lrintf(x);
}
static inline int clampi(int v, int lo, int hi) {
  if (v < lo)
    return lo;
  if (v > hi)
    return hi;
  return v;
}

// ================= Resize → NCHW + Gray ==================
static void
resize_rgb565_to_96x96_rgbNCHW_and_gray_NEAREST(const uint8_t *src, int sw,
                                                int sh, float *__restrict dst_f,
                                                uint8_t *__restrict dst_gray) {
  const float sx = (float)sw / (float)W;
  const float sy = (float)sh / (float)H;
  const float inv255 = 1.0f / 255.0f;

  const int plane = (int)(H * W);
  float *__restrict dstR = dst_f + 0 * plane;
  float *__restrict dstG = dst_f + 1 * plane;
  float *__restrict dstB = dst_f + 2 * plane;

  for (int y = 0; y < (int)H; ++y) {
    int ys = clampi((int)floorf((y + 0.5f) * sy), 0, sh - 1);
    for (int x = 0; x < (int)W; ++x) {
      int xs = clampi((int)floorf((x + 0.5f) * sx), 0, sw - 1);
      int si = ys * sw + xs;

      uint16_t v = RGB565_IS_MSB_FIRST ? load_rgb565_BE(src, si)
                                       : load_rgb565_LE(src, si);
      uint8_t r, g, b;
      rgb565_to_rgb888_u16(v, r, g, b);

      const int di = y * W + x;
      dstR[di] = ((float)r - 123.675f) / 58.395f;
      dstG[di] = ((float)g - 116.28f) / 57.12f;
      dstB[di] = ((float)b - 103.53f) / 57.375f;

      dst_gray[di] = clamp_u8(0.299f * r + 0.587f * g + 0.114f * b);
    }
  }
}

// ================= softmax + top1 ==================
static void softmax_vec(const float *in, int n, float *out) {
  float m = -INFINITY;
  for (int i = 0; i < n; ++i)
    if (isfinite(in[i]) && in[i] > m)
      m = in[i];
  float s = 0.f;
  for (int i = 0; i < n; ++i) {
    float z = isfinite(in[i]) ? (in[i] - m) : -50.f;
    float e = expf(z);
    out[i] = e;
    s += e;
  }
  if (s <= 0.f) {
    float u = 1.0f / (float)n;
    for (int i = 0; i < n; ++i)
      out[i] = u;
  } else {
    float inv = 1.0f / s;
    for (int i = 0; i < n; ++i)
      out[i] *= inv;
  }
}
static inline void top1(const float *p, int n, int *idx, float *val) {
  int k = 0;
  float b = -1.f;
  for (int i = 0; i < n; ++i) {
    if (p[i] > b) {
      b = p[i];
      k = i;
    }
  }
  *idx = k;
  *val = b;
}

// ================= CRC32 ==================
static uint32_t crc32_arduino(const uint8_t *data, size_t len) {
  uint32_t crc = 0xFFFFFFFFu;
  for (size_t i = 0; i < len; ++i) {
    crc ^= (uint32_t)data[i];
    for (int b = 0; b < 8; ++b) {
      if (crc & 1u)
        crc = (crc >> 1) ^ 0xEDB88320u;
      else
        crc >>= 1;
    }
  }
  return ~crc;
}

// ================= Serial frame ==================
static const uint8_t MAGIC[4] = {'F', 'R', 'M', 'E'};
static uint16_t g_seq = 0;

static inline void put_le16(uint8_t *p, uint16_t v) {
  p[0] = (uint8_t)(v & 0xFF);
  p[1] = (uint8_t)(v >> 8);
}
static inline void put_le32(uint8_t *p, uint32_t v) {
  p[0] = (uint8_t)(v & 0xFF);
  p[1] = (uint8_t)((v >> 8) & 0xFF);
  p[2] = (uint8_t)((v >> 16) & 0xFF);
  p[3] = (uint8_t)((v >> 24) & 0xFF);
}

static void send_frame_gray_FRME(uint16_t w, uint16_t h, uint8_t cls,
                                 uint16_t prob_x1000, uint16_t ms_x10,
                                 const uint8_t *gray) {
  const uint32_t payload_len = (uint32_t)w * (uint32_t)h;
  const uint32_t crc = crc32_arduino(gray, payload_len);

  uint8_t hdr[20];
  memcpy(hdr, MAGIC, 4);
  hdr[4] = 1; // version
  put_le16(&hdr[5], g_seq);
  put_le16(&hdr[7], w);
  put_le16(&hdr[9], h);
  hdr[11] = cls;
  put_le16(&hdr[12], prob_x1000);
  put_le16(&hdr[14], ms_x10);
  put_le32(&hdr[16], payload_len);

  Serial.write(hdr, sizeof(hdr));
  Serial.write(gray, payload_len);

  uint8_t cbuf[4];
  put_le32(cbuf, crc);
  Serial.write(cbuf, 4);

  g_seq++;
}

// ================= Setup ==================
void setup() {
  pinMode(LEDR, OUTPUT);
  pinMode(LEDG, OUTPUT);
  pinMode(LEDB, OUTPUT);
  digitalWrite(LEDR, LOW);
  digitalWrite(LEDG, LOW);
  digitalWrite(LEDB, LOW);

  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");

    while (1)
      ;
  }

  Serial.print("Accelerometer sample rate = ");
  Serial.print(IMU.accelerationSampleRate());
  Serial.println(" Hz");
  Serial.println();
  Serial.println("Acceleration in g's");
  Serial.println("X\tY\tZ");

  BLE.begin();
  BLE.setLocalName("MoodSip");
  BLE.setAdvertisedService(grayService);
  grayService.addCharacteristic(grayChar);
  grayService.addCharacteristic(commandChar);
  BLE.addService(grayService);
  BLE.advertise();

  // ✅ Sposta qui gli handler di evento
  BLE.setEventHandler(BLEConnected, onBleConnect);
  BLE.setEventHandler(BLEDisconnected, onBleDisconnect);

  BLE.advertise();

  Serial.begin(BAUD);
  while (Serial.available())
    Serial.read();

  if (setLogFunction) {
    if (STREAM_TO_PC)
      setLogFunction([](char *) {}); // silenzioso
    else
      setLogFunction([](char *msg) {
        Serial.print("[ZANT] ");
        if (msg)
          Serial.println(msg);
        else
          Serial.println("(null)");
      });
  }

  // ---- Camera ----
  cam.begin(CAMERA_R320x240, CAMERA_RGB565, 30);
  Serial.println("[ZANT] Ready (NCHW 1x3x96x96, normalized 0..1).");
}

// ================= Loop ==================
void loop() {
  BLE.poll(); // processa BLE sempre
  if (!isBleConnected) {
    delay(100); // piccola pausa per non sovraccaricare
    return;
  } else {

    // ================== GESTIONE BLE ==================
    if (bleState == WAIT_CMD) {
      BLE.poll(); // importante per non bloccare lo stack BLE

      if (commandChar.written()) {
        uint8_t cmd = commandChar.value()[0];

        if (cmd == 1) {
          // conferma presenza umana → LED rosso acceso brevemente
          digitalWrite(LEDR, HIGH);
          delay(300); // lampeggio visibile
          dynamicTimer =
              max(300000UL, dynamicTimer - 300000UL); // -5 min, minimo 5 min
          digitalWrite(LEDR, LOW);
        } else {
          // comando 0 → nessuna azione, resta spento
          digitalWrite(LEDR, LOW);
        }

        // resetta stato e riprende il ciclo
        commandChar.setValue(0);
        bleState = IDLE;
        clsWaiting = -1;
      }

      // ✅ ritorna al loop normale solo se non c'è comando ancora
      return;
    }

    if (cam.grabFrame(fb, 3000) != 0) {
      Serial.println("[ZANT] camera timeout");
      delay(5);
      return;
    }

    const uint8_t *buf = fb.getBuffer();
    resize_rgb565_to_96x96_rgbNCHW_and_gray_NEAREST(buf, 320, 240, gInput,
                                                    gGray8);

    // Inference
    float *out_raw = nullptr;
    unsigned long t0 = micros();
    int rc = predict(gInput, inputShape, 4, &out_raw);
    unsigned long t1 = micros();
    float ms_f = (t1 - t0) / 1000.0f;
    uint16_t ms_x10 = (uint16_t)(ms_f * 10.0f + 0.5f);

    if (rc != 0 || !out_raw) {
      Serial.print("[ZANT] predict() rc=");
      Serial.println(rc);
      delay(5);
      return;
    }

    // ================= Predizione ==================
    static float p80[CLASSES];
    static int cls;
    static float prob;
    static uint16_t prob_x1000;

    softmax_vec(out_raw, (int)CLASSES, p80);
    top1(p80, (int)CLASSES, &cls, &prob);
    prob = fmaxf(0.f, fminf(1.f, prob));
    prob_x1000 = (uint16_t)lrintf(prob * 1000.f);

    digitalWrite(LEDG, (prob >= THR) ? HIGH : LOW);

    if (STREAM_TO_PC)
      send_frame_gray_FRME(W, H, (uint8_t)cls, prob_x1000, ms_x10, gGray8);
    else {
      Serial.print("[ZANT] cls=");
      Serial.print(cls);
      Serial.print(" prob=");
      Serial.println(prob, 3);
      Serial.print(" time=");
      Serial.print(ms_f, 1);
      Serial.println(" ms");
    }

    // ================= BLE ==================
    if (cls == 1) {
      digitalWrite(LEDR, LOW);
      grayChar.writeValue(gGray8, W * H);
      clsWaiting = cls;
      bleState = WAIT_CMD;
    } else {
      digitalWrite(LEDR, LOW);
      clsWaiting = -1;
    }

    if (zant_free_result)
      zant_free_result(out_raw);
    out_raw = nullptr;

    // ================= Temperatura ogni 60 minuti ==================
    unsigned long now = millis();
    if (now - lastTempMillis >= TEMP_INTERVAL) {
      lastTempMillis = now;

      if (IMU.temperatureAvailable()) {
        int temperature_int = 0;
        float temperature_float = 0;
        IMU.readTemperature(temperature_int);
        IMU.readTemperatureFloat(temperature_float);

        Serial.print("LSM6DSOX Temperature = ");
        Serial.print(temperature_int);
        Serial.print(" (");
        Serial.print(temperature_float);
        Serial.print(")");
        Serial.println(" °C");
      }
      if (temperature > 28.0) {
        dynamicTimer =
            max(600000UL, dynamicTimer - 600000UL); // -10 min, minimo 10 min
        Serial.println("[TIMER] Temperatura > 28°C → -10 min");
      }

      float ax, ay, az;

      if (IMU.accelerationAvailable()) {
        IMU.readAcceleration(ax, ay, az);

        Serial.print(ax);
        Serial.print('\t');
        Serial.print(ay);
        Serial.print('\t');
        Serial.println(az);
      }

      // Accelerazione diversa da 9.81 → misura durata e aumenta timer
      float accelMag =
          sqrt(ax * ax + ay * ay + az * az); // modulo accelerazione
      if (fabs(accelMag - 9.81) > 0.5) { // soglia ±0.5g per rilevare movimento
        unsigned long increment = elapsed * 5; // aumenta di tempo_trascorso * 5
        dynamicTimer += increment;
        Serial.print("[TIMER] Movimento durato ");
        Serial.print(elapsed / 1000.0);
        Serial.print("s → +");
        Serial.print(increment / 60000.0);
        Serial.println(" min");
      }
    }

    // Decrescita naturale del timer (ogni ciclo)
    unsigned long nowTimer = millis();
    if (nowTimer - lastTimerUpdate >= 1000) { // ogni secondo
      lastTimerUpdate = nowTimer;
      if (dynamicTimer > 0)
        dynamicTimer -= 1000; // -1s
    }

    // ================= TIMER SCADUTO ==================
    if ((long)dynamicTimer <= 0) {
      Serial.println("[TIMER] Scaduto! LED blu acceso per 10 secondi.");

      digitalWrite(LEDB, HIGH);
      delay(10000); // 10 secondi
      digitalWrite(LEDB, LOW);

      // reset timer al valore base (es. 60 minuti)
      dynamicTimer = baseTimer;
      Serial.println("[TIMER] Timer resettato a 60 minuti.");
    }
  }
}
