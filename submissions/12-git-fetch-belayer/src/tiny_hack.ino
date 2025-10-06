/************ Nicla Vision QSPI XIP (Memory-Mapped) + predict ************
 * Core: arduino:mbed_nicla (4.4.1)
 * - HAL QSPI (QUADSPI)
 * - Pin: CLK=PB2, CS=PG6, IO0..3=PD11..PD14 (AF QUADSPI)
 * - QE su SR2, poi READ 0x6B 1-1-4 con 8 dummy
 *****************************************************************************/

extern "C"
{
#ifndef STM32H747xx
#define STM32H747xx
#endif
#ifndef HAL_QSPI_MODULE_ENABLED
#define HAL_QSPI_MODULE_ENABLED
#endif
#include "stm32h7xx_hal.h"
#include "stm32h7xx_hal_qspi.h"
}

// ================== Config ==================
#define BAUD                 921600
#define THR                  0.60f
#define RGB565_IS_MSB_FIRST  1   // 1: big-endian (MSB-first), 0: little-endian
#define STREAM_TO_PC         0   // 1: stream binario compatibile con viewer Python, 0: solo log

// Required by the Zig library:
extern "C" __attribute__((used))
const uint8_t *flash_weights_base = (const uint8_t *)0x90000000u;

#include <Arduino.h>
#include <lib_zant.h> // int predict(float*, uint32_t*, uint32_t, float**)
#include "variables.h"
#include <ArduinoJson.h>
#include <ArduinoHttpClient.h>
#include <Arduino_LSM6DSOX.h>
#include <math.h>
#include <ArduinoBLE.h>
#include <WiFi.h>
#include "camera.h"
#include "gc2145.h"





// ***** STUFF TAKEN FROM CAMERA.INO *****
static QSPI_HandleTypeDef hqspi;

static const uint8_t CMD_RDID = 0x9F, CMD_WREN = 0x06;
static const uint8_t CMD_RDSR1 = 0x05, CMD_RDSR2 = 0x35, CMD_WRSR = 0x01;
static const uint8_t CMD_READ_QO = 0x6B;

void prepareInput(uint8_t* rgb_image, int width, int height, float* input) {
    int pixels = width * height;
    Serial.print("4");
    // Normalizza e separa i canali
    for (int i = 0; i < pixels; i++) {
        // Canale R (primi 9216 elementi)
        input[i] = rgb_image[i*3 + 0] / 255.0f;
        
        // Canale G (elementi 9216-18431)
        input[pixels + i] = rgb_image[i*3 + 1] / 255.0f;
        
        // Canale B (elementi 18432-27647)
        input[2*pixels + i] = rgb_image[i*3 + 2] / 255.0f;
    }
    Serial.print("5");
}
// MSP init (GPIO+clock)
extern "C" void HAL_QSPI_MspInit(QSPI_HandleTypeDef *h)
{
    if (h->Instance != QUADSPI)
        return;
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_GPIOG_CLK_ENABLE();
    __HAL_RCC_QSPI_CLK_ENABLE();

    GPIO_InitTypeDef GPIO = {0};
    // CLK PB2 (AF9)
    GPIO.Pin = GPIO_PIN_2;
    GPIO.Mode = GPIO_MODE_AF_PP;
    GPIO.Pull = GPIO_NOPULL;
    GPIO.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO.Alternate = GPIO_AF9_QUADSPI;
    HAL_GPIO_Init(GPIOB, &GPIO);
    // CS PG6 (AF10)
    GPIO.Pin = GPIO_PIN_6;
    GPIO.Alternate = GPIO_AF10_QUADSPI;
    HAL_GPIO_Init(GPIOG, &GPIO);
    // IO0..IO3 PD11..PD14 (AF9)
    GPIO.Pin = GPIO_PIN_11 | GPIO_PIN_12 | GPIO_PIN_13 | GPIO_PIN_14;
    GPIO.Alternate = GPIO_AF9_QUADSPI;
    HAL_GPIO_Init(GPIOD, &GPIO);
}

