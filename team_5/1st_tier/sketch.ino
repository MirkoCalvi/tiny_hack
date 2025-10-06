/*
  Nicla Vision Melanoma Triage System
  
  Proximity-based skin lesion classification system using ML inference and WiFi upload.
  
  Features:
  - VL53L1X proximity sensor ensures optimal distance (30-50mm)
  - GC2145 camera captures 320x320 RGB565 images
  - Zant-compiled melanoma classifier (96x96x3 NCHW input)
  - WiFi upload to Flask server for suspicious lesions
  - Demo mode: uploads every 5th capture regardless of classification
  
  LED Status:
  - Yellow (R+G): Waiting for optimal distance (30-50mm)
  - Blue: Processing image and running inference
  - Red: Malignant detection (≥65% threshold) - always uploads
  - Green: Benign detection - uploads every 5th capture (demo mode)
  
  Hardware:
  - Arduino Nicla Vision (STM32H747 Cortex-M7)
  - VL53L1X proximity sensor (built-in I2C on Wire1)
  - GC2145 camera sensor
  - WiFi connection required
*/

#include <Arduino.h>
#include <WiFi.h>
#include "camera.h"
#include "gc2145.h"
#include <VL53L1X.h>  // Proximity sensor library

#include <lib_melanoma_classifier.h>  // Your melanoma classifier

// Camera instance with GC2145 sensor (Nicla Vision's camera)
GC2145 galaxyCore;
Camera cam(galaxyCore);

// Frame buffer: 320x320 RGB565 = 204,800 bytes
FrameBuffer fb(320, 320, 2);

// -----------------------------------------------------------------------------
// WiFi & Server Configuration
// -----------------------------------------------------------------------------
constexpr char WIFI_SSID[] = "toolbox";
constexpr char WIFI_PASS[] = "Toolbox.Torino";

constexpr char SERVER_HOST[] = "10.100.15.27";
constexpr uint16_t SERVER_PORT = 8000;
constexpr char SERVER_ENDPOINT[] = "/ingest";

// -----------------------------------------------------------------------------
// Proximity Sensor Configuration
// -----------------------------------------------------------------------------
constexpr uint16_t MIN_DISTANCE_MM = 30;
constexpr uint16_t MAX_DISTANCE_MM = 50;
constexpr uint16_t DISTANCE_TIMEOUT_MS = 100;
constexpr unsigned long DISTANCE_CHECK_INTERVAL_MS = 200;

// -----------------------------------------------------------------------------
// Inference & Timing Parameters
// -----------------------------------------------------------------------------
constexpr float ALERT_THRESHOLD = 0.65f;
constexpr unsigned long NEXT_CASE_DELAY_MS = 4000;
constexpr unsigned long WIFI_RETRY_DELAY_MS = 5000;

// Model input dimensions (NCHW format)
constexpr int MODEL_IMAGE_WIDTH = 96;
constexpr int MODEL_IMAGE_HEIGHT = 96;
constexpr int MODEL_IMAGE_CHANNELS = 3;
constexpr int MODEL_INPUT_SIZE = MODEL_IMAGE_WIDTH * MODEL_IMAGE_HEIGHT * MODEL_IMAGE_CHANNELS;
static uint32_t MODEL_INPUT_SHAPE[] = {1, MODEL_IMAGE_CHANNELS, MODEL_IMAGE_HEIGHT, MODEL_IMAGE_WIDTH};
constexpr size_t MODEL_INPUT_DIMS = sizeof(MODEL_INPUT_SHAPE) / sizeof(MODEL_INPUT_SHAPE[0]);
constexpr int MODEL_OUTPUT_CLASSES = 2;
constexpr float PIXEL_SCALE = 1.0f / 255.0f;

// Camera configuration
constexpr int CAMERA_INFERENCE_RES = CAMERA_R320x320;
constexpr int CAMERA_INFERENCE_FMT = CAMERA_RGB565;
constexpr int CAMERA_UPLOAD_RES = CAMERA_R320x320;
constexpr int CAMERA_UPLOAD_FMT = CAMERA_RGB565;
constexpr int CAMERA_WIDTH_QVGA = 320;
constexpr int CAMERA_HEIGHT_QVGA = 320;

// Buffers
static float model_input_buffer[MODEL_INPUT_SIZE];
static float* model_output = nullptr;

// Payload structure for server upload
struct CapturePayload {
  const uint8_t* data;
  size_t length;
};

// Proximity sensor instance
VL53L1X proximitySensor;

// System state machine
enum SystemState {
  STATE_WAITING_DISTANCE,
  STATE_PROCESSING,
  STATE_ALERT,
  STATE_CLEAR
};

SystemState currentState = STATE_WAITING_DISTANCE;
unsigned long lastDistanceCheck = 0;

