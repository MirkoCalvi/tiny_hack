# Smart Trash Collector

A real-time trash classification system connected to Arduino Nicla Vision for live camera-based waste detection and bin sorting.

## Features

- **Real-time predictions** - Watches `predictions.json` for updates
- **Bin highlighting** - Highlights the current active bin
- **Confidence display** - Shows prediction confidence percentage
- **History tracking** - Displays last 10 classifications
- **Auto-refresh** - Updates every 2 seconds

## Quick Start

1. **Install dependencies:**
   ```bash
   cd bin-sorter-simple
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```

3. **Connect to Nicla Vision:**
 
## How It Works

### System Architecture
```
Nicla Vision → Edge AI Inference → Serial/WiFi → Web Interface → Bin Display
     ↓              ↓                    ↓              ↓            ↓
  Camera Feed   Classification      Real-time      Live Updates   Visual
   (96x96px)    (5 categories)     Streaming      (500ms)        Feedback
```

### File Structure
```
bin-sorter-simple/
├── public/
│   └── predictions.json    # Real-time prediction data from Nicla Vision
├── src/
│   ├── components/
│   │   ├── BinDisplay.tsx  # Main display with camera feed
│   │   └── ui/            # UI components
│   └── App.tsx            # App entry point
```

### Real-time Data Format
The system receives live predictions from Nicla Vision:
```json
{
  "category": "plastic",
  "confidence": 0.85,
  "class_id": 4,
  "timestamp": "2024-01-15T10:30:00.000Z",
  "frame_id": 12345,
  "camera_active": true
}
```

### Categories
- `general` (class_id: 0) - General waste 🗑️
- `glass` (class_id: 1) - Glass items 🍷
- `paper` (class_id: 2) - Paper/cardboard 📄
- `organic` (class_id: 3) - Organic waste 🍎
- `plastic` (class_id: 4) - Plastic items ♻️

## Nicla Vision Integration

### Hardware Requirements
- **Arduino Nicla Vision** with camera module
- **USB connection** or **WiFi** for data streaming
- **Power supply** (USB or external)

### Software Setup
1. **Flash the waste classification model** to your Nicla Vision
2. **Configure communication** (Serial or WiFi)
3. **Start the web interface** to receive live predictions

### Communication Methods
- **Serial (USB)**: Direct USB connection for reliable data transfer
- **WiFi**: Wireless connection for remote monitoring
- **WebSocket**: Real-time bidirectional communication

## Production Build

```bash
npm run build
npm run preview
```

This creates a production build that can be served from any static file server.
