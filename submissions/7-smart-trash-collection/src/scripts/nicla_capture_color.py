#!/usr/bin/env python3
import argparse, sys, time, struct
from pathlib import Path
import numpy as np
import serial, cv2

MAGIC = b"FRMC"
HDR_LEN = 16  # 4 magic + (ver,seq,w,h,pixfmt,payload_len)

def crc32_arduino(payload: bytes) -> int:
    crc = 0xFFFFFFFF
    for b in payload:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xEDB88320 if (crc & 1) else (crc >> 1)
    return (~crc) & 0xFFFFFFFF

def frame_gen(ser: serial.Serial):
    buf = bytearray()
    while True:
        chunk = ser.read(4096)
        if chunk: buf.extend(chunk)
        else: time.sleep(0.001)

        m = buf.find(MAGIC)
        if m < 0:
            if len(buf) > 1_000_000: del buf[:-16]
            continue
        if len(buf) < m + HDR_LEN: continue

        hdr = bytes(buf[m:m+HDR_LEN])
        if hdr[:4] != MAGIC: del buf[:m+1]; continue

        ver, seq, w, h, pixfmt, payload_len = struct.unpack_from("<B H H H B I", hdr, 4)
        if payload_len == 0 or payload_len > 10_000_000:
            del buf[:m+4]; continue

        need = HDR_LEN + payload_len + 4
        if len(buf) < m + need: continue

        start = m + HDR_LEN
        payload = bytes(buf[start:start+payload_len])
        crc_rx  = struct.unpack_from("<I", buf, start+payload_len)[0]
        del buf[:m+need]

        if crc_rx != crc32_arduino(payload):
            print(f"[warn] CRC mismatch seq={seq}", file=sys.stderr);
            continue

        yield (ver, seq, w, h, pixfmt, payload)

def main():
    last_save = 0.0

    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True, help="/dev/ttyACM0 | COMx")
    ap.add_argument("--baud", type=int, default=921600)
    ap.add_argument("--out-dir", type=Path, default=Path("./captures_color"))
    ap.add_argument("--show", action="store_true", help="show live preview")
    ap.add_argument("--little", action="store_true", help="decode RGB565 as little-endian (if colors look wrong)")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.01)
    except Exception as e:
        print(f"Failed to open {args.port}: {e}", file=sys.stderr); sys.exit(1)
    ser.reset_input_buffer()

    print(f"[info] Saving every frame to: {args.out_dir.resolve()}")

    try:
        for (ver, seq, w, h, pixfmt, payload) in frame_gen(ser):
            if len(payload) != w*h*2:
                print(f"[warn] bad payload size {len(payload)} != {w*h*2}", file=sys.stderr)
                continue

            # Decode RGB565
            # Nicla stream uses pixfmt=1 → MSB-first 16-bit (big-endian) by default.
            # If colors look wrong, pass --little to flip interpretation.
            dt = "<u2" if args.little else ">u2"
            arr = np.frombuffer(payload, dtype=dt).reshape(h, w)

            r5 = (arr >> 11) & 0x1F
            g6 = (arr >> 5 ) & 0x3F
            b5 = (arr      ) & 0x1F

            r8 = ((r5 * 255 + 15) // 31).astype(np.uint8)
            g8 = ((g6 * 255 + 31) // 63).astype(np.uint8)
            b8 = ((b5 * 255 + 15) // 31).astype(np.uint8)

            img_bgr = np.dstack([b8, g8, r8])

            # Save every frame
            fn = args.out_dir / f"seq{seq:06d}_{w}x{h}.png"

            # throttle saves to ~5 Hz
            now = time.time()
            wait = 0.5 - (now - last_save)
            if wait > 0:
                time.sleep(wait)
            last_save = time.time()
            cv2.imwrite(str(fn), img_bgr)

            if args.show:
                disp = cv2.resize(img_bgr, (w*3, h*3), interpolation=cv2.INTER_NEAREST)
                cv2.imshow("Nicla Color Capture", disp)
                if (cv2.waitKey(1) & 0xFF) == ord('q'): break

    except KeyboardInterrupt:
        pass
    finally:
        try: ser.close()
        except: pass
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

