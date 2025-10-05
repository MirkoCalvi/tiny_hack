#include <ArduinoJson.h>
#include <ArduinoHttpClient.h>
#include <Arduino.h>
#include <Arduino_LSM6DSOX.h>
#include <math.h>
#include <ArduinoBLE.h>
#include <lib_zant.h>
#include "variables.h"


// Forward declarations
const char* stateToString(State state);
void changeState(State newState);
void notifyStateChange(State state);

// Bluetooth function declarations (defined in bluetooth_central.ino)
bool initBluetooth();
bool connectToPeripheral(const char* deviceName);
bool checkBluetoothConnection();
float distance();
void disconnectBluetooth();


static unsigned long roll_out_start_ms = 0;
static bool was_roll_out = false;
static bool roll_out_triggered = false;

HttpClient client = HttpClient(wifi, server, port);

// ***** FUNCTIONS *****
const char* stateToString(State state) 
{
  switch (state) {
    case IDLE:
      return "idle";
    case CONNECTING:
      return "connecting";
    case CALIBRATING:
      return "calibrating";
    case RUNNING:
      return "running";
    default:
      return "unknown";
  }
}

void calibrateGyro() 
{
  float sx=0, sy=0, sz=0;
  uint16_t n=0;
  unsigned long t0 = millis();
  while (n < CAL_SAMPLES && (millis() - t0) < 2000) {
    if (IMU.gyroscopeAvailable()) {
      float gx, gy, gz;
      IMU.readGyroscope(gx, gy, gz);
      sx += gx; sy += gy; sz += gz;
      n++;
    }
  }
  if (n > 0) {
    gxBias = sx / n;
    gyBias = sy / n;
    gzBias = sz / n;
  }
}

float getRoll()
{
  unsigned long now = micros();
  float dt = (now - last_us) * 1e-6f;
  if (dt <= 0.0f || dt > 0.2f) dt = 0.01f;
  last_us = now;

  float ax, ay, az, gx, gy, gz;
  bool haveAcc = false, haveGyro = false;

  if (IMU.gyroscopeAvailable()) {
    IMU.readGyroscope(gx, gy, gz);
    gx -= gxBias; gy -= gyBias; gz -= gzBias;
    haveGyro = true;
  }
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);
    haveAcc = true;
  }

  if (haveGyro) {
    roll_deg += gx * dt;
  }

  if (haveAcc) {
    float accRoll = rad2deg(atan2f(ay, az));
    accRoll_lpf_deg += ACC_LPF_ALPHA * (accRoll - accRoll_lpf_deg);

    float gyroMag = sqrtf(gx*gx + gy*gy + gz*gz);
    float accMag  = sqrtf(ax*ax + ay*ay + az*az);
    bool isStatic = (gyroMag < GYRO_STATIC_TH) && (fabsf(accMag - 1.0f) < ACC_STATIC_TH);

    float alpha = isStatic ? COMP_ALPHA_STATIC : COMP_ALPHA_MOVING;
    roll_deg = alpha * roll_deg + (1.0f - alpha) * accRoll_lpf_deg;
  }
  return roll_deg;
}

static inline float rad2deg(float r){ return r * (180.0f / PI); }

void connectToWiFi() 
{
  WiFi.disconnect();
  delay(100);
  
  Serial.print("Connecting to WiFi: ");
  // Serial.println(ssid);
  // Serial.println(password);
  if(WiFi.begin(ssid, password) == 0) {
    Serial.println("OK!");
    //printMemoryState();
  }
  
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConnected to WiFi!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect to WiFi");
  }
}

void registerArduino() 
{
  Serial.println("Registering with server...");
  
  DynamicJsonDocument doc(1024);
  doc["arduino_id"] = arduinoId;
  doc["timestamp"] = millis();
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  client.setTimeout(5000);
  client.post("/api/register_arduino", "application/json", jsonString);
  
  int statusCode = client.responseStatusCode();
  String response = client.responseBody();
  
  Serial.print("Registration status: ");
  Serial.println(statusCode);
  Serial.print("Response: ");
  Serial.println(response);
  
  client.stop();
}

