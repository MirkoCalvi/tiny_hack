#include "variables.h"

// ***** IMU & Roll Calculation Constants *****
const float COMP_ALPHA_MOVING = 0.98f;
const float COMP_ALPHA_STATIC = 0.02f;
const float ACC_LPF_ALPHA     = 0.10f;
const float GYRO_STATIC_TH    = 1.5f;   // deg/s
const float ACC_STATIC_TH     = 0.06f;  // g
const uint32_t PRINT_US       = 20000;  // 50 Hz
const uint16_t CAL_SAMPLES    = 400;

// IMU state variables
float roll_deg = 0.0f;
float accRoll_lpf_deg = 0.0f;
float gxBias = 0.0f, gyBias = 0.0f, gzBias = 0.0f;

unsigned long last_us = 0;
unsigned long last_print_us = 0;

// ***** WiFi Configuration *****
const char* ssid = "toolbox";
const char* password = "Toolbox.Torino";
// const char* ssid = "Hinnhi";
// const char* password = "12345678";

// ***** Server Configuration *****
const char* server = "13.61.178.131";
const int port = 8080;

unsigned long lastPollTime = 0;
const unsigned long pollInterval = 500; // Poll every 500ms
String arduinoId = "";

// ***** Roll Monitoring *****
float rif_roll;  // Reference roll angle
float roll;      // Current roll angle
float delta_degree = 45.0;  // Tolerance in degrees

// ***** Control Variables *****
float dist;  // Current distance from Bluetooth
int model_distracted;  // Distraction prediction (1=focused, 0=distracted)

// ***** Bluetooth Distance Calculation *****
const int RSSI_AT_1M = -59;  // RSSI value at 1 meter distance
const float PATH_LOSS_EXPONENT = 2.0;  // Path loss exponent (2.0 = free space)

// ***** Distance Filter (Moving Average) *****
const int FILTER_SIZE = 10;  // Number of samples for averaging
float distanceBuffer[FILTER_SIZE];  // Circular buffer for distance samples
int bufferIndex = 0;  // Current position in buffer
bool bufferFilled = false;  // Whether buffer has been filled once
