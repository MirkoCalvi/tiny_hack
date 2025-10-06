#include <Arduino.h>
#include <math.h>
#include <stdint.h>
#include <string.h>
#include "lib_zant.h"
#include "camera.h"
#include <ArduinoBLE.h>
#include "gc2145.h"
#include <Arduino_LSM6DSOX.h>

// ================= TIMER DINAMICO ==================
unsigned long baseTimer = 3600000UL; // timer iniziale: 60 minuti
unsigned long dynamicTimer = baseTimer;    // timer modificabile
unsigned long lastTimerUpdate = 0;        // tempo ultima modifica

// ================= BLE ==================
BLEService grayService("12345678-1234-5678-1234-56789abcdef0"); 
BLECharacteristic grayChar(
    "abcdef01-1234-5678-1234-56789abcdef0", 
    BLERead | BLENotify, 
    96*96
); 
BLECharacteristic commandChar(
    "abcdef02-1234-5678-1234-56789abcdef0", 
    BLEWrite | BLEWriteWithoutResponse, 
    1
); 
bool isBleConnected = false;

// ================= Temperatura ==================
unsigned long lastTempMillis = 0;
const unsigned long TEMP_INTERVAL = 3600000UL; // 60 minuti

// ================= Config ==================
#define BAUD                 921600
#define THR                  0.60f
#define RGB565_IS_MSB_FIRST  1   
#define STREAM_TO_PC         0  

// ================= Modello (NCHW) ==================
static const uint32_t N=1, C=3, H=96, W=96;     
static const uint32_t CLASSES=2;               
static uint32_t inputShape[4] = {N, C, H, W};  

// ================= Buffers ==================
alignas(32) static float gInput[N*C*H*W];  
static uint8_t gGray8[W*H];                

// ================= Camera ==================
GC2145  sensor;
Camera  cam(sensor);
FrameBuffer fb;

// ================= ZANT hooks (deboli) ==================
extern "C" void setLogFunction(void (*logger)(char*)) __attribute__((weak));
extern "C" void zant_free_result(float*) __attribute__((weak));
extern "C" void zant_init_weights_io(void) __attribute__((weak));
extern "C" void zant_set_weights_base_address(const uint8_t*) __attribute__((weak));
extern "C" void zant_register_weight_callback(int (*cb)(size_t,uint8_t*,size_t)) __attribute__((weak));
extern "C" __attribute__((used)) const uint8_t* flash_weights_base=(const uint8_t*)0x90000000u;

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

// ================= BLE global variables ==================
enum BleState {
  IDLE,       
  WAIT_CMD    
};

BleState bleState = IDLE;  
int clsWaiting = -1;       

// ================= Funzioni BLE ==================
void onBleConnect(BLEDevice central) {
  isBleConnected = true;
  Serial.print("[BLE] Connesso a: ");
  Serial.println(central.address());
  digitalWrite(LEDB, HIGH);
}

void onBleDisconnect(BLEDevice central) {
  isBleConnected = false;
  Serial.print("[BLE] Disconnesso da: ");
  Serial.println(central.address());
  digitalWrite(LEDB, LOW);
  bleState = IDLE;
  clsWaiting = -1;
}

// ================= COCO80 ==================
static const char* COCO80[CLASSES] = {"background","humans"};

