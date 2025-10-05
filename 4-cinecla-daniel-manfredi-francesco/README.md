# tiny hack

## context

context.md

## Setup Steps

### 1. Run Frontend

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Run dev server
npm run dev
```

Frontend runs on `http://localhost:5173`

### 2. Run Backend

```bash
# Install dependencies
uv sync

# Run server
cd backend && uv run python run.py
```

Backend runs on `http://0.0.0.0:3002`

### 3. Run macOS Setup

This script installs required tools (Homebrew, arduino-cli, zig, dfu-util, uv) and sets up the Arduino environment for the cards:

```bash
./macos_setup.sh
```

### 4. Run AIO for Serial Cards

Run `./aio.sh` for both cards on serial port number 1 and 2:

```bash
# For first card (serial port 1)
./aio.sh 1

# For second card (serial port 2)
./aio.sh 2
```

The `aio.sh` script takes a command line argument (1 or 2) to specify which card to use.

## How It Works

When `aio.sh` has compiled the model and flashed it onto the card, it calls `tv.py` which:
- Reads the JSON streams from the cards
- Sends them to the backend
- The backend then communicates via WebSocket to the frontend
