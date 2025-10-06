import serial
import numpy as np
from PIL import Image

W, H = 320, 240
SERIAL_PORT = "/dev/ttyACM0"
BAUDRATE = 921600
frame_size = W * H * 2

ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=2)

# --- cerca inizio frame ---
while True:
    line = ser.readline().decode(errors="ignore").strip()
    if line == f"FRAME {W}x{H}:":
        break

# --- leggi frame raw ---
data = ser.read(frame_size)
if len(data) != frame_size:
    raise RuntimeError(f"Frame incompleto: letti {len(data)} byte, attesi {frame_size}")

# --- opzionale: leggi fino a END (consuma i byte residui) ---
while True:
    line = ser.readline().decode(errors="ignore").strip()
    if line == "END":
        break

ser.close()

# --- RGB565 -> RGB888 ---
rgb565 = np.frombuffer(data, dtype=np.uint16)
rgb565 = rgb565.byteswap()  # se l'endianness non coincide

r = ((rgb565 >> 11) & 0x1F) << 3
g = ((rgb565 >> 5) & 0x3F) << 2
b = (rgb565 & 0x1F) << 3

img = np.stack([r, g, b], axis=-1).reshape(H, W, 3).astype(np.uint8)

# --- salva immagine ---
Image.fromarray(img).save("frame.png")
print("✅ Immagine salvata come frame.png")

ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
