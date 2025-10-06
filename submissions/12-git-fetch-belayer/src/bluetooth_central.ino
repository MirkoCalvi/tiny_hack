/*
  BLE Central con monitoraggio distanza continuo
  Arduino Nicla Vision
*/

#include <ArduinoBLE.h>
#include "variables.h"
// Bluetooth distance calculation constants are defined in variables.h
// RSSI_AT_1M and PATH_LOSS_EXPONENT

// BLE device tracking
BLEDevice connectedPeripheral;
bool isBluetoothConnected = false;

// Distance calculation with RSSI
float calculateDistance(int rssi) {
  if (rssi == 0) return -1.0;
  float ratio = (RSSI_AT_1M - rssi) / (10.0 * PATH_LOSS_EXPONENT);
  return pow(10, ratio);
}

String getProximityLevel(float distance) {
  if (distance < 0) return "Sconosciuta";
  if (distance < 0.5) return "Molto vicino";
  if (distance < 1.5) return "Vicino";
  if (distance < 3.0) return "Medio";
  if (distance < 6.0) return "Lontano";
  return "Molto lontano";
}

// Funzione per aggiungere un campione al filtro
void addToFilter(float distance) {
  distanceBuffer[bufferIndex] = distance;
  bufferIndex = (bufferIndex + 1) % FILTER_SIZE;
  
  if (bufferIndex == 0) {
    bufferFilled = true;
  }
}

// Funzione per calcolare la media mobile
float getFilteredDistance() {
  float sum = 0;
  int count = bufferFilled ? FILTER_SIZE : bufferIndex;
  
  if (count == 0) return -1.0;
  
  for (int i = 0; i < count; i++) {
    sum += distanceBuffer[i];
  }
  
  return sum / count;
}

// Funzione per resettare il filtro
void resetFilter() {
  bufferIndex = 0;
  bufferFilled = false;
  for (int i = 0; i < FILTER_SIZE; i++) {
    distanceBuffer[i] = 0;
  }
}

// Initialize Bluetooth
bool initBluetooth() {
  if (!BLE.begin()) {
    Serial.println("Starting BLE failed!");
    return false;
  }
  Serial.println("BLE initialized successfully");
  resetFilter();
  return true;
}

// Connect to a specific BLE peripheral
bool connectToPeripheral(const char* deviceName) {
  Serial.print("Scanning for device: ");
  Serial.println(deviceName);
  
  BLE.scanForName(deviceName);
  
  unsigned long startTime = millis();
  while (millis() - startTime < 10000) {  // 10 second timeout
    BLEDevice peripheral = BLE.available();
    
    if (peripheral) {
      Serial.print("Found device: ");
      Serial.println(peripheral.localName());
      
      BLE.stopScan();
      
      Serial.print("Connecting to ");
      Serial.print(peripheral.address());
      Serial.println("...");
      
      if (peripheral.connect()) {
        Serial.println("Connected!");
        connectedPeripheral = peripheral;
        isBluetoothConnected = true;
        resetFilter();
        return true;
      } else {
        Serial.println("Failed to connect!");
        return false;
      }
    }
    delay(100);
  }
  
  Serial.println("Device not found");
  BLE.stopScan();
  return false;
}

// Check if still connected
bool checkBluetoothConnection() {
  if (!isBluetoothConnected) {
    return false;
  }
  
  if (!connectedPeripheral.connected()) {
    Serial.println("Bluetooth connection lost!");
    isBluetoothConnected = false;
    resetFilter();
    return false;
  }
  
  return true;
}

// Main distance measurement function
float distance() {
  // If not connected, return a default value
  if (!isBluetoothConnected || !connectedPeripheral.connected()) {
    return 10.0;  // Default distance when disconnected
  }
  
  // Get RSSI from connected device
  int rssi = connectedPeripheral.rssi();
  
  if (rssi == 0) {
    return 10.0;  // Return default if RSSI unavailable
  }
  
  // Calculate raw distance
  float rawDistance = calculateDistance(rssi);
  
  // Add to filter for smoothing
  addToFilter(rawDistance);
  
  // Get filtered distance
  float filteredDistance = getFilteredDistance();
  
  // Optional: Print debug info (comment out in production)
  /*
  Serial.print("RSSI: ");
  Serial.print(rssi);
  Serial.print(" dBm | Dist raw: ");
  Serial.print(rawDistance, 2);
  Serial.print(" m | Dist filtered: ");
  Serial.print(filteredDistance, 2);
  Serial.print(" m | ");
  Serial.println(getProximityLevel(filteredDistance));
  */
  
  return filteredDistance;
}

// Disconnect from current peripheral
void disconnectBluetooth() {
  if (isBluetoothConnected && connectedPeripheral.connected()) {
    connectedPeripheral.disconnect();
    Serial.println("Disconnected from Bluetooth device");
  }
  isBluetoothConnected = false;
  resetFilter();
}

  