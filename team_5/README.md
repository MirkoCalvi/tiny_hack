# 🔬 MelaNoMore

**AI-Powered Skin Lesion Screening for Clinical Decision Support**

---

## Overview

**MelaNoMore** is a computer vision-based decision support tool designed to assist dermatologists in the early detection and classification of skin lesions. By combining edge AI on the **Arduino Nicla Vision** with a powerful server-side deep learning model, MelaNoMore provides a two-tier screening system that balances speed, accuracy, and accessibility.

### Key Features

- ⚡ **Fast on-device screening** - Binary classification (suspicious vs. non-suspicious) directly on the Nicla Vision
- 🧠 **Advanced server-side analysis** - Multi-class classification across 7 lesion types using Vision Transformer
- 📡 **Seamless WiFi integration** - Automatic image upload for suspicious cases
- 🎯 **Distance guidance** - Time-of-Flight sensor ensures correct positioning
- 💡 **Intuitive LED feedback** - Color-coded status for real-time user guidance
- 🌐 **Web dashboard** - Accessible interface for reviewing detailed predictions

---

## 👥 Team

- **[Arslan](https://www.linkedin.com/in/arslan-ali-1804bbb1/)**
- **[Vittorio](https://www.linkedin.com/in/vittorio-sironi/)**
- **[Alessandro](https://www.linkedin.com/in/alessandro-sola03/)**

---

## Use Case

MelaNoMore serves as a **"second set of eyes"** for dermatologists during clinical examinations:

1. **Pre-screening** happens instantly on the handheld device, even offline
2. **Suspicious cases** are automatically escalated to a more powerful model running on a server
3. **Detailed classification** helps dermatologists make informed decisions about diagnosis and treatment

This workflow helps:
- ⏱️ Save time during patient consultations
- 🔍 Reduce diagnostic errors
- 🩺 Improve early detection of dangerous skin cancers like melanoma

---

## 🏗️ System Architecture

MelaNoMore employs a **two-tier classification system**:

### Tier 1: Edge Device (Arduino Nicla Vision)
- **Model**: `fai-cls-n-coco` (Focoos AI)
- **Task**: Binary classification (suspicious vs. non-suspicious)
- **Input**: 96x96 RGB images
- **Inference**: Real-time, on-device
- **Output**: Classification + LED feedback

### Tier 2: Server (PC/Cloud)
- **Model**: Vision Transformer Large (ViT-L/16)
- **Task**: Multi-class classification across 7 lesion types
- **Parameters**: ~305M
- **Inference**: Triggered only for suspicious cases
- **Output**: Detailed classification with confidence scores

### Communication Flow

```
[Nicla Vision] -> Capture Image -> On-Device Inference
       |
  Suspicious?
       |
    [YES] -> WiFi Upload -> [Flask Server] -> ViT-L/16 Inference
       |                          |
    [NO]                   Web Dashboard
       |
   Green LED
```

---

## 🧬 Dataset

**HAM10000** (Human Against Machine with 10,000 training images)
Source: [ISIC Archive - Collection 212](https://api.isic-archive.com/collections/212/)

### Lesion Categories (7 classes)
1. Actinic Keratoses
2. Basal Cell Carcinoma
3. Benign Keratosis-like lesions
4. Dermatofibroma
5. Melanocytic Nevi
6. Melanoma
7. Vascular lesions

---

## 🤖 Model Details

### Edge Model (Nicla Vision)
- **Architecture**: `fai-cls-n-coco` (Focoos AI)
- **Pretraining**: COCO dataset
- **Fine-tuning**: Binary classification on HAM10000 (suspicious vs. non-suspicious)
- **Input Size**: 96x96
- **Export Format**: ONNX with quantization
- **Deployment**: Flashed via Zant

### Server Model (PC)
- **Architecture**: Vision Transformer Large (ViT-L/16)
- **Parameters**: ~305M
- **Pretraining**: ImageNet-21k
- **Fine-tuning**: HAM10000 with Focal Loss (to handle class imbalance)
- **Framework**: PyTorch

### Performance Metrics

<table>
<tr>
<td width="50%">

**Edge Model (Nicla Vision)**
*Binary Classification*

| Metric | Score |
|--------|-------|
| **Accuracy** | 76% |
| **Precision** | 67.99% |
| **Recall** | 94.01% |
| **F1-Score** | 76.44% |

</td>
<td width="50%">

**Server Model (ViT-L/16)**
*Multi-Class Classification*

| Metric | Score |
|--------|-------|
| **Accuracy** | 84.60% |
| **F1 (Macro)** | 72.80% |
| **F1 (Weighted)** | 83.40% |

</td>
</tr>
</table>


---

## 🔧 Hardware Components

### Required Hardware
- **Arduino Nicla Vision** - Edge AI processing and image capture
- **PC/Server** - Flask web server + Vision Transformer inference

### Device Integration
The Nicla Vision is integrated into a handheld, dermatoscope-like form factor for ease of use in clinical settings.

---

## 💻 Software Stack

### On-Device (Arduino Nicla Vision)
- Arduino IDE
- Focoos AI platform (model training & export)
- ONNX runtime
- Zant (firmware flashing)

### Server-Side (PC)
- Python 3.8+
- Flask (web server)
- PyTorch
- torchvision
- scikit-learn
- NumPy, Pandas

---

## 🚀 Getting Started

### 1. Hardware Setup
1. Assemble the MelaNoMore handheld device with Nicla Vision
2. Ensure ToF sensor and camera are properly connected
3. Verify LED indicators are functional

### 2. Deploy Edge Model
```bash
# Flash the ONNX model to Nicla Vision using Zant
zant flash --model model.onnx --device nicla-vision
```

### 3. Upload Arduino Sketch
```bash
# Open sketch.ino in Arduino IDE and upload to Nicla Vision
arduino-cli compile --fqbn arduino:mbed_nicla:nicla_vision sketch.ino
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:mbed_nicla:nicla_vision sketch.ino
```

### 4. Start Server
```bash
# Navigate to server directory
cd server/

# Create venv
python -m venv venv

# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Flask server
python app.py --host 0.0.0.0 --port 8000
```

### 5. Configure WiFi
Update WiFi credentials in `sketch.ino`:
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverURL = "http://YOUR_SERVER_IP:8000/ingest";
```

---

## 📖 Usage Guide

### Clinical Workflow

1. **Position Device**
   - Hold the MelaNoMore device over the patient's skin lesion
   - **Yellow LED** indicates positioning mode
   - ToF sensor ensures correct distance (3-5 cm)

2. **Capture Image**
   - Once positioned correctly, **Blue LED** activates
   - Image is automatically captured

3. **On-Device Classification**
   - Nicla Vision runs binary classification
   - **Green LED** = Non-suspicious (Done)
   - **Red LED** = Suspicious (Image uploaded to server)

4. **Server Analysis** (for suspicious cases only)
   - Image automatically transmitted via WiFi
   - Vision Transformer performs detailed 7-class classification
   - Results appear on web dashboard

5. **Review Results**
   - Dermatologist reviews detailed classification on PC dashboard
   - Prediction includes lesion type and confidence scores
   - Clinical decision made based on AI recommendation + medical expertise

---

## 💡 LED Feedback System

| LED Color | Meaning |
|-----------|---------|
| 🟡 Yellow | Positioning - adjust distance |
| 🔵 Blue | Capturing image |
| 🟢 Green | Non-suspicious lesion detected |
| 🔴 Red | Suspicious lesion - uploading to server |

---

## 📁 Project Structure

```
SkinCancerDetection_TinyHack/
├── README.md                   # Project overview and documentation
├── 1st_tier/
│   └── sketch.ino              # Arduino Nicla Vision firmware (tier-1 classifier)
├── 2nd_tier/
│   ├── dataset.py              # Dataset utilities for HAM10000
│   ├── evaluate.py             # Evaluation pipeline and metrics
│   ├── metrics.py              # Metric computation helpers
│   ├── model.py                # Vision Transformer model definition
│   ├── train.py                # Training entrypoint
│   ├── visualize.py            # Visual analysis scripts
│   └── requirements.txt        # Python dependencies for training
├── server/
│   ├── app.py                  # Flask server entrypoint
│   ├── classifier.py           # Tier-2 inference orchestration
│   ├── requirements.txt        # Runtime dependencies for the server
│   ├── static/
│   │   ├── dashboard.js        # Dashboard interactivity
│   │   └── styles.css          # Dashboard styling
│   ├── templates/
│   │   ├── base.html           # Base HTML layout
│   │   └── dashboard.html      # Dashboard view
│   ├── models/
│   │   ├── best_model.pth      # Fine-tuned ViT weights
│   │   ├── inference_api.py    # Model loading and inference helpers
│   │   └── INTEGRATION_GUIDE.md  # Deployment/integration notes
│   └── incoming/               # Uploaded lesion images from the device
└── venv/                       # (Optional) Local Python virtual environment
```

---

## ⚡ Technical Highlights

### Edge AI Optimization
- **Quantization**: ONNX model optimized for embedded inference
- **Resolution**: 96x96 input size balances accuracy and speed
- **Offline capability**: On-device inference works without internet

### Server-Side Intelligence
- **Focal Loss**: Addresses class imbalance in HAM10000 dataset
- **Vision Transformer**: State-of-the-art architecture for medical imaging
- **Scalability**: Server can handle multiple concurrent requests

### Sensor Fusion
- **ToF + Camera**: Ensures consistent image quality
- **WiFi + LED**: Provides seamless user experience

---

## 🎯 Future Improvements

- Mobile app integration for patient record management
- Database integration for longitudinal lesion tracking
- Multi-language support for global deployment
- Real-time analytics dashboard for dermatology clinics
- HIPAA-compliant encryption for patient data

---

## 📚 References

- **Dataset**: [HAM10000 - ISIC Archive](https://api.isic-archive.com/collections/212/)
- **Focoos AI**: [Model training and export platform](https://focoos.ai/)
- **Arduino Nicla Vision**: [Official Documentation](https://docs.arduino.cc/hardware/nicla-vision)
- **Z-Ant**: [Beer model timing](https://github.com/ZantFoundation/Z-Ant)
- **Vision Transformer**: [An Image is Worth 16x16 Words](https://arxiv.org/abs/2010.11929)

---

## 📜 License

This project was developed as part of a 24-hour hackathon challenge.

---

## 🙏 Acknowledgments

Special thanks to the organizers of the hackathon and the creators of the Focoos, Zant, and Arduino Nicla Vision platforms for making edge AI accessible to developers.

---

**MelaNoMore** - Empowering dermatologists with AI-driven decision support 🩺

Built with ❤️ by Arslan, Vittorio, and Alessandro