// Demo mode: upload every 5th capture
static uint32_t capture_counter = 0;
constexpr uint32_t UPLOAD_EVERY_N = 5;

// -----------------------------------------------------------------------------
// LED Control (active low)
// -----------------------------------------------------------------------------
void setLedColor(bool red_on, bool green_on, bool blue_on) {
  digitalWrite(LEDR, red_on ? LOW : HIGH);
  digitalWrite(LEDG, green_on ? LOW : HIGH);
  digitalWrite(LEDB, blue_on ? LOW : HIGH);
}

void indicateIdle() { setLedColor(false, false, false); }
void indicateWaitingDistance() {
  digitalWrite(LEDR, LOW);   // Yellow = Red + Green
  digitalWrite(LEDG, LOW);
  digitalWrite(LEDB, HIGH);
}
void indicateProcessing() { setLedColor(false, false, true); }
void indicateClear() { setLedColor(false, true, false); }
void indicateAlert() { setLedColor(true, false, false); }

// -----------------------------------------------------------------------------
// Proximity Sensor
// -----------------------------------------------------------------------------
bool initProximitySensor() {
  Wire1.begin();
  Wire1.setClock(400000);
  
  proximitySensor.setBus(&Wire1);
  
  if (!proximitySensor.init()) {
    Serial.println("ERROR: Failed to initialize VL53L1X");
    return false;
  }
  
  proximitySensor.setDistanceMode(VL53L1X::Short);
  proximitySensor.setMeasurementTimingBudget(50000);
  proximitySensor.startContinuous(50);
  
  Serial.println("Proximity sensor initialized");
  return true;
}

uint16_t readDistance() {
  proximitySensor.read();
  
  if (proximitySensor.timeoutOccurred()) {
    Serial.println("WARNING: Proximity sensor timeout");
    return 0xFFFF;
  }
  
  return proximitySensor.ranging_data.range_mm;
}

bool isDistanceOptimal(uint16_t distance_mm) {
  if (distance_mm == 0xFFFF) {
    return false;
  }
  return (distance_mm >= MIN_DISTANCE_MM && distance_mm <= MAX_DISTANCE_MM);
}

// -----------------------------------------------------------------------------
// WiFi Connection
// -----------------------------------------------------------------------------
void connectToWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.disconnect();

  while (WiFi.begin(WIFI_SSID, WIFI_PASS) != WL_CONNECTED) {
    Serial.println("  • Connection failed, retrying...");
    delay(WIFI_RETRY_DELAY_MS);
  }

  Serial.print("Connected! IP address: ");
  Serial.println(WiFi.localIP());
}

// -----------------------------------------------------------------------------
// Image Processing: RGB565 to NCHW Float32
// -----------------------------------------------------------------------------
void downscaleToModelInput(const uint8_t* rgb565, int src_width, int src_height) {
  const int stride_x = (src_width << 8) / MODEL_IMAGE_WIDTH;
  const int stride_y = (src_height << 8) / MODEL_IMAGE_HEIGHT;

  for (int y = 0; y < MODEL_IMAGE_HEIGHT; ++y) {
    const int src_y = (y * stride_y) >> 8;
    for (int x = 0; x < MODEL_IMAGE_WIDTH; ++x) {
      const int src_x = (x * stride_x) >> 8;
      const uint16_t pixel = reinterpret_cast<const uint16_t*>(rgb565)[src_y * src_width + src_x];
      
      // Extract RGB565 components
      const uint8_t r5 = (pixel >> 11) & 0x1F;
      const uint8_t g6 = (pixel >> 5) & 0x3F;
      const uint8_t b5 = pixel & 0x1F;

      // Convert to 8-bit RGB
      const uint8_t r8 = static_cast<uint8_t>((r5 << 3) | (r5 >> 2));
      const uint8_t g8 = static_cast<uint8_t>((g6 << 2) | (g6 >> 4));
      const uint8_t b8 = static_cast<uint8_t>((b5 << 3) | (b5 >> 2));

      // Store in NCHW format: all R channel, then all G channel, then all B channel
      // Channel 0 (R): indices 0 to (96*96-1)
      // Channel 1 (G): indices (96*96) to (2*96*96-1)
      // Channel 2 (B): indices (2*96*96) to (3*96*96-1)
      const size_t hw_offset = static_cast<size_t>(y) * MODEL_IMAGE_WIDTH + static_cast<size_t>(x);
      const size_t channel_size = MODEL_IMAGE_WIDTH * MODEL_IMAGE_HEIGHT;
      
      model_input_buffer[hw_offset] = static_cast<float>(r8) * PIXEL_SCALE;                      // R channel
      model_input_buffer[channel_size + hw_offset] = static_cast<float>(g8) * PIXEL_SCALE;       // G channel
      model_input_buffer[2 * channel_size + hw_offset] = static_cast<float>(b8) * PIXEL_SCALE;  // B channel
    }
  }
}