static HAL_StatusTypeDef qspi_init_16mb(QSPI_HandleTypeDef *h)
{
    h->Instance = QUADSPI;
    h->Init.ClockPrescaler = 7;
    h->Init.FifoThreshold = 4;
    h->Init.SampleShifting = QSPI_SAMPLE_SHIFTING_NONE;
    h->Init.FlashSize = 23; // 2^24 = 16MB -> set 23
    h->Init.ChipSelectHighTime = QSPI_CS_HIGH_TIME_2_CYCLE;
    h->Init.ClockMode = QSPI_CLOCK_MODE_0;
    h->Init.FlashID = QSPI_FLASH_ID_1;
    h->Init.DualFlash = QSPI_DUALFLASH_DISABLE;
    return HAL_QSPI_Init(h);
}

static HAL_StatusTypeDef qspi_cmd(QSPI_HandleTypeDef *h, uint8_t inst,
                                  uint32_t addrMode, uint32_t dataMode,
                                  uint32_t addr, uint32_t dummy,
                                  uint8_t *data, size_t len, bool rx)
{
    QSPI_CommandTypeDef c = {0};
    c.InstructionMode = QSPI_INSTRUCTION_1_LINE;
    c.Instruction = inst;
    c.AddressMode = addrMode;
    c.Address = addr;
    c.AddressSize = QSPI_ADDRESS_24_BITS;
    c.DataMode = dataMode;
    c.NbData = len;
    c.DummyCycles = dummy;
    if (HAL_QSPI_Command(h, &c, HAL_MAX_DELAY) != HAL_OK)
        return HAL_ERROR;
    if (len == 0)
        return HAL_OK;
    return rx ? HAL_QSPI_Receive(h, data, HAL_MAX_DELAY)
              : HAL_QSPI_Transmit(h, data, HAL_MAX_DELAY);
}

static HAL_StatusTypeDef rd_sr(QSPI_HandleTypeDef *h, uint8_t cmd, uint8_t *val)
{
    return qspi_cmd(h, cmd, QSPI_ADDRESS_NONE, QSPI_DATA_1_LINE, 0, 0, val, 1, true);
}
static HAL_StatusTypeDef wren(QSPI_HandleTypeDef *h)
{
    return qspi_cmd(h, CMD_WREN, QSPI_ADDRESS_NONE, QSPI_DATA_NONE, 0, 0, nullptr, 0, true);
}
static HAL_StatusTypeDef wr_sr12(QSPI_HandleTypeDef *h, uint8_t sr1, uint8_t sr2)
{
    uint8_t buf[2] = {sr1, sr2};
    return qspi_cmd(h, CMD_WRSR, QSPI_ADDRESS_NONE, QSPI_DATA_1_LINE, 0, 0, buf, 2, false);
}

static HAL_StatusTypeDef wait_wip_clear(QSPI_HandleTypeDef *h, uint32_t timeout_ms)
{
    uint32_t t0 = millis();
    for (;;)
    {
        uint8_t sr1 = 0;
        if (rd_sr(h, CMD_RDSR1, &sr1) != HAL_OK)
            return HAL_ERROR;
        if ((sr1 & 0x01) == 0)
            return HAL_OK;
        if ((millis() - t0) > timeout_ms)
            return HAL_TIMEOUT;
        delay(1);
    }
}
static HAL_StatusTypeDef enable_quad(QSPI_HandleTypeDef *h)
{
    uint8_t sr1 = 0, sr2 = 0;
    if (rd_sr(h, CMD_RDSR1, &sr1) != HAL_OK)
        return HAL_ERROR;
    if (rd_sr(h, CMD_RDSR2, &sr2) != HAL_OK)
        return HAL_ERROR;
    if (sr2 & 0x02)
        return HAL_OK; // QE already 1
    if (wren(h) != HAL_OK)
        return HAL_ERROR;
    sr2 |= 0x02;
    if (wr_sr12(h, sr1, sr2) != HAL_OK)
        return HAL_ERROR;
    if (wait_wip_clear(h, 500) != HAL_OK)
        return HAL_ERROR;
    if (rd_sr(h, CMD_RDSR2, &sr2) != HAL_OK)
        return HAL_ERROR;
    return (sr2 & 0x02) ? HAL_OK : HAL_ERROR;
}

