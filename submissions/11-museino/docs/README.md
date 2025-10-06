## 🎨 **Project: MuseINO — Smart Museum Vision System**

### 🔍 **General Concept**

Install an **Arduino Nicla Vision** on the **lower frame of a painting or artwork** to create an **intelligent surveillance and visitor behavioral analysis system**.

### 🎯 **Main Objectives**

1. **Surveillance and security:**
   * Use the **depth sensor (ToF)** to measure visitors' distance from the painting.
   * Establish a **safety distance** as a "baseline" and generate an **alert** if someone gets too close.
   * Detect and **count people** in the area of interest, to analyse flows and plan accordingly.

2. **Visitor statistical analysis:**
   * Recognize **how many people actually look at the painting**, not just how many pass in front of it.
   * Estimate **average dwell time** for each visitor.
   * Use a **classification or detection model (Focoos AI)** to differentiate between "passersby" and "observers".

3. **Future extensions:**
   * Application in **stores or supermarkets** for behavioral analysis and "shopping analytics".
   * Totems in **shopping malls** for heatmaps and interaction data.

---

## ⚙️ **Technical Architecture**

### 🧠 **1. On-edge Processing (Nicla Vision)**

The Nicla Vision (dual-core STM32H747, 2MP camera, integrated ToF sensor and IMU):

* Captures frames from the **camera** and **ToF sensor**.
* Executes **object detection or classification** locally.
* Sends **synthetic data** (position, distance, object ID) via **WiFi or BLE** to the server.
* In case of anomaly (e.g., too close to the painting), can also transmit **the image**.

### 💻 **2. Server (PC or Python mini-server)**

* Receives data via **WiFi/IP**.
* Performs **post-processing**:
  * Tracking people over time.
  * Calculating average dwell time.
  * Generating **heatmaps** for position and viewing direction.
* Web dashboard: displays number of visitors, average duration, most observed areas.
* (Roadmap feature) **Database** for historical analysis or real-time dashboard.

### 🔁 **3. Communication and Synchronization**

* Nicla → Server via **WiFi (ESP32/Murata 1DX)** or **BLE**.
* Lightweight protocol (e.g., MQTT or Python socket).
* Optional alert module (buzzer or LED) managed by Arduino.

---

## 🧩 **AI Pipeline**

### 📸 **Computer Vision Model Sketch (on-edge)**

1. **Dataset collection**
   * Acquiring images of people in front of the painting, various distances and poses.

2. **Preprocessing and data augmentation**
   * Cropping, resizing, rotation, lighting variations.

3. **Model training** on **Focoos AI** intuitive platform (finetuning of `fai-cls-n-coco`).

4. **Testing and validation**

5. **Quantization** and **compilation**
   * Converting using ONNX the model to **optimized format (C++ static library)**.

6. **Deploy on Nicla Vision** via **Zant** and **Zig compiler**.

---

## 🌐 **Complete Integration**

| Component     | Function                              | Language / Tool                    |
| ------------- | ------------------------------------- | ---------------------------------- |
| Nicla Vision  | Acquisition + on-edge inference       | C / C++ / ArduinoIDE               |
| Focoos AI     | Training and model optimization       | Python / Focoos SDK                |
| Server PC     | Processing, tracking, dashboard       | Python             				      |
| Web Dashboard | Real-time data visualization          | Gradio                             |

---

## 🔦 **Expected Outputs**

* Real-time alerts when a visitor gets too close.
* Visitor count.
* Interactive dashboard for curators and museum staff.

## 🔮 **Future extension**
* Average dwell times per painting.
* Visual heatmap of observation points.
* More analytics (areas of interest, people density).
* Extension to retail, groceries.


## Project Structure

```
11-MuseINO/
├── src/
│   ├── person_classifier_v2.ino      # Main Arduino sketch
│   ├── person_classifier_v2.onnx     # ONNX model (361KB)
│   ├── model_info.json               # Model metadata and configuration
│   └── model/
│       ├── parse_and_trim_coco.py    # COCO dataset preprocessing
│       └── infer_stats.py            # Model validation script
└── docs/                              # Documentation (empty)
```

## Hardware Requirements