// ================= Helper colore ==================
static inline uint16_t load_rgb565_BE(const uint8_t* S2, int idx) {
  return (uint16_t)((S2[2*idx] << 8) | S2[2*idx + 1]);
}
static inline uint16_t load_rgb565_LE(const uint8_t* S2, int idx) {
  return (uint16_t)((S2[2*idx + 1] << 8) | S2[2*idx]);
}
static inline void rgb565_to_rgb888_u16(uint16_t v, uint8_t &R, uint8_t &G, uint8_t &B){
  uint8_t r5=(v>>11)&0x1F, g6=(v>>5)&0x3F, b5=v&0x1F;
  R=(uint8_t)((r5<<3)|(r5>>2));
  G=(uint8_t)((g6<<2)|(g6>>4));
  B=(uint8_t)((b5<<3)|(b5>>2));
}
static inline uint8_t clamp_u8(float x){
  if (x <= 0.f) return 0;
  if (x >= 255.f) return 255;
  return (uint8_t)lrintf(x);
}
static inline int clampi(int v, int lo, int hi){
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

// ================= Resize → NCHW + Gray ==================
static void resize_rgb565_to_96x96_rgbNCHW_and_gray_NEAREST(
    const uint8_t* src, int sw, int sh,
    float* __restrict dst_f, uint8_t* __restrict dst_gray)
{
  const float sx = (float)sw / (float)W;
  const float sy = (float)sh / (float)H;
  const int plane = H*W;
  float* dstR = dst_f + 0*plane;
  float* dstG = dst_f + 1*plane;
  float* dstB = dst_f + 2*plane;

  for (int y=0; y<H; ++y) {
    int ys = clampi((int)floorf((y + 0.5f) * sy), 0, sh-1);
    for (int x=0; x<W; ++x) {
      int xs = clampi((int)floorf((x + 0.5f) * sx), 0, sw-1);
      int si = ys*sw + xs;
      uint16_t v = RGB565_IS_MSB_FIRST ? load_rgb565_BE(src, si) : load_rgb565_LE(src, si);
      uint8_t r,g,b; rgb565_to_rgb888_u16(v, r,g,b);
      int di = y*W + x;
      dstR[di] = ((float)r - 123.675f) / 58.395f;
      dstG[di] = ((float)g - 116.28f) / 57.12f;
      dstB[di] = ((float)b - 103.53f) / 57.375f; 
      dst_gray[di] = clamp_u8(0.299f*r + 0.587f*g + 0.114f*b);
    }
  }
}

// ================= softmax + top1 ==================
static void softmax_vec(const float* in, int n, float* out){
  float m = -INFINITY;
  for(int i=0;i<n;++i) if(isfinite(in[i]) && in[i]>m) m=in[i];
  float s=0.f;
  for(int i=0;i<n;++i){
    float z = isfinite(in[i]) ? (in[i]-m) : -50.f;
    float e = expf(z); out[i]=e; s+=e;
  }
  if(s<=0.f){ for(int i=0;i<n;++i) out[i]=1.f/(float)n; }
  else { float inv=1.f/s; for(int i=0;i<n;++i) out[i]*=inv; }
}
static inline void top1(const float* p,int n,int* idx,float* val){
  int k=0; float b=-1.f;
  for(int i=0;i<n;++i) if(p[i]>b){ b=p[i]; k=i; }
  *idx=k; *val=b;
}

// ================= CRC32 ==================
static uint32_t crc32_arduino(const uint8_t* data, size_t len){
  uint32_t crc=0xFFFFFFFFu;
  for(size_t i=0;i<len;++i){
    crc ^= (uint32_t)data[i];
    for(int b=0;b<8;++b){ crc = (crc & 1u) ? (crc >> 1)^0xEDB88320u : crc>>1; }
  }
  return ~crc;
}

// ================= Serial frame ==================
static const uint8_t MAGIC[4] = {'F','R','M','E'};
static uint16_t g_seq=0;
static inline void put_le16(uint8_t* p,uint16_t v){ p[0]=(uint8_t)(v&0xFF); p[1]=(uint8_t)(v>>8); }
static inline void put_le32(uint8_t* p,uint32_t v){ p[0]=(uint8_t)(v&0xFF); p[1]=(uint8_t)((v>>8)&0xFF); p[2]=(uint8_t)((v>>16)&0xFF); p[3]=(uint8_t)((v>>24)&0xFF); }

static void send_frame_gray_FRME(uint16_t w,uint16_t h,uint8_t cls,uint16_t prob_x1000,uint16_t ms_x10,const uint8_t* gray){
  uint32_t payload_len=(uint32_t)w*(uint32_t)h;
  uint32_t crc=crc32_arduino(gray,payload_len);
  uint8_t hdr[20];
  memcpy(hdr,MAGIC,4); hdr[4]=1;
  put_le16(&hdr[5],g_seq); put_le16(&hdr[7],w); put_le16(&hdr[9],h);
  hdr[11]=cls; put_le16(&hdr[12],prob_x1000); put_le16(&hdr[14],ms_x10); put_le32(&hdr[16],payload_len);
  Serial.write(hdr,sizeof(hdr)); Serial.write(gray,payload_len);
  uint8_t cbuf[4]; put_le32(cbuf,crc); Serial.write(cbuf,4);
  g_seq++;
}

// ================= Setup ==================
void setup(){
  pinMode(LEDR, OUTPUT); pinMode(LEDG, OUTPUT); pinMode(LEDB, OUTPUT);
  digitalWrite(LEDR, LOW); digitalWrite(LEDG, LOW); digitalWrite(LEDB, LOW);

  if(!IMU.begin()){ Serial.println("Failed to initialize IMU!"); while(1); }

  Serial.print("Accelerometer sample rate = "); Serial.print(IMU.accelerationSampleRate()); Serial.println(" Hz");
  Serial.println("Acceleration in g's: X\tY\tZ");

  Serial.begin(BAUD);
  while(Serial.available()) Serial.read();

  BLE.begin(); BLE.setLocalName("MoodSip"); BLE.setAdvertisedService(grayService);
  grayService.addCharacteristic(grayChar); grayService.addCharacteristic(commandChar);
  BLE.addService(grayService);
  BLE.setEventHandler(BLEConnected,onBleConnect);
  BLE.setEventHandler(BLEDisconnected,onBleDisconnect);
  BLE.advertise();

  if(setLogFunction){
    if(STREAM_TO_PC) setLogFunction([](char*){});
    else setLogFunction([](char* msg){ Serial.print("[ZANT] "); if(msg) Serial.println(msg); else Serial.println("(null)"); });
  }

  cam.begin(CAMERA_R320x240,CAMERA_RGB565,30);
  Serial.println("[ZANT] Ready (NCHW 1x3x96x96, normalized 0..1).");
}

// ================= Loop ==================
void loop() {
  BLE.poll(); // processa BLE sempre

  // ================== Lettura IMU ==================
  float temperature_float = 0.0f;
  float x=0.0f, y=0.0f, z=0.0f;

  if(IMU.temperatureAvailable()){
      IMU.readTemperatureFloat(temperature_float);
      Serial.print("LSM6DSOX Temperature = ");
      Serial.println(temperature_float, 2);
  }

  if(IMU.accelerationAvailable()){
      IMU.readAcceleration(x, y, z);
      Serial.print("Acceleration (g): ");
      Serial.print(x, 2); Serial.print("\t");
      Serial.print(y, 2); Serial.print("\t");
      Serial.println(z, 2);
  }

  // ================== Aggiornamento dynamicTimer ==================
  // temperatura > 28°C → decremento timer
  if(temperature_float > 28.0f){
      dynamicTimer = max(600000UL, dynamicTimer - 600000UL); // -10 min
      Serial.println("[TIMER] Temperatura > 28°C → -10 min");
  }

  // accelerazione diversa da 9.81 → incremento timer
  float accelMag = sqrt(x*x + y*y + z*z);
  if(fabs(accelMag - 9.81f) > 0.5f){
      unsigned long elapsed = 1000; // possiamo usare 1 secondo come riferimento
      unsigned long increment = elapsed * 5;
      dynamicTimer += increment;
      Serial.print("[TIMER] Movimento rilevato → +");
      Serial.print(increment/60000.0);
      Serial.println(" min");
  }

  // ================== Decrescita naturale timer ==================
  unsigned long nowTimer = millis();
  if(nowTimer - lastTimerUpdate >= 1000){ // ogni secondo
      lastTimerUpdate = nowTimer;
      if(dynamicTimer > 0) dynamicTimer -= 1000; // -1s
  }

  // ================== Gestione BLE ==================
  if(bleState == WAIT_CMD){
      if(commandChar.written()){
          uint8_t cmd = commandChar.value()[0];
          if(cmd == 1){
              digitalWrite(LEDR, HIGH);
              delay(300); // lampeggio LED rosso breve
              dynamicTimer = max(300000UL, dynamicTimer - 300000UL); // -5 min
              digitalWrite(LEDR, LOW);
          }
          commandChar.setValue(0);
          bleState = IDLE;
          clsWaiting = -1;
      }
      // non facciamo return: la predizione continua comunque
  }

  // ================== Lettura camera ==================
  if(cam.grabFrame(fb, 3000) != 0){
      Serial.println("[ZANT] camera timeout");
      delay(5);
      return;
  }

  const uint8_t* buf = fb.getBuffer();
  resize_rgb565_to_96x96_rgbNCHW_and_gray_NEAREST(buf, 320, 240, gInput, gGray8);

  // ================== Inference ==================
  float* out_raw = nullptr;
  unsigned long t0 = micros();
  int rc = predict(gInput, inputShape, 4, &out_raw);
  unsigned long t1 = micros();
  float ms_f = (t1 - t0)/1000.0f;
  uint16_t ms_x10 = (uint16_t)(ms_f*10.0f + 0.5f);

  if(rc!=0 || !out_raw){
      Serial.print("[ZANT] predict() rc=");
      Serial.println(rc);
      delay(5);
      return;
  }

  static float p80[CLASSES];
  static int cls;
  static float prob;
  static uint16_t prob_x1000;

  softmax_vec(out_raw, (int)CLASSES, p80);
  top1(p80, (int)CLASSES, &cls, &prob);
  prob = fmaxf(0.f, fminf(1.f, prob));
  prob_x1000 = (uint16_t)lrintf(prob*1000.f);

  // ================== LED e log ==================
  digitalWrite(LEDG, (prob>=THR)?HIGH:LOW);

  if(cls == 1){ // human → LED rosso acceso sempre
      digitalWrite(LEDR, HIGH);
      clsWaiting = cls;
      bleState = WAIT_CMD;
      grayChar.writeValue(gGray8, W*H);
  } else {
      digitalWrite(LEDR, LOW);
      clsWaiting = -1;
  }

  if(STREAM_TO_PC)
      send_frame_gray_FRME(W, H, (uint8_t)cls, prob_x1000, ms_x10, gGray8);
  else{
      Serial.print("[ZANT] cls=");
      Serial.print(cls);
      Serial.print(" prob=");
      Serial.println(prob,3);
      Serial.print(" time=");
      Serial.print(ms_f,1);
      Serial.println(" ms");
  }

  if(zant_free_result) zant_free_result(out_raw);
  out_raw = nullptr;

  // ================== Timer scaduto ==================
  if((long)dynamicTimer <= 0){
      Serial.println("[TIMER] Scaduto! LED blu acceso per 10 secondi.");
      digitalWrite(LEDB, HIGH);
      delay(10000);
      digitalWrite(LEDB, LOW);
      dynamicTimer = baseTimer;
      Serial.println("[TIMER] Timer resettato a 60 minuti.");
  }
}