// -----------------------------------------------------------------------------
// ML Inference
// -----------------------------------------------------------------------------
static void softmax(float* output, int len) {
    float max_val = output[0];
    for (int i = 1; i < len; i++) {
        if (output[i] > max_val) max_val = output[i];
    }
    
    float sum = 0.0f;
    for (int i = 0; i < len; i++) {
        output[i] = exp(output[i] - max_val);
        sum += output[i];
    }
    
    for (int i = 0; i < len; i++) {
        output[i] /= sum;
    }
}

float runInference() {
  const int status = predict(model_input_buffer, MODEL_INPUT_SHAPE,
                             static_cast<uint32_t>(MODEL_INPUT_DIMS), &model_output);
  if (status != 0 || model_output == nullptr) {
    Serial.print("ERROR: predict() failed with code ");
    Serial.println(status);
    return 0.0f;
  }

  Serial.println("Raw logits:");
  Serial.print("  Benign: ");
  Serial.println(model_output[0], 6);
  Serial.print("  Malignant: ");
  Serial.println(model_output[1], 6);

  float probs[MODEL_OUTPUT_CLASSES];
  for (int i = 0; i < MODEL_OUTPUT_CLASSES; i++) {
    probs[i] = model_output[i];
  }
  softmax(probs, MODEL_OUTPUT_CLASSES);

  Serial.println("Probabilities:");
  Serial.print("  Benign: ");
  Serial.print(probs[0] * 100.0f, 2);
  Serial.println("%");
  Serial.print("  Malignant: ");
  Serial.print(probs[1] * 100.0f, 2);
  Serial.println("%");

  const float suspicious_score = probs[1];
  return constrain(suspicious_score, 0.0f, 1.0f);
}

// -----------------------------------------------------------------------------
// Server Upload
// -----------------------------------------------------------------------------
bool sendAlertToServer(const uint8_t* jpeg_data, size_t jpeg_len, float score) {
  WiFiClient client;
  if (!client.connect(SERVER_HOST, SERVER_PORT)) {
    Serial.println("ERROR: Cannot reach server");
    return false;
  }
  
  Serial.println("Connected to server");

  char metadata[256];
  snprintf(metadata, sizeof(metadata),
           "{\"device_id\":\"nicla-vision\",\"score\":%.3f,\"timestamp\":%lu,\"width\":%d,\"height\":%d,\"format\":\"rgb565\"}",
           score, millis(), CAMERA_WIDTH_QVGA, CAMERA_HEIGHT_QVGA);

  const char boundary[] = "----NICLAHACKATHONBOUNDARY";

  String body_header;
  body_header.reserve(256);
  body_header += "--";
  body_header += boundary;
  body_header += "\r\nContent-Disposition: form-data; name=\"metadata\"\r\n\r\n";
  body_header += metadata;
  body_header += "\r\n--";
  body_header += boundary;
  body_header += "\r\nContent-Disposition: form-data; name=\"image\"; filename=\"capture.rgb565\"\r\n";
  body_header += "Content-Type: application/octet-stream\r\n\r\n";

  const String body_footer = String("\r\n--") + boundary + "--\r\n";

  const size_t content_length = body_header.length() + jpeg_len + body_footer.length();

  client.print("POST ");
  client.print(SERVER_ENDPOINT);
  client.println(" HTTP/1.1");
  client.print("Host: ");
  client.print(SERVER_HOST);
  client.print(":");
  client.println(SERVER_PORT);
  client.println("Connection: close");
  client.print("Content-Type: multipart/form-data; boundary=");
  client.println(boundary);
  client.print("Content-Length: ");
  client.println(content_length);
  client.println();

  Serial.print("Sending body_header (");
  Serial.print(body_header.length());
  Serial.println(" bytes)");
  client.print(body_header);
  client.write(jpeg_data, jpeg_len);
  client.print(body_footer);
  client.flush();
  
  Serial.print("Sent ");
  Serial.print(content_length);
  Serial.println(" bytes");

  unsigned long deadline = millis() + 5000;
  while (client.connected() && millis() < deadline) {
    while (client.available()) {
      Serial.write(client.read());
    }
  }
  client.stop();
  return true;
}

// -----------------------------------------------------------------------------
// Camera Capture
// -----------------------------------------------------------------------------
bool captureInferenceFrame() {
  int retries = 3;
  int capture_result = -1;
  
  for (int attempt = 0; attempt < retries; attempt++) {
    if (attempt > 0) {
      Serial.print("Retry ");
      Serial.println(attempt);
      delay(200);
    }
    
    capture_result = cam.grabFrame(fb, 5000);
    
    if (capture_result == 0 && fb.getBufferSize() > 0 && fb.getBuffer() != nullptr) {
      Serial.print("Captured ");
      Serial.print(fb.getBufferSize());
      Serial.println(" bytes");
      break;
    }
  }
  
  if (capture_result != 0 || fb.getBufferSize() == 0 || fb.getBuffer() == nullptr) {
    Serial.println("ERROR: Capture failed");
    return false;
  }
  
  downscaleToModelInput(fb.getBuffer(), CAMERA_WIDTH_QVGA, CAMERA_HEIGHT_QVGA);
  return true;
}

