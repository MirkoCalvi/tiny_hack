# Nicla Vision — Attention Pipeline (Wi‑Fi + BLE + TinyML)

This project implements a **four‑state embedded pipeline** on **Arduino Nicla Vision** that integrates **Wi‑Fi communication**, **Bluetooth distance sensing**, and **on‑device TinyML inference** to perform **real‑time attention monitoring**.

## Overview

- **States**: `IDLE → CONNECTING → CALIBRATING → RUNNING`
- **Wi‑Fi**: periodic HTTP exchange with a web app (start signal, image upload, feedback 0/1)
- **BLE**: distance estimation to adapt processing timing
- **IMU**: roll (rotation around Y) used with a reference angle and tolerance
- **TinyML**: `predict()` returns attention classification (1 attentive, 0 distracted)

## State Machine


```text
Power On
   │
   ▼
[IDLE] --(start command from web app)--> [CONNECTING] --(BLE link OK)--> [CALIBRATING]
   ^                                                                             │
   │                                                                             ├─(web app says "capture")
   └--------------------------(stop/reset)--------------------------------------- ▼
                                                                          [RUNNING]
     In RUNNING:
       - Read BLE distance (adaptive timing)
       - Read reference angle (IMU)
       - Use web feedback (presence 1/0)
       - Run tinyML `predict()` for attention
       - Decide: attentive / distracted
```

### IDLE
Device is powered and connected to Wi‑Fi. Waits for a **start** command from the web app.

```cpp
// IDLE → CONNECTING when web app sends "start"
if (currentState == IDLE && webApp.startRequested()) {
  currentState = CONNECTING;
  BLE.begin();          // prepare BLE for distance estimation
  logStateChange(IDLE, CONNECTING);
}
```

### CONNECTING
Enables **BLE** and attempts to connect to the target for distance estimation.

```cpp
// CONNECTING → CALIBRATING once BLE is connected to the target
if (currentState == CONNECTING) {
  if (BLE.connected()) {
    currentState = CALIBRATING;
    logStateChange(CONNECTING, CALIBRATING);
  } else {
    BLE.scan(true);  // keep scanning
  }
}
```

### CALIBRATING
On web trigger, captures an image, uploads it, and expects **feedback = 1** to proceed.

```cpp
// CALIBRATING: wait for web app trigger, capture image, get feedback (1/0)
if (currentState == CALIBRATING && webApp.captureRequested()) {
  Image img = camera.capture();
  int feedback = webApp.uploadAndGetFeedback(img); // 1=approved, 0=rejected
  if (feedback == 1) {
    setReferenceAngle(readRoll()); // defined at startup/calibration
    currentState = RUNNING;
    logStateChange(CALIBRATING, RUNNING);
  }
}
```

### RUNNING
Continuously evaluates attention based on **presence (web)**, **angle window (IMU)**, and **TinyML `predict()`**. The sampling delay is **adaptive** to the measured BLE distance.

```cpp
// RUNNING: attention logic with adaptive timing based on BLE distance
if (currentState == RUNNING) {
  float dist_m = bleDistanceMeters();           // 1..10m range, else flag
  uint32_t wait_ms = adaptDelayFromDistance(dist_m); // e.g. closer → shorter wait
  int presence = webApp.lastPresence();         // 1 present, 0 not present
  float roll = readRoll();                      // IMU reading around Y axis
  int attn = predict(/* features or preprocessed frame */);

  bool distracted = (presence == 0) ||
                    !withinAngleWindow(roll, referenceAngle, DEG_WINDOW) ||
                    (attn == 0);

  if (distracted) {
    signalDistracted();   // LED/Buzzer/Message
  } else {
    signalAttentive();
  }
  delay(wait_ms);
}
```

## Adaptive Timing (distance‑aware)
Use BLE distance to scale the evaluation interval (e.g., closer → shorter wait). Example policy:

```cpp
uint32_t adaptDelayFromDistance(float d_m) {
  // Clamp 1..10m; further → slower updates, closer → faster
  if (d_m < 1.0f) d_m = 1.0f;
  if (d_m > 10.0f) d_m = 10.0f;
  // Map 1m→100ms, 10m→500ms (linear)
  return (uint32_t)(100.0f + (d_m - 1.0f) * (400.0f / 9.0f));
}
```

## File Tree
```
tiny_hack/
  bluetooth_central.ino
  build/
    arduino.mbed_nicla.nicla_vision/
      tiny_hack.ino.bin
      tiny_hack.ino.elf
      tiny_hack.ino.hex
      tiny_hack.ino.map
      tiny_hack.ino.with_bootloader.bin
      tiny_hack.ino.with_bootloader.hex
  custom.ld
  flash_nicla_xip.sh
  state_machine.ino
  tiny_hack.ino
  variables.cpp
  variables.h
```
## Dependencies
Detected and/or inferred from sources:
- Arduino
- ArduinoBLE
- ArduinoHttpClient
- ArduinoJson
- Arduino_LSM6DSOX
- WiFiNINA
- WiFiNINA (or Nicla Vision WiFi)

## Build & Upload (Arduino IDE)

1. **Board & Core**
   - Install *Arduino Mbed OS Nicla Boards* via Boards Manager.
   - Select **Nicla Vision** as the target board.

2. **Libraries**
   - Install required libraries from Library Manager (see *Dependencies* below).

3. **Wi‑Fi firmware**
   - Ensure the Wi‑Fi filesystem/firmware is present. If you see
     `Failed to mount the filesystem containing the WiFi firmware`,
     use the *WiFiNINA Firmware Updater* (Tools → WiFi101/WiFiNINA Firmware/Certificate Updater)
     and restore the default firmware/filesystem.

4. **Port & Upload**
   - Put the board in DFU/bootloader mode if needed (double‑tap reset).
   - Select the correct **Port** and click **Upload**.

5. **Serial Monitor**
   - Open Serial Monitor at 115200 baud to observe state transitions and logs.

## Configuration Tips
- **Reference angle**: set during calibration (store in RAM or NVS if needed).
- **Angle window**: choose a tolerance (e.g., ±45°) suitable for your use case.
- **Presence feedback**: cache last web response to avoid blocking loops.
- **Non‑blocking design**: avoid long delays; replace with timers where possible.

## Logging
Print state transitions and key variables:
```cpp
void logStateChange(State fromS, State toS) {
  Serial.print("STATE: "); Serial.print(stateToString(fromS));
  Serial.print(" -> ");     Serial.println(stateToString(toS));
}
```

## Troubleshooting

- **Exit status 74 / DFU “No DFU capable USB device available”**
  - Double‑tap reset to enter bootloader, try a different USB cable/port, or reinstall *dfu-util*.
- **“Failed to mount the filesystem containing the WiFi firmware.”**
  - Re‑flash WiFiNINA filesystem via Firmware/Certificate Updater.
- **Duplicate `setup()` / `loop()` definitions**
  - Ensure only one `.ino` in the sketch folder defines `setup()` and `loop()` (or merge files appropriately).
- **BLE API changes**
  - Prefer `BLE.scan(true)` and check `BLE.connected()`; avoid non‑existent methods like `BLE.scanning()`.

---

**Notes**  
- Code snippets are intentionally short and self‑contained to illustrate the pipeline logic.  
- Replace utility calls like `webApp.*`, `camera.capture()`, and `bleDistanceMeters()` with your project’s actual APIs.