void pollForCommands() 
{
  String endpoint = "/api/poll?arduino_id=" + arduinoId;
  
  client.setTimeout(5000);
  int err = client.get(endpoint);
  
  if (err != 0) {
    Serial.print("Poll connection error: ");
    Serial.println(err);
    client.stop();
    return;
  }
  
  int statusCode = client.responseStatusCode();
  
  if (statusCode == 200) {
    String response = client.responseBody();
    
    if (response.length() > 0) {
      processCommand(response);
    }
  } else if (statusCode != 204) {
    Serial.print("Poll status error: ");
    Serial.println(statusCode);
  }
  
  client.stop();
}

void processCommand(String jsonResponse) 
{
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, jsonResponse);
  
  if (error) {
    Serial.print("JSON parsing failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  const char* command = doc["command"];
  
  if (command == nullptr) {
    return;
  }
  
  Serial.print("Received command: ");
  Serial.println(command);
  
  if (strcmp(command, "start") == 0) {
    handleStartCommand();
  } else if (strcmp(command, "send_picture") == 0) {
    handleSendPictureCommand();
  } else if (strcmp(command, "approved") == 0) {
    handleApprovedSignal();
  } else if (strcmp(command, "not_approved") == 0) {
    handleNotApprovedSignal();
  }
}

void handleStartCommand() 
{
  Serial.println("Processing START command");
  
  if (currentState == IDLE) {
    changeState(CONNECTING);
  } else {
    Serial.println("ERROR: Cannot start from current state");
    sendError("Cannot start from current state");
  }
}

void handleConnectingState() 
{
  static unsigned long connectStartTime = 0;
  static bool connecting = false;
  
  if (!connecting) {
    connecting = true;
    connectStartTime = millis();
    Serial.println("Attempting to connect to Bluetooth device...");
    
    // Initialize Bluetooth
    if (!initBluetooth()) {
      Serial.println("Failed to initialize Bluetooth!");
      sendError("Bluetooth initialization failed");
      changeState(IDLE);
      connecting = false;
      return;
    }
    
    // Try to connect to peripheral (replace "YourDeviceName" with actual device name)
    if (connectToPeripheral("NiclaVision_1")) {
      Serial.println("Bluetooth connection established!");
      connecting = false;
      changeState(RUNNING);
    } else {
      Serial.println("Failed to connect to Bluetooth device!");
      sendError("Bluetooth connection failed");
      changeState(IDLE);
      connecting = false;
    }
  }
}

void handleSendPictureCommand() 
{
  Serial.println("Processing SEND_PICTURE command");
  
  if (currentState == CALIBRATING) {
    takePicture();
  } else {
    Serial.println("ERROR: Not in CALIBRATING state");
    sendError("Not in calibrating state");
  }
}

void takePicture() 
{


  // CHANGE
  Serial.println("Taking picture...");
  delay(500);
  sendPictureToFrontend();
  Serial.println("Picture sent to frontend");
}

void sendPictureToFrontend() 
{
  DynamicJsonDocument doc(2048);
  doc["arduino_id"] = arduinoId;
  doc["timestamp"] = millis();
  doc["format"] = "jpeg";
  doc["data"] = "dummy_image_data_base64_encoded";
  doc["width"] = 320;
  doc["height"] = 240;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  client.setTimeout(5000);
  client.post("/api/picture", "application/json", jsonString);
  
  int statusCode = client.responseStatusCode();
  Serial.print("Picture upload status: ");
  Serial.println(statusCode);
  
  client.stop();
}

void handleApprovedSignal() 
{
  Serial.println("Processing APPROVED signal");
  
  if (currentState == CALIBRATING) {
    changeState(RUNNING);
  } else {
    Serial.println("ERROR: Not in CALIBRATING state");
    sendError("Not in calibrating state for approval");
  }
}

void handleNotApprovedSignal() 
{
  Serial.println("Processing NOT_APPROVED signal");
  
  if (currentState == CALIBRATING) {
    Serial.println("Picture not approved, waiting for new send_picture command");
    // Stay in CALIBRATING state and wait for another send_picture command
  } else {
    Serial.println("ERROR: Not in CALIBRATING state");
    sendError("Not in calibrating state");
  }
}

void changeState(State newState) 
{
  State oldState = currentState;
  currentState = newState;
  
  Serial.print("State changed: ");
  Serial.print(stateToString(oldState));
  Serial.print(" -> ");
  Serial.println(stateToString(newState));
  
  notifyStateChange(newState);
}

void notifyStateChange(State state) 
{
  DynamicJsonDocument doc(1024);
  doc["arduino_id"] = arduinoId;
  doc["state"] = stateToString(state);
  doc["timestamp"] = millis();
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  client.setTimeout(5000);
  client.post("/api/state_change", "application/json", jsonString);
  
  int statusCode = client.responseStatusCode();
  Serial.print("State change notification status: ");
  Serial.println(statusCode);
  
  client.stop();
}

void sendError(const char* errorMessage)
{
  DynamicJsonDocument doc(1024);
  doc["arduino_id"] = arduinoId;
  doc["message"] = errorMessage;
  doc["state"] = stateToString(currentState);
  doc["timestamp"] = millis();
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  client.setTimeout(5000);
  client.post("/api/error", "application/json", jsonString);
  
  Serial.print("Error sent: ");
  Serial.println(errorMessage);
  
  client.stop();
}

void setAngle()
{
  if (!IMU.begin()) {
    while (1);
  }
  calibrateGyro();
  rif_roll = getRoll();
  rif_roll = abs(rif_roll);
  rif_roll *= 10;
  Serial.print("Fixed angle: ");
  Serial.println(rif_roll, 2);
}

void mainLoop() 
{

    roll = getRoll();

    // uint8_t image[96*96*3];  // RGB interleaved
    // float input[27648];
    // prepareInput(image, 96, 96, input);
    // uint32_t shape[4] = {1, 3, 96, 96};
    // float* result = NULL;




    if (cam.grabFrame(fb, 3000) != 0){
        delay(5);
    return;
    }
    const uint8_t* buf = fb.getBuffer();

    // Preprocess: NCHW (float 0..1) + gray preview
    resize_rgb565_to_96x96_rgbNCHW_and_gray_NEAREST(buf, 320, 240, gInput, gGray8);

    // Inference
    float* out_raw = nullptr;
    unsigned long t0 = micros();
    //int rc = predict(gInput, inputShape, 4, &out_raw); 
      //  Serial.print(rc);


    model_distracted = predict(gInput, inputShape, 4, &out_raw); 
    Serial.println(model_distracted);

    // distance calculated with bluetooth
    dist = distance();

    unsigned long grace_ms;
    if (dist > 10.0f) {
      grace_ms = 2000UL;
    } else if (dist < 1.0f) {
      grace_ms = 5000UL;
    } else {
      float ms = 5000.0f + ((dist - 1.0f) * (-4000.0f / 9.0f));
      grace_ms = (ms > 0.0f) ? (unsigned long)(ms + 0.5f) : 0UL;
    }

    bool roll_out_now = (fabs(roll - rif_roll) >= delta_degree);

    if (roll_out_now) {
      if (!was_roll_out) {
        was_roll_out = true;
        roll_out_start_ms = millis();
      }
      if (!roll_out_triggered) {
        unsigned long elapsed = millis() - roll_out_start_ms;
        if (elapsed >= grace_ms) roll_out_triggered = true;
      }
    } else {
      was_roll_out = false;
      roll_out_triggered = false;
    }

    // Person can be distracted either by the negative classification or due to the imu
    bool distracted = (model_distracted == 0) || roll_out_triggered;

    if (distracted) {
      digitalWrite(LEDB, LOW);
      digitalWrite(LEDR, HIGH);
      
      for (;;) {
        if (cam.grabFrame(fb, 3000) != 0){
          delay(5);
          return;
        }
        const uint8_t* buf = fb.getBuffer();

        // Preprocess: NCHW (float 0..1) + gray preview
        resize_rgb565_to_96x96_rgbNCHW_and_gray_NEAREST(buf, 320, 240, gInput, gGray8);

        // Inference
        float* out_raw = nullptr;
        unsigned long t0 = micros();

        int   m2   = predict(gInput, inputShape, 4, &out_raw); 
        float r2   = getRoll();
        bool roll_ok = (fabs(r2 - rif_roll) < delta_degree);
        if (m2 == 1 && roll_ok) break;
        delay(20);
      }

      digitalWrite(LEDR, LOW);
      digitalWrite(LEDB, HIGH);

      was_roll_out = false;
      roll_out_triggered = false;
    }
}
