<div align="center">
  <img src="img/loghi.png" alt="Alt text" width="900" >
</div>

# 🍄 AllucInation

**AllucInation** is an intelligent embedded system designed to **classify mushrooms** as either **edible** or **poisonous** using **machine learning** and **IoT integration**.  
Developed by **Ezmiron Deniku**, **Stiven Gjinaj**, **Alberto Giunti**, and **Daniele Gagni**, this project bridges **embedded vision**, **AI inference**, and **web technologies** to deliver a seamless classification experience.

---

## 🌟 Project Overview

The core of **AllucInation** lies in combining an **Arduino Nicla Vision** board supporting for offline inference with a **React-based web interface** and a **Node.js backend**.

- The **Nicla Vision** captures an image of a mushroom 🧠📷
- The onboard or external model classifies it as **edible** or **poisonous** ☠️
- The classification and image are sent to a **backend** for storage 🗃️
- The **frontend** displays results and allows live interaction 🌐

---

## 🧩 Folder Structure

```

AllucInation/
├── backend/                # ⚙️ Node.js backend for data storage and API
│   └── server.mjs           # Express server receiving images and classification
│
├── frontend/               # 💻 React web interface for visualization
│   ├── src/
│   ├── public/
│   └── package.json
│
├── Z-Ant/
│   ├── datasets/
│   │   └── models/
│   │       └── mushroom/   # 🧠 Pre-trained model and JSON specification
│   │           ├── mushroom.onnx
│   │           └── mushroom.json
│   │
│   └── examples/
│       └── tiny_hack/
│           └── tiny_hack.ino  # 💡 Core Arduino Nicla script
│
└── README.md               # 📘 Project documentation

```

---

## 🧠 Embedded System — Nicla Vision

The **Nicla Vision** acts as the intelligent sensor node of the project.

📸 **Responsibilities:**
- Captures an image of the mushroom in front of it  
- Processes the image locally or sends it for remote inference  
- Sends results (image + classification) to the backend server over Wi-Fi  

💾 The main script controlling this behavior is located at:
```

Z-Ant/examples/tiny_hack/tiny_hack.ino

```

---

## 🖥️ Backend

The **backend** handles the communication between the embedded system and the web interface.

⚙️ **Features:**
- Receives and stores images from the Nicla Vision
- Logs classification results (edible/poisonous)
- Provides REST API endpoints for the frontend

💡 **Technologies:**
- Node.js
- Express.js
- Multer (for handling image uploads)

---

## 🌐 Frontend

The **frontend** provides a user-friendly interface to visualize the classifications performed by the embedded system.

✨ **Features:**
- Displays real-time mushroom classifications
- Shows stored images and labels
- Simple and modern React UI for interaction

💡 **Technologies:**
- React.js
- Axios (for communicating with the backend)
- Tailwind CSS (for styling)

---

## 🧠 AI Model

The **mushroom classification model** is stored in:
```

Z-Ant/datasets/models/mushroom/

````

This folder includes:
- `mushroom.onxx` → The trained TensorFlow Lite model  
- `mushroom.json` → Model metadata and input/output specifications  

The model takes as input an image captured by the Nicla and predicts whether the mushroom is **🍽️ edible** or **☠️ poisonous**.

---

## 🚀 Getting Started

### 🔧 Requirements
- Arduino Nicla Vision  
- Node.js (v18+)
- npm or yarn
- React environment setup
- Wi-Fi connection for the Nicla and host machine

### 🧰 Installation

1. **Clone the repository**
   ```bash
   git clone --recursive https://github.com/ezmi234/tiny_hack.git AllucInation
   cd AllucInation
    ```

2. **Run the backend**

   ```bash
   cd backend
   npm install
   npm start
   ```

3. **Run the frontend**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Upload the Arduino sketch**

   * Open `Z-Ant/examples/tiny_hack/tiny_hack.ino` in Arduino IDE
   * Configure your Wi-Fi credentials and server IP
   * Upload to the Nicla Vision board

---

## 🧪 How It Works

1. Nicla Vision captures a photo of a mushroom 🍄
2. The model classifies it (Edible or Poisonous)
3. The image and classification are sent to the backend 🛰️
4. The frontend fetches and displays the latest results in real-time 📊

---

## 👨‍💻 Authors

| Name               | Role                                 |
|--------------------|--------------------------------------|
| **Ezmiron Deniku** | Machine Learning & Model Development |
| **Stiven Gjinaj**  | Embedded System & Integration        |
| **Alberto Giunti** | Backend & API Design                 |
| **Daniele Gagni**  | Frontend & UI Development            |

---

## 🧭 Future Improvements

* Implement live video streaming 🌐
* Expand dataset for better model generalization 🍄📊
* Deploy full-stack app using Docker 🐳

---

## 🏁 License

This project is developed for educational and research purposes.
All rights reserved © 2025 by **Ezmiron Deniku**, **Stiven Gjinaj**, **Alberto Giunti**, and **Daniele Gagni**.

---

```
