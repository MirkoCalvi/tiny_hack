# Nicla Vision Camera Resolution & M4 RAM - Complete Guide


## Camera Minimum Resolutions for Nicla Vision

### Available Resolutions

The camera library supports these standard resolutions:
- **CAMERA_R160x120** (QQVGA) - smallest available
- **CAMERA_R320x240** (QVGA) - most commonly used
- **CAMERA_R320x320**
- **CAMERA_R640x480** (VGA)
- **CAMERA_R800x600** (SVGA)
- **CAMERA_R1600x1200** (higher resolutions)

**Source:** The camera library defines these resolutions as standard options available for the GC2145 sensor on Nicla Vision.

### How to Use Smaller Resolution (QQVGA 160x120)

To use the minimal 160x120 resolution, modify your code:
```cpp
// Change this line in setup():
// FROM:
cam.begin(CAMERA_R320x240, CAMERA_RGB565, 30);// TO:
cam.begin(CAMERA_R160x120, CAMERA_RGB565, 30);  // QQVGA = 160x120// Update your dimensions:
static const uint32_t H=96, W=96;  // Keep 96x96 for your model
// OR change to match camera exactly:
static const uint32_t H=120, W=160;  // Match camera if your model supports it
```

### Custom 120x160 Resolution

Unfortunately, **120x160 is not a standard resolution**. The GC2145 camera sensor doesn't support arbitrary resolutions. Your options:

1. **Use QQVGA (160x120)** and crop/resize to 120x96 or your target size
2. **Use QVGA (320x240)** and downsample
3. Work with the sensor's native resolutions

**Important Note:** The GC2145 sensor internally has a resolution of 1600x1200, and these dimensions are scaled down. QVGA (320×240) provides the maximum field of view when no cropping is applied.

**Source:** The GC2145 has limited settings for full frame capture. The sensor internally has a resolution of 1600x1200. These dimensions can be divided by non-even values to scale down the resolution.

---

## ealloc Library for Cortex-M4 RAM on Nicla Vision

### About Dual-Core Architecture

The Nicla Vision uses an STM32H747AII6 dual-core processor with:
- **M7 core**: 480MHz (main core, runs Arduino code)
- **M4 core**: 240MHz (auxiliary core)
- **Total RAM**: 1MB shared between cores
- **External QSPI**: 16MB flash for additional storage

**Source:** The Nicla Vision uses an STM32H747AII6 dual-core processor with 480MHz Arm Cortex-M7 core and a 240MHz Cortex-M4 core, 1MB of RAM, 2MB of flash memory, and 16MB of external QSPI flash for additional storage.

### alloc Library Status

### Option 1: STM32H7 Dual-Core Memory Management

The STM32H747 has multiple RAM domains:
```cpp

// Memory regions on STM32H747:
// DTCM RAM (M7 only): 128KB - fastest
// AXI SRAM: 512KB - shared
// SRAM1, SRAM2, SRAM3: ~384KB - shared
// SRAM4: 64KB - can be dedicated to M4
```


### Option 2: Use Memory-Mapped Regions

You can allocate buffers in specific RAM sections using linker attributes:
```cpp

// Place buffer in specific RAM section (linker script)
attribute((section(".sram4"))) static uint8_t m4_buffer[1601202];// Or use shared RAM explicitly
attribute((section(".shared_ram"))) static uint8_t shared_fb[3202402];

```

### Option 3: Arduino RPC Library (Recommended)

For dual-core operation on STM32H747, you need to ensure:
- **Static pre-compilation assignment**: Peripherals such as a UART are assigned in devicetree before compilation. The user must ensure peripherals are not assigned to both cores at the same time.
- **Run time protection**: Interrupt-controller and GPIO configurations could be accessed by both cores at run time. Accesses are protected by a hardware semaphore to avoid potential concurrent access issues.
- **Build separate binaries**: Applications should be built per core target, using either M7 or M4 as the target.

**Source:** Compilation requirements for dual-core STM32H747 include clock configuration accessible only to M7 core, static pre-compilation assignment of peripherals, and runtime protection via hardware semaphore.

Arduino provides RPC (Remote Procedure Call) library for M4 communication:
```cpp
#include "RPC.h"void setup() {
RPC.begin();  // Initialize M7-M4 communication// M7 can call functions on M4
// M4 can process data independently

```

---

## Practical Recommendations

### For Minimal Memory Usage:
```cpp

// Modified config for smallest footprint
#define USE_QQVGA  // Use 160x120 instead of 320x240#ifdef USE_QQVGA
static const uint32_t CAM_W = 160;
static const uint32_t CAM_H = 120;
#else
static const uint32_t CAM_W = 320;
static const uint32_t CAM_H = 240;
#endif// Your model input (keep as is or adjust)
static const uint32_t H=96, W=96;// In setup():
cam.begin(CAMERA_R160x120, CAMERA_RGB565, 30);  // Use QQVGA// Adjust resize function to work with 160x120 source:
resize_rgb565_to_96x96_rgbNCHW_and_gray_NEAREST(
buf, CAM_W, CAM_H,  // Now 160x120
gInput, gGray8
);
```

### Memory Savings Calculation:

```
QVGA (320x240):  320×240×2 = 153,600 bytes (~150 KB)
QQVGA (160x120): 160×120×2 =  38,400 bytes (~37.5 KB)
Savings: ~115 KB of framebuffer RAM

```


