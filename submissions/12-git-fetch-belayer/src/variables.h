#ifndef VARIABLES_H
#define VARIABLES_H
#include <Arduino.h>

// ***** IMU & Roll Calculation Constants *****
extern const float COMP_ALPHA_MOVING;
extern const float COMP_ALPHA_STATIC;
extern const float ACC_LPF_ALPHA;
extern const float GYRO_STATIC_TH;
extern const float ACC_STATIC_TH;
extern const uint32_t PRINT_US;
extern const uint16_t CAL_SAMPLES;

// IMU state variables
extern float roll_deg;
extern float accRoll_lpf_deg;
extern float gxBias, gyBias, gzBias;

extern unsigned long last_us;
extern unsigned long last_print_us;

// ***** WiFi Configuration *****
extern const char* ssid;
extern const char* password;

// ***** Server Configuration *****
extern const char* server;
extern const int port;

extern unsigned long lastPollTime;
extern const unsigned long pollInterval;
extern String arduinoId;

// ***** Roll Monitoring *****
extern float rif_roll;  // Reference roll angle
extern float roll;      // Current roll angle
extern float delta_degree;  // Tolerance in degrees

// ***** Control Variables *****
extern float dist;  // Current distance from Bluetooth
extern int model_distracted;  // Distraction prediction (1=focused, 0=distracted)

// ***** Bluetooth Distance Calculation *****
extern const int RSSI_AT_1M;
extern const float PATH_LOSS_EXPONENT;

// ***** Distance Filter (Moving Average) *****
extern const int FILTER_SIZE;
extern float distanceBuffer[];
extern int bufferIndex;
extern bool bufferFilled;

// State machine states
enum State {
  IDLE,
  CONNECTING,
  CALIBRATING,
  RUNNING
};

#endif // VARIABLES_H
