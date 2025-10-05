from db import OrbitData
from PIL import Image
import numpy as np
import serial
import json
import io

### Serial communication variables ###
W, H = 320, 240
FRAME_SIZE = W * H * 2
SERIAL_PORT = "/dev/cu.usbmodem11301"  
BAUD_RATE = 921600

feed = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
feed.reset_output_buffer()
feed.reset_input_buffer()

classification = None
frame = None

def process_feed(ser: serial.Serial):
    global classification, frame, waitingForFrame

    line = feed.readline()

    print(line)

    if not line:
        return

    if line.startswith(b"[PROB]"):
        parts = line[len("[PROB]"):].split(b',')
        classification = [float(v.strip()) for v in parts if v.strip()]

        if all([cls < 0.6 for cls in classification]):
            print("skipping classification")
            classification = None
        else:
            print("classification taken")

    if line.startswith(b"FRAME"):
        data = ser.read(FRAME_SIZE)

        if len(data) != FRAME_SIZE:
            raise RuntimeError(f"Frame incompleto: letti {len(data)} byte, attesi {FRAME_SIZE}")

        while True:
            line = ser.readline().decode(errors="ignore").strip()
            if line == "END":
                break

        rgb565 = np.frombuffer(data, dtype=np.uint16)
        rgb565 = rgb565.byteswap()  # se l'endianness non coincide

        r = ((rgb565 >> 11) & 0x1F) << 3
        g = ((rgb565 >> 5) & 0x3F) << 2
        b = (rgb565 & 0x1F) << 3

        img = np.stack([r, g, b], axis=-1).reshape(H, W, 3).astype(np.uint8)
        img_pil = Image.fromarray(img, mode='RGB')
        
        byte_arr = io.BytesIO()
        img_pil.save(byte_arr, format="PNG")
        frame = byte_arr.getvalue()
        print("frame taken")

    if classification and frame:
        OrbitData.create(classification=json.dumps(classification),image=frame)
        print("row pushed")
        classification = None
        frame = None
