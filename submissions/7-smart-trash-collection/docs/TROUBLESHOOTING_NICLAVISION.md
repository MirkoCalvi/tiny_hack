# Troubleshooting Guide - Arduino Nicla Vision

This document collects common issues you may encounter when using the **Arduino Nicla Vision** and how to fix them.

---

## 🛠️ Issue: WiFi Connection Error

**Error message:**

```text
Failed to mount the filesystem containing the Wifi firmware.
Usually that means that the Wifi firmware has not been installed yet or was overwritten with another firmware.
```

### ✅ Root Cause
This happens when the **WiFi firmware** or the **certificates** on the Nicla Vision are missing, corrupted, or have been overwritten by another firmware.

### 🔧 Solution
You need to update the WiFi firmware and certificates on the Nicla Vision.

1. Open the **Arduino IDE**.  
2. Go to:  
   `File → Examples → STM32H747_System → WiFiFirmwareUpdate`  
3. Upload and run this sketch on your Nicla Vision.  
4. Open the **Serial Monitor** and wait for the update process to finish.  
5. The sketch will flash the correct WiFi firmware and update the certificates.  
6. Once the update is complete, unplug and replug the board, then re-upload your project sketch.  

### 💡 Notes
- This procedure only needs to be done once, unless the WiFi firmware gets corrupted again.  
- After running the update, the Nicla Vision should successfully mount the WiFi filesystem and connect to networks.  

---

## 🛠️ Issue: Uploading/Flashing Error on Linux
**Error message:**
```text
Failed uploading: uploading error: exit status 1
```

### ✅ Root Cause
On Linux systems, this error usually occurs because the correct udev rules for Arduino boards are missing or not properly installed.

### 🔧 Solution
Follow the official Arduino guide to fix udev rules on Linux: [Fix udev rules on Linux (Arduino Support)](https://support.arduino.cc/hc/en-us/articles/9005041052444-Fix-udev-rules-on-Linux#mbed-os).

---
