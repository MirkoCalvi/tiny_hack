#include <WiFi.h>
#include <WiFiClient.h>
#include <camera.h>
#include <gc2145.h>
#include <cmath>
#include "lib_hands.h"
#include "lib_zant.h"

static const char *WIFI_SSID = "Galaxy A54 5G C365";
static const char *WIFI_PASSWORD = "Pizza1234";

static const char *SERVER_HOST = "192.168.204.232";
static const uint16_t SERVER_PORT = 9000;

static const uint16_t TARGET_W = 96;
static const uint16_t TARGET_H = 96;

static float inputTensor[HANDS_INPUT_LENGTH];
static uint32_t inputShape[4] = {1, 3, TARGET_H, TARGET_W};
static const char *GESTURE_LABELS[HANDS_OUTPUT_LENGTH] = {
  "1", "2", "3",
};

GC2145 sensor;
Camera camera(sensor);
FrameBuffer frameBuffer(160, 120, 2);
WiFiClient client;

extern "C" const uint8_t *const flash_weights_base = (const uint8_t *)0x90000000UL;

static bool ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < 20000UL) {
    delay(250);
  }
  return WiFi.status() == WL_CONNECTED;
}

static bool ensureServer() {
  if (client.connected()) {
    return true;
  }
  if (!client.connect(SERVER_HOST, SERVER_PORT)) {
    return false;
  }
  client.println("{\"type\":\"hello\",\"device\":\"nicla-vision-hands\"}");
  return true;
}

static void sendJson(const String &payload) {
  if (!client.connected()) {
    return;
  }
  client.println(payload);
}

static inline int clampi(int v, int lo, int hi) {
  if (v < lo) {
    return lo;
  }
  if (v > hi) {
    return hi;
  }
  return v;
}

static void convertToTensor(const uint8_t *src, uint32_t srcWidth, uint32_t srcHeight) {
  const size_t plane = TARGET_W * TARGET_H;
  float *dstR = inputTensor;
  float *dstG = inputTensor + plane;
  float *dstB = inputTensor + 2 * plane;

  static constexpr float MEAN_R = 123.675f;
  static constexpr float MEAN_G = 116.280f;
  static constexpr float MEAN_B = 103.530f;
  static constexpr float STD_R  = 58.395f;
  static constexpr float STD_G  = 57.120f;
  static constexpr float STD_B  = 57.375f;

  const uint32_t cropSize = (srcWidth < srcHeight) ? srcWidth : srcHeight;
  const uint32_t offsetX = (srcWidth > cropSize) ? (srcWidth - cropSize) / 2 : 0;
  const uint32_t offsetY = (srcHeight > cropSize) ? (srcHeight - cropSize) / 2 : 0;
  const float sx = static_cast<float>(cropSize) / static_cast<float>(TARGET_W);
  const float sy = static_cast<float>(cropSize) / static_cast<float>(TARGET_H);
  const int cropMax = static_cast<int>(cropSize) - 1;

  for (uint16_t y = 0; y < TARGET_H; ++y) {
    int sampleY = clampi(static_cast<int>(std::floor((static_cast<float>(y) + 0.5f) * sy)), 0, cropMax);
    uint32_t srcY = offsetY + static_cast<uint32_t>(sampleY);
    for (uint16_t x = 0; x < TARGET_W; ++x) {
      int sampleX = clampi(static_cast<int>(std::floor((static_cast<float>(x) + 0.5f) * sx)), 0, cropMax);
      uint32_t srcX = offsetX + static_cast<uint32_t>(sampleX);
      size_t srcIdx = (static_cast<size_t>(srcY) * srcWidth + srcX) << 1;
      uint16_t pixel = (static_cast<uint16_t>(src[srcIdx]) << 8) | src[srcIdx + 1];

      uint8_t r = ((pixel >> 11) & 0x1F) << 3;
      uint8_t g = ((pixel >> 5) & 0x3F) << 2;
      uint8_t b = (pixel & 0x1F) << 3;

      size_t dstIndex = y * TARGET_W + x;
      dstR[dstIndex] = (static_cast<float>(r) - MEAN_R) / STD_R;
      dstG[dstIndex] = (static_cast<float>(g) - MEAN_G) / STD_G;
      dstB[dstIndex] = (static_cast<float>(b) - MEAN_B) / STD_B;
    }
  }
}

static bool captureFrame() {
  if (camera.grabFrame(frameBuffer, 200) != 0) {
    return false;
  }
  const uint8_t *raw = frameBuffer.getBuffer();
  if (!raw) {
    return false;
  }
  uint32_t srcWidth = camera.getResolutionWidth();
  uint32_t srcHeight = camera.getResolutionHeight();
  if (srcWidth == 0 || srcHeight == 0) {
    return false;
  }
  convertToTensor(raw, srcWidth, srcHeight);
  return true;
}

static void runInference() {
  float *result = nullptr;
  int rc = predict(inputTensor, inputShape, 4, &result);
  if (rc != 0 || result == nullptr) {
    sendJson("{\"type\":\"error\",\"device\":\"nicla-vision-hands\",\"code\":" + String(rc) + "}");
    return;
  }

  size_t best = 0;
  float bestVal = result[0];
  float sum = result[0];
  for (size_t i = 1; i < HANDS_OUTPUT_LENGTH; ++i) {
    sum += result[i];
    if (result[i] > bestVal) {
      bestVal = result[i];
      best = i;
    }
  }
  float confidence = (sum > 0.0f) ? (bestVal / sum) : 0.0f;

  String payload = "{\"type\":\"hand\",\"device\":\"nicla-vision-hands\",\"id\":\"hand\"," \
                   "\"gesture\":\"" + String(GESTURE_LABELS[best]) + "\",\"confidence\":" + String(confidence, 3) + "," \
                   "\"x\":0.0,\"y\":0.0,\"z\":0.0}";
  sendJson(payload);

  zant_free_result(result);
}

void setup() {
  zant_set_weights_base_address(flash_weights_base);
  Serial.begin(115200);
  while (!Serial && millis() < 5000) { }

  if (!camera.begin(CAMERA_R160x120, CAMERA_RGB565, 30)) {
    Serial.println("Camera init failed");
    while (true) {
      delay(1000);
    }
  }
  //camera.zoomToCenter(CAMERA_R320x240);

  if (!ensureWiFi()) {
    Serial.println("WiFi failed");
  }
}

void loop() {
  if (!ensureWiFi()) {
    delay(1000);
    return;
  }
  ensureServer();

  if (captureFrame()) {
    runInference();
  }

  delay(200);
}
