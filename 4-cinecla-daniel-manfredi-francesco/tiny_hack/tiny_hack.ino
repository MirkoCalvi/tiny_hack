/************ Nicla Vision QSPI XIP (Memory-Mapped) + predict + camera stream + NN ************
 * Core: arduino:mbed_nicla (4.4.1)
 * - HAL QSPI (QUADSPI)
 * - Pin: CLK=PB2, CS=PG6, IO0..3=PD11..PD14 (AF QUADSPI)
 * - QE su SR2, poi READ 0x6B 1-1-4 con 8 dummy

 * Streams camera feed over serial for visualization
 * Press '1' in serial monitor to capture and run inference
 * Press '2' to toggle continuous streaming
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

// Required by the Zig library:
extern "C" __attribute__((used))
const uint8_t *flash_weights_base = (const uint8_t *)0x90000000u;

#include <Arduino.h>
#include <lib_zant.h> // int predict(float*, uint32_t*, uint32_t, float**)
#include "camera.h"
#include "gc2145.h"

GC2145 galaxyCore;
Camera cam(galaxyCore);

static QSPI_HandleTypeDef hqspi;

static const uint8_t CMD_RDID = 0x9F, CMD_WREN = 0x06;
static const uint8_t CMD_RDSR1 = 0x05, CMD_RDSR2 = 0x35, CMD_WRSR = 0x01;
static const uint8_t CMD_READ_QO = 0x6B;

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

FrameBuffer fb;
bool streamMode = false;

static bool processCameraFrame()
{
    if (cam.grabFrame(fb, 3000) != 0)
    {
        Serial.println("Camera grab failed!");
        return false;
    }

    uint8_t *data = fb.getBuffer();
    uint32_t cam_width = 160;  // QQVGA width
    uint32_t cam_height = 120; // QQVGA height
    uint32_t target_size = 96;
    
    // Crop top-right quarter: start from right half, top half
    uint32_t crop_x = cam_width / 2;  // Start from right half (80)
    uint32_t crop_y = 0;              // Start from top half
    
    // Resize the 80x60 top-right quarter to 96x96
    float scale_x = (float)(cam_width / 2) / (float)target_size;  // 80/96 = 0.83
    float scale_y = (float)(cam_height / 2) / (float)target_size; // 60/96 = 0.625
    
    for (uint32_t y = 0; y < target_size; y++)
    {
        for (uint32_t x = 0; x < target_size; x++)
        {
            // Calculate source coordinates with scaling
            uint32_t src_x = crop_x + (uint32_t)(x * scale_x);
            uint32_t src_y = crop_y + (uint32_t)(y * scale_y);
            
            // Clamp to valid range
            if (src_x >= cam_width) src_x = cam_width - 1;
            if (src_y >= cam_height) src_y = cam_height - 1;
            
            uint32_t src_idx = src_y * cam_width + src_x;
            uint32_t dst_idx = y * target_size + x;
            inputData[dst_idx] = data[src_idx] / 255.0f;
        }
    }
    return true;
}

static void printOutput(const float *out, int len)
{
    if (!out || len <= 0)
    {
        Serial.println("Output nullo");
        return;
    }
    Serial.println("=== Classification Result ===");
    
    if (len >= 2)
    {
        // Binary classification: 0=neutral, 1=engaged
        float neutral_score = out[0];
        float engaged_score = out[1];
        
        Serial.print("Neutral score: ");
        Serial.println(neutral_score, 6);
        Serial.print("Engaged score: ");
        Serial.println(engaged_score, 6);
        
        // Determine classification based on higher score
        if (engaged_score > neutral_score)
        {
            Serial.println("Result: ENGAGED (1)");
        }
        else
        {
            Serial.println("Result: NEUTRAL (0)");
        }
    }
    else
    {
        // Fallback for unexpected output length
        for (int i = 0; i < len; ++i)
        {
            Serial.print("out[");
            Serial.print(i);
            Serial.print("] = ");
            Serial.println(out[i], 6);
        }
    }
    Serial.println("=============================");
}

void setup()
{
    Serial.begin(921600);
    uint32_t t0 = millis();
    while (!Serial && (millis() - t0) < 4000)
        delay(10);
    Serial.println("\n== Nicla Vision Camera Stream + Engagement Classification ==");
    Serial.println("Commands:");
    Serial.println("  '1' - Capture frame and run engagement classification");
    Serial.println("  '2' - Toggle continuous streaming with classification");
    Serial.println("  '3' - Save single frame as ASCII art");
    Serial.println("Output: 0=Neutral, 1=Engaged");

    Serial.println("[QSPI] Initializing...");
    if (qspi_init_16mb(&hqspi) != HAL_OK)
    {
        Serial.println("QSPI init FAIL");
        for (;;) {}
    }
    if (enable_quad(&hqspi) != HAL_OK)
    {
        Serial.println("Enable QE FAIL");
        for (;;) {}
    }
    if (qspi_enter_mmap(&hqspi) != HAL_OK)
    {
        Serial.println("XIP FAIL");
        for (;;) {}
    }
    Serial.println("[QSPI] Memory-mapped mode active");

    // Prepare NCHW input (simple constant pattern per channel)
    for (uint32_t c = 0; c < IN_C; ++c)
        for (uint32_t h = 0; h < IN_H; ++h)
            for (uint32_t w = 0; w < IN_W; ++w)
            {
                uint32_t idx = c * (IN_H * IN_W) + h * IN_W + w;
                inputData[idx] = (c == 0) ? 0.8f : (c == 1 ? 0.5f : 0.2f);
            }

    float *out = nullptr;
    Serial.println("[Predict] Calling predict()...");
    int rc = -3;
    unsigned long average_sum = 0;

    for(uint32_t i = 0; i<10; i++) {
        unsigned long t_us0 = micros();
        rc = predict(inputData, inputShape, 4, &out);
        unsigned long t_us1 = micros();
        average_sum = average_sum + t_us1 - t_us0;
        if(rc!=0) break;
    }

    Serial.print("[Predict] rc=");
    Serial.println(rc);
    Serial.print("[Predict] us=");
    Serial.println((unsigned long)(average_sum/10));
    if (rc == 0 && out)
    {
        printOutput(out, OUT_LEN);
        Serial.println("[Predict] Model loaded successfully - ready for real-time classification!");
    }
    else
    {
        Serial.println("[Predict] FAIL - Model loading failed!");
    }

    Serial.println("[Camera] Initializing...");
    // Use QQVGA (160x120) for better memory efficiency
    // This reduces framebuffer from 320x240=76,800 bytes to 160x120=19,200 bytes
    if (!cam.begin(CAMERA_R160x120, CAMERA_GRAYSCALE, 15))
    {
        Serial.println("Camera init FAIL!");
        for (;;) {}
    }
    Serial.println("[Camera] Ready! Using QQVGA (160x120) for memory efficiency");
    Serial.println("\nReady for commands...");
}

void loop()
{
    // Check for serial commands
    if (Serial.available())
    {
        char cmd = Serial.read();
        
        if (cmd == '1')
        {
            // Single inference
            Serial.println("\n[Classification] Capturing and processing...");
            if (processCameraFrame())
            {
                float *out = nullptr;
                unsigned long t_us0 = micros();
                int rc = predict(inputData, inputShape, 4, &out);
                unsigned long t_us1 = micros();
                
                Serial.print("[Predict] rc=");
                Serial.println(rc);
                Serial.print("[Predict] time (us)=");
                Serial.println(t_us1 - t_us0);
                
                if (rc == 0 && out)
                {
                    printOutput(out, OUT_LEN);
                }
                else
                {
                    Serial.println("[Classification] FAILED!");
                }
            }
        }
        else if (cmd == '2')
        {
            streamMode = !streamMode;
            Serial.print("Stream mode: ");
            Serial.println(streamMode ? "ON" : "OFF");
        }
        else if (cmd == '3')
        {
            // Display single frame as ASCII art
            if (cam.grabFrame(fb, 3000) == 0)
            {
                Serial.println("\n=== ASCII Camera View (96x96 top-right quarter from QQVGA) ===");
                uint8_t *data = fb.getBuffer();
                uint32_t cam_width = 160;  // QQVGA width
                uint32_t cam_height = 120; // QQVGA height
                uint32_t target_size = 96;
                
                // Crop top-right quarter: start from right half, top half
                uint32_t crop_x = cam_width / 2;  // Start from right half (80)
                uint32_t crop_y = 0;              // Start from top half
                
                // Resize the 80x60 top-right quarter to 96x96
                float scale_x = (float)(cam_width / 2) / (float)target_size;  // 80/96 = 0.83
                float scale_y = (float)(cam_height / 2) / (float)target_size; // 60/96 = 0.625
                
                // Print every 4th row and column to fit in terminal
                for (uint32_t y = 0; y < target_size; y += 4)
                {
                    for (uint32_t x = 0; x < target_size; x += 2)
                    {
                        // Calculate source coordinates with scaling
                        uint32_t src_x = crop_x + (uint32_t)(x * scale_x);
                        uint32_t src_y = crop_y + (uint32_t)(y * scale_y);
                        
                        // Clamp to valid range
                        if (src_x >= cam_width) src_x = cam_width - 1;
                        if (src_y >= cam_height) src_y = cam_height - 1;
                        
                        uint32_t idx = src_y * cam_width + src_x;
                        uint8_t pixel = data[idx];
                        
                        // Convert to ASCII based on brightness
                        char c;
                        if (pixel < 32) c = ' ';
                        else if (pixel < 64) c = '.';
                        else if (pixel < 96) c = ':';
                        else if (pixel < 128) c = '-';
                        else if (pixel < 160) c = '=';
                        else if (pixel < 192) c = '+';
                        else if (pixel < 224) c = '*';
                        else c = '#';
                        
                        Serial.print(c);
                    }
                    Serial.println();
                }
                Serial.println("==========================================");
            }
        }
    }

    // Continuous streaming with inference on every frame
    if (streamMode)
    {
        if (cam.grabFrame(fb, 3000) == 0)
        {
            // Process frame for inference
            if (processCameraFrame())
            {
                // Run inference
                float *out = nullptr;
                unsigned long t_us0 = micros();
                int rc = predict(inputData, inputShape, 4, &out);
                unsigned long t_us1 = micros();
                
                // Create JSON output
                Serial.print("{\"inference\":{\"rc\":");
                Serial.print(rc);
                Serial.print(",\"time_us\":");
                Serial.print(t_us1 - t_us0);
                
                if (rc == 0 && out)
                {
                    Serial.print(",\"output\":[");
                    for (int i = 0; i < OUT_LEN; i++)
                    {
                        if (i > 0) Serial.print(",");
                        Serial.print(out[i], 6);
                    }
                    Serial.print("]");
                    
                    // Add classification result
                    if (OUT_LEN >= 2)
                    {
                        bool is_engaged = out[1] > out[0];
                        Serial.print(",\"classification\":");
                        Serial.print(is_engaged ? "1" : "0");
                        Serial.print(",\"label\":\"");
                        Serial.print(is_engaged ? "engaged" : "neutral");
                        Serial.print("\"");
                    }
                }
                Serial.print("},\"frame_data\":\"");
                
                // Encode 96x96 cropped and scaled top-right quarter frame data as hex string
                uint8_t *frameData = fb.getBuffer();
                uint32_t cam_width = 160;  // QQVGA width
                uint32_t cam_height = 120; // QQVGA height
                uint32_t target_size = 96;
                
                // Crop top-right quarter: start from right half, top half
                uint32_t crop_x = cam_width / 2;  // Start from right half (80)
                uint32_t crop_y = 0;              // Start from top half
                
                // Resize the 80x60 top-right quarter to 96x96
                float scale_x = (float)(cam_width / 2) / (float)target_size;  // 80/96 = 0.83
                float scale_y = (float)(cam_height / 2) / (float)target_size; // 60/96 = 0.625
                
                for (uint32_t y = 0; y < target_size; y++)
                {
                    for (uint32_t x = 0; x < target_size; x++)
                    {
                        // Calculate source coordinates with scaling
                        uint32_t src_x = crop_x + (uint32_t)(x * scale_x);
                        uint32_t src_y = crop_y + (uint32_t)(y * scale_y);
                        
                        // Clamp to valid range
                        if (src_x >= cam_width) src_x = cam_width - 1;
                        if (src_y >= cam_height) src_y = cam_height - 1;
                        
                        uint32_t src_idx = src_y * cam_width + src_x;
                        uint8_t pixel = frameData[src_idx];
                        if (pixel < 16) Serial.print("0");
                        Serial.print(pixel, HEX);
                    }
                }
                
                Serial.println("\"}");
            }
        }
        delay(1000); // ~1 FPS as requested
    }
    else
    {
        delay(100);
    }
}