static HAL_StatusTypeDef qspi_enter_mmap(QSPI_HandleTypeDef *h)
{
    QSPI_CommandTypeDef c = {0};
    c.InstructionMode = QSPI_INSTRUCTION_1_LINE;
    c.Instruction = CMD_READ_QO; // 0x6B
    c.AddressMode = QSPI_ADDRESS_1_LINE;
    c.AddressSize = QSPI_ADDRESS_24_BITS;
    c.Address = 0x000000;
    c.AlternateByteMode = QSPI_ALTERNATE_BYTES_NONE;
    c.DataMode = QSPI_DATA_4_LINES;
    c.DummyCycles = 8;
#ifdef QSPI_DDR_MODE_DISABLE
    c.DdrMode = QSPI_DDR_MODE_DISABLE;
    c.DdrHoldHalfCycle = QSPI_DDR_HHC_ANALOG_DELAY;
#endif
#ifdef QSPI_SIOO_INST_EVERY_CMD
    c.SIOOMode = QSPI_SIOO_INST_EVERY_CMD;
#endif
    QSPI_MemoryMappedTypeDef mm = {0};
    mm.TimeOutActivation = QSPI_TIMEOUT_COUNTER_DISABLE;
    mm.TimeOutPeriod = 0;
    return HAL_QSPI_MemoryMapped(h, &c, &mm);
}

// ---- Predict demo ----
#ifndef ZANT_OUTPUT_LEN
#define ZANT_OUTPUT_LEN 2 // <<<<<<<<<<<<<<<< ensure it is correct !!
#endif
static const int OUT_LEN = ZANT_OUTPUT_LEN;
static const uint32_t IN_N = 1, IN_C = 3, IN_H = 96, IN_W = 96; // <<<<<<<<<<<<<<<< ensure it is correct !!
static const uint32_t IN_SIZE = IN_N * IN_C * IN_H * IN_W;
static float inputData[IN_SIZE];
static uint32_t inputShape[4] = {IN_N, IN_C, IN_H, IN_W};

alignas(32) static float gInput[IN_N*IN_C*IN_H*IN_W];
static uint8_t gGray8[IN_W*IN_H];

static void printOutput(const float *out, int len)
{
    if (!out || len <= 0)
    {
        Serial.println("Output nullo");
        return;
    }
    Serial.println("=== Output ===");
    for (int i = 0; i < len; ++i)
    {
        Serial.print("out[");
        Serial.print(i);
        Serial.print("] = ");
        Serial.println(out[i], 6);
    }
    Serial.println("==============");
}
static int qspi_xip_read(size_t off, uint8_t* buf, size_t sz) {
  if (!buf || !flash_weights_base) return -1;
  memcpy(buf, flash_weights_base + off, sz);
  return 0;
}