- **Arduino Nicla Vision** (STM32H747 dual-core)
- **QSPI Flash**: 16MB (memory-mapped at 0x90000000)
- **Camera**: GC2145 sensor (160x120 RGB565)
- **Serial**: USB connection for streaming/logging

## Model Specifications

**Architecture**: FAI-CLS-N (Classification Nano)
- **Input**: 96x96 RGB (NCHW format, channels-first)
- **Output**: 2 classes (person, no_person)
- **Backbone**: STDC Nano (4-5-3 layers, base=64)
- **Normalization**: ImageNet stats
  - Mean: [123.675, 116.28, 103.53]
  - Std: [58.395, 57.12, 57.375]
- **Model size**: 361KB (ONNX)
- **Reference ID**: `479fcf5032f340f5`

## Setup

### 1. Dataset Preparation (Optional)

If you need to retrain or validate the model:

```bash
# Preprocess COCO dataset
python src/model/parse_and_trim_coco.py \
  --coco_root_folder /path/to/coco \
  --new_coco_folder /path/to/output

# Validate model performance
python src/model/infer_stats.py \
  --model_id 479fcf5032f340f5 \
  --dataset_test_folder /path/to/test
```

### 2. Flash Model Weights

1. Convert ONNX model to quantized weights (INT8 or float) using FocoosAI script
2. Flash weights to QSPI memory at address `0x90000000`
3. Ensure weights are compatible with Zant inference library and check architecture with Netron.
4. Follow religiously Zant's tutorial: in /docs/Guide_XIP_NICLA.pdf

### 3. Upload in QSPI memory the chosen Arduino Sketch using shell script ./flash_nicla_xip.sh