bool captureHighResolutionJPEG(CapturePayload& out) {
  if (cam.grabFrame(fb, 3000) != 0) {
    Serial.println("ERROR: Upload capture failed");
    return false;
  }
  
  out.data = fb.getBuffer();
  out.length = fb.getBufferSize();
  
  if (out.length == 0 || out.data == nullptr) {
    Serial.println("ERROR: Invalid buffer");
    return false;
  }
  
  return true;
}

// -----------------------------------------------------------------------------
// Main Processing (triggered when distance is optimal)
// -----------------------------------------------------------------------------
void processCapture() {
  indicateProcessing();
  
  capture_counter++;
  Serial.print("=== Capture #");
  Serial.print(capture_counter);
  Serial.println(" ===");

  if (!captureInferenceFrame()) {
    indicateIdle();
    delay(500);
    currentState = STATE_WAITING_DISTANCE;
    return;
  }

  const float suspicious_score = runInference();
  Serial.print("Malignant score: ");
  Serial.print(suspicious_score * 100.0f, 2);
  Serial.println("%");

  bool should_upload_demo = (capture_counter % UPLOAD_EVERY_N == 0);

  if (suspicious_score >= ALERT_THRESHOLD) {
    currentState = STATE_ALERT;
    indicateAlert();
    Serial.println("ALERT: Uploading malignant detection");
    
    CapturePayload payload{};
    if (captureHighResolutionJPEG(payload)) {
      sendAlertToServer(payload.data, payload.length, suspicious_score);
    }
    
    delay(NEXT_CASE_DELAY_MS);
    currentState = STATE_WAITING_DISTANCE;
    indicateIdle();
  } else if (should_upload_demo) {
    currentState = STATE_CLEAR;
    indicateClear();
    Serial.println("DEMO: Uploading benign (every 5th)");
    
    CapturePayload payload{};
    if (captureHighResolutionJPEG(payload)) {
      sendAlertToServer(payload.data, payload.length, suspicious_score);
    }
    
    delay(NEXT_CASE_DELAY_MS);
    currentState = STATE_WAITING_DISTANCE;
    indicateIdle();
  } else {
    currentState = STATE_CLEAR;
    indicateClear();
    Serial.println("Benign - no upload");
    
    delay(NEXT_CASE_DELAY_MS);
    currentState = STATE_WAITING_DISTANCE;
    indicateIdle();
  }
}

// -----------------------------------------------------------------------------
// Setup
// -----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;
  }

  Serial.println("=== Nicla Vision Melanoma Triage System ===");

  pinMode(LEDR, OUTPUT);
  pinMode(LEDG, OUTPUT);
  pinMode(LEDB, OUTPUT);
  indicateIdle();

  if (!initProximitySensor()) {
    Serial.println("FATAL: Proximity sensor failed");
    while (true) {
      setLedColor(true, false, false);
      delay(500);
      setLedColor(false, false, false);
      delay(500);
    }
  }

  if (!cam.begin(CAMERA_INFERENCE_RES, CAMERA_INFERENCE_FMT, 15)) {
    Serial.println("FATAL: Camera failed");
    while (true) {
      delay(1000);
    }
  }
  
  Serial.println("Warming up camera...");
  for (int i = 0; i < 3; i++) {
    delay(100);
    cam.grabFrame(fb, 3000);
  }
  Serial.println("Camera ready");

  connectToWiFi();

  Serial.println("Ready - waiting for optimal distance (30-50mm)");
  indicateWaitingDistance();
}

// -----------------------------------------------------------------------------
// Main Loop
// -----------------------------------------------------------------------------
void loop() {
  connectToWiFi();

  unsigned long currentTime = millis();
  
  if (currentTime - lastDistanceCheck >= DISTANCE_CHECK_INTERVAL_MS) {
    lastDistanceCheck = currentTime;
    
    uint16_t distance = readDistance();
    
    if (distance != 0xFFFF) {
      Serial.print("Distance: ");
      Serial.print(distance);
      Serial.println(" mm");
    }
    
    if (currentState == STATE_WAITING_DISTANCE) {
      if (isDistanceOptimal(distance)) {
        currentState = STATE_PROCESSING;
        processCapture();
      } else {
        indicateWaitingDistance();
      }
    }
  }
  
  delay(10);
}