// ================== Helpers colore ==================
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
  if (x <= 0.f)   return 0;
  if (x >= 255.f) return 255;
  return (uint8_t)lrintf(x);
}
static inline int clampi(int v, int lo, int hi){
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

static void attach_weights_io() {
  if (zant_init_weights_io) zant_init_weights_io();
  if (zant_set_weights_base_address)      zant_set_weights_base_address(flash_weights_base);
  else if (zant_register_weight_callback) zant_register_weight_callback(qspi_xip_read);
}

// ================== Resize → NCHW + Gray ==================
// Output gInput (NCHW): float normalizzato [0,1]
static void resize_rgb565_to_96x96_rgbNCHW_and_gray_NEAREST(
    const uint8_t* src, int sw, int sh,
    float* __restrict dst_f, uint8_t* __restrict dst_gray)
{
  const float sx = (float)sw / (float)IN_W;
  const float sy = (float)sh / (float)IN_H;
  const float inv255 = 1.0f / 255.0f;

  const int plane = (int)(IN_H*IN_W);
  float* __restrict dstR = dst_f + 0*plane;
  float* __restrict dstG = dst_f + 1*plane;
  float* __restrict dstB = dst_f + 2*plane;

  for (int y = 0; y < (int)IN_H; ++y) {
    int ys = clampi((int)floorf((y + 0.5f) * sy), 0, sh - 1);
    for (int x = 0; x < (int)IN_W; ++x) {
      int xs = clampi((int)floorf((x + 0.5f) * sx), 0, sw - 1);
      int si = ys * sw + xs;

      uint16_t v = RGB565_IS_MSB_FIRST ? load_rgb565_BE(src, si)
                                       : load_rgb565_LE(src, si);
      uint8_t r,g,b; rgb565_to_rgb888_u16(v, r,g,b);

      const int di = y*IN_W + x;
      dstR[di] = (float)r * inv255;
      dstG[di] = (float)g * inv255;
      dstB[di] = (float)b * inv255;

      // Gray solo per preview (0..255)
      gGray8[di] = clamp_u8(0.299f*r + 0.587f*g + 0.114f*b);
    }
  }
}
// ***** /STUFF TAKEN FROM CAMERA.INO *****





FrameBuffer fb;
WiFiClient wifi;
State currentState = IDLE;
GC2145  sensor;
Camera  cam(sensor);

void setup()
{
    Serial.begin(115200);
    pinMode(LEDR, OUTPUT);
    pinMode(LEDG, OUTPUT);
    pinMode(LEDB, OUTPUT);
    digitalWrite(LEDR, HIGH);
    attach_weights_io();

    // ---- Camera ----
    cam.begin(CAMERA_R320x240, CAMERA_RGB565, 30);
    while (!Serial) {
      ;
    }
    //Serial.println("Starting WiFi connection...");
    //connectToWiFi();
  
    arduinoId = "arduino_" + String(random(10000, 99999));
    // Serial.print("Arduino ID: ");
    // Serial.println(arduinoId);
  
    //registerArduino();

    
    uint32_t t0 = millis();
    while (!Serial && (millis() - t0) < 4000)
        delay(10);
    //Serial.println("\n== Nicla Vision QSPI XIP (HAL) + predict ==");

    if (qspi_init_16mb(&hqspi) != HAL_OK)
    {
        Serial.println("QSPI init FAIL");
        for (;;)
        {
        }
    }
    if (enable_quad(&hqspi) != HAL_OK)
    {
        Serial.println("Enable QE FAIL");
        for (;;)
        {
        }
    }
    if (qspi_enter_mmap(&hqspi) != HAL_OK)
    {
        Serial.println("XIP FAIL");
        for (;;)
        {
        }
    }

    // Prepare NCHW input (simple constant pattern per channel)
    /*for (uint32_t c = 0; c < IN_C; ++c)
        for (uint32_t h = 0; h < IN_H; ++h)
            for (uint32_t w = 0; w < IN_W; ++w)
            {
                uint32_t idx = c * (IN_H * IN_W) + h * IN_W + w;
                inputData[idx] = (c == 0) ? 0.8f : (c == 1 ? 0.5f : 0.2f);
            }

    int *out = nullptr;
    Serial.println("[Predict] Calling predict()...");
    int rc = -3 ;
    unsigned long average_sum = 0;

    for(uint32_t i = 0; i<10; i++) {
        unsigned long t_us0 = micros();
        rc = predict(inputData, inputShape, 4, &out);
        unsigned long t_us1 = micros();
        average_sum = average_sum + t_us1 - t_us0;
        if(rc!=0) break;
    }*/
}

void loop() 
{ 
    // ***** WIFI CONNECTION *****
    // // Check WiFi connection
    // if (WiFi.status() != WL_CONNECTED) {
    //   Serial.println("WiFi disconnected. Reconnecting...");
    //   connectToWiFi();
    // }
  
    // Poll server for commands
    // if (millis() - lastPollTime > pollInterval) {
    //   pollForCommands();
    //   lastPollTime = millis();
    // }
    // ***** /WIFI CONNECTION *****

    // You should start from IDLE, but wifi not working so skipping it
    // Skipping also bluetooth 
    currentState = RUNNING;

    switch (currentState) {
      case IDLE:
        break;
      
      case CONNECTING:
        handleConnectingState();  //bluetooth connection but skipping
        break;
      
      case CALIBRATING:
        break;
      
      case RUNNING:
        setAngle();
        mainLoop();
        break;
    }
  
    delay(10);
 }
 //THE END :) (hopefully)