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
| Server PC     | Processing, tracking, dashboard       | Python             				 |
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
* Exansion to retail, groceries.