**Configuration** ([person_classifier_v2.ino:9-13](src/person_classifier_v2.ino#L9-L13)):
```cpp
#define BAUD                 921600   // Serial baud rate
#define THR                  0.60f    // Detection threshold
#define RGB565_IS_MSB_FIRST  1        // Byte order (1=big-endian)
#define STREAM_TO_PC         0        // 0=log mode, 1=binary stream
```

**Upload Steps**:
1. Open `src/person_classifier_v2.ino` in Arduino IDE
2. Select: **Board → Arduino Nicla Vision**
3. Set serial port
4. Compile and upload
5. Open Serial Monitor at 921600 baud

## Operation Modes

### Log Mode (STREAM_TO_PC = 0)

Prints human-readable detection results:
```
[ZANT] QSPI MMAP OK @0x90000000
[ZANT] Ready (NCHW 1x3x96x96, normalized 0..1).
[ZANT] PERSON top1: idx=0 label=person prob=0.876 time=45.2 ms
[ZANT] PERSON top1: idx=1 label=not_person prob=0.124 time=44.8 ms
```

### Streaming Mode (STREAM_TO_PC = 1)

Sends binary frames over serial with FRME protocol:

**Frame Structure**:
```
[4B] Magic: "FRME"
[1B] Version: 1
[2B] Sequence number (LE)
[2B] Width (LE)
[2B] Height (LE)
[1B] Class index (0=person, 1=not_person)
[2B] Probability × 1000 (LE)
[2B] Inference time × 10 ms (LE)
[4B] Payload length (LE)
[NB] Grayscale image data (96×96 = 9216 bytes)
[4B] CRC32 (LE)
```

Total frame size: **9,240 bytes**

## Inference Pipeline

1. **Frame Capture**: GC2145 camera captures 160x120 RGB565 frame
2. **Preprocessing**:
   - Resize to 96x96 using nearest neighbor
   - Convert RGB565 → RGB888
   - Normalize with ImageNet stats (NCHW format)
   - Generate grayscale preview for streaming
3. **Inference**: Run model with XIP weights from QSPI flash
4. **Post-processing**:
   - Apply softmax activation
   - Select top-1 class
   - LED feedback (on when prob ≥ threshold)
5. **Output**: Serial log or binary stream

## Performance

- **Inference time**: ~45ms per frame
- **Frame rate**: ~22 FPS (limited by camera grab)
- **Serial bandwidth**: 921600 baud (~92KB/s)
- **Stream latency**: ~100ms per frame at 921600 baud

## QSPI Configuration

**Hardware Pins** (STM32H747):
- `PB2`: CLK (AF9)
- `PG6`: nCS (AF10)
- `PD11-PD14`: IO0-IO3 (AF9)

**Settings**:
- Flash size: 16MB (2^24 bytes)
- Read command: 0x6B (Quad Output Fast Read)
- Mode: 1-1-4 (single instruction/address, quad data)
- Dummy cycles: 8
- Clock prescaler: 7

## Key Features

### Memory-Mapped Execution (XIP)
Weights are accessed directly from QSPI flash without loading into RAM, enabling larger models on memory-constrained devices.

### Efficient Preprocessing
- **Nearest neighbor resize**: Fast, deterministic scaling
- **In-place normalization**: Minimal memory overhead
- **Dual output**: NCHW float for inference + grayscale for visualization

### Robust Frame Protocol
- **CRC32 validation**: Detects transmission errors
- **Sequence numbers**: Track frame drops
- **Little-endian format**: Cross-platform compatibility

## Troubleshooting

### QSPI Initialization Failed
```
[ZANT] QSPI init FAILED
```
- Check GPIO pin connections (PB2, PG6, PD11-PD14)
- Verify flash chip is 16MB and supports Quad mode
- Test flash with memory read at 0x90000000

### Camera Timeout
```
[ZANT] camera timeout
```
- Verify GC2145 sensor is connected
- Check I2C bus (SDA/SCL)
- Reset board and retry

### Predict Returns Error
```
[ZANT] predict() rc=-1
```
- Weights not properly flashed to QSPI
- Model/weight format mismatch
- Insufficient memory for inference

### Streaming Issues
- Reduce baud rate to 115200 if frames are corrupted
- Check CRC32 on receiving end
- Ensure STREAM_TO_PC is set to 1

## Model Training & Validation

The model was trained using the Focoos framework:

**Training Configuration**:
- Base model: `fai-cls-n-coco`
- Backbone: STDC Nano
- Hidden dim: 512
- Dropout: 0.2
- Resolution: 96×96
- Loss: Cross-entropy with pos_weight=2.0

**Dataset**:
- Binary classification (person vs. no_person)
- Balanced sampling (1:1 ratio)
- Filtered annotations (min height=100px, width=50px)
- COCO format with remapped categories

**Validation**:
Run inference statistics on test set:
```bash
python src/model/infer_stats.py \
  --model_id 479fcf5032f340f5 \
  --dataset_test_folder /path/to/test
```

Metrics computed:
- Person recall: 0.7019867549668874
- Person precision: 0.796448087431694
- No Person recall: 0.8086062941554271
- No Person precision: 0.7177879133409351

## Technical Details

### Normalization

ImageNet statistics applied per-channel:
```cpp
R_norm = (R - 123.675) / 58.395
G_norm = (G - 116.28) / 57.12
B_norm = (B - 103.53) / 57.375
```

### Color Conversion

RGB565 → RGB888 with bit expansion:
```cpp
R8 = (R5 << 3) | (R5 >> 2)  // 5-bit → 8-bit
G8 = (G6 << 2) | (G6 >> 4)  // 6-bit → 8-bit
B8 = (B5 << 3) | (B5 >> 2)  // 5-bit → 8-bit
```

### Softmax Activation

Numerically stable softmax with overflow protection:
```cpp
max = max(logits)
exp_sum = sum(exp(logits - max))
prob[i] = exp(logits[i] - max) / exp_sum
```

## Dependencies

**Arduino Libraries**:
- `camera.h`: Camera interface
- `gc2145.h`: GC2145 sensor driver
- `lib_zant.h`: Zant inference engine
- STM32 HAL QSPI drivers

**Python (for preprocessing)**:
- focoos
- torch
- numpy
- pillow
- tqdm

## License

See root LICENSE file.

## References

- [Focoos Framework](https://github.com/focoos/focoos)
- [Zant Inference Engine](https://zant.ai)
- [Arduino Nicla Vision](https://docs.arduino.cc/hardware/nicla-vision)
- [STM32H747 QSPI Documentation](https://www.st.com/resource/en/reference_manual/rm0399-stm32h745755-and-stm32h747757-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)
