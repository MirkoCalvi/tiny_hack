#!/usr/bin/env python3
"""
nicla_viewer.py — Visualize Nicla 'FRME' grayscale frames over serial.

Protocol (little-endian):
  MAGIC: 'FRME' (4 bytes)
  ver: uint8
  seq: uint16
  w:   uint16
  h:   uint16
  cls: uint8
  prob_x1000: uint16
  ms_x10:     uint16
  payload_len: uint32   (should be w*h)
  payload: gray bytes
  crc32:   uint32       (Arduino-style of payload only)

Keys:
  q = quit
  s = save PNG of current frame
"""

import argparse
import sys
import time
import struct
from pathlib import Path

import numpy as np
import serial
import cv2

MAGIC = b"FRME"
HEADER_LEN = 20  # 4 (MAGIC) + 16 rest
# Class names (adjust if you change your firmware table)
CLASS_NAMES = ["general", "glass", "organic", "paper", "plastic"]

def crc32_arduino(payload: bytes) -> int:
    """Match the Arduino bitwise CRC (init 0xFFFFFFFF, poly 0xEDB88320, final ~)."""
    crc = 0xFFFFFFFF
    for byte in payload:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return (~crc) & 0xFFFFFFFF

def find_magic(buf: bytearray) -> int:
    """Return index of MAGIC in buf or -1."""
    return buf.find(MAGIC)

def read_exact(ser: serial.Serial, n: int, timeout_s: float = 5.0) -> bytes:
    """Read exactly n bytes or raise TimeoutError."""
    out = bytearray()
    t0 = time.time()
    while len(out) < n:
        chunk = ser.read(n - len(out))
        if chunk:
            out.extend(chunk)
        else:
            if (time.time() - t0) > timeout_s:
                raise TimeoutError(f"Timed out reading {n} bytes (got {len(out)})")
    return bytes(out)

def parse_header(hdr: bytes):
    assert len(hdr) == HEADER_LEN
    if hdr[:4] != MAGIC:
        raise ValueError("Bad MAGIC")
    # <B H H H B H H I  (little-endian)
    ver, seq, w, h, cls, prob_x1000, ms_x10, payload_len = struct.unpack_from(
        "<B H H H B H H I", hdr, 4
    )
    return {
        "ver": ver,
        "seq": seq,
        "w": w,
        "h": h,
        "cls": cls,
        "prob": prob_x1000 / 1000.0,
        "ms": ms_x10 / 10.0,
        "payload_len": payload_len,
    }

def frame_generator(ser: serial.Serial):
    """Yield parsed frames as dicts with keys: meta, img (H,W uint8)."""
    buf = bytearray()
    while True:
        # Read whatever is available
        chunk = ser.read(4096)
        if chunk:
            buf.extend(chunk)
        else:
            # small sleep prevents tight spin when no data
            time.sleep(0.001)

        # Try to find MAGIC
        m = find_magic(buf)
        if m < 0:
            # keep buffer reasonable
            if len(buf) > 1_000_000:
                del buf[:-16]
            continue

        # Ensure we have full header
        if len(buf) < m + HEADER_LEN:
            continue  # wait for more

        hdr = bytes(buf[m : m + HEADER_LEN])
        try:
            meta = parse_header(hdr)
        except Exception:
            # If header is corrupt, drop this MAGIC and continue
            del buf[: m + 1]
            continue

        need = meta["payload_len"] + 4  # payload + CRC
        total_needed = HEADER_LEN + need
        if meta["payload_len"] > 10_000_000:  # sanity guard
            # something's wrong, skip this MAGIC
            del buf[: m + 4]
            continue

        # Wait for full frame
        if len(buf) < m + total_needed:
            continue

        # Extract payload + crc
        start = m + HEADER_LEN
        payload = bytes(buf[start : start + meta["payload_len"]])
        crc_rx = struct.unpack_from("<I", buf, start + meta["payload_len"])[0]
        crc_calc = crc32_arduino(payload)

        # Advance buffer
        del buf[: m + total_needed]

        if crc_rx != crc_calc:
            print(
                f"[warn] CRC mismatch (seq {meta['seq']}): rx=0x{crc_rx:08X}, calc=0x{crc_calc:08X}",
                file=sys.stderr,
            )
            continue

        # Convert payload into image
        w, h = meta["w"], meta["h"]
        if len(payload) != w * h:
            print(
                f"[warn] Bad payload size (seq {meta['seq']}): expected {w*h}, got {len(payload)}",
                file=sys.stderr,
            )
            continue

        img = np.frombuffer(payload, dtype=np.uint8).reshape((h, w))
        yield {"meta": meta, "img": img}

def draw_overlay(frame: np.ndarray, text_lines, scale=1.0):
    y = 18
    for line in text_lines:
        cv2.putText(
            frame,
            line,
            (8, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45 * scale,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        y += int(18 * scale)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True, help="Serial port (e.g., /dev/ttyACM0)")
    ap.add_argument("--baud", type=int, default=921600, help="Baud rate")
    ap.add_argument("--scale", type=int, default=4, help="Integer upscaling factor for display")
    ap.add_argument("--save-dir", type=Path, default=Path("./captures"), help="Where to save PNGs on 's'")
    ap.add_argument("--no-overlay", action="store_true", help="Disable overlay text")
    args = ap.parse_args()

    args.save_dir.mkdir(parents=True, exist_ok=True)

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.01)
    except Exception as e:
        print(f"Failed to open {args.port}: {e}", file=sys.stderr)
        sys.exit(1)

    # Flush any pending text/noise
    ser.reset_input_buffer()

    win = "Nicla FRME Viewer"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    last_t = time.time()
    fps = 0.0
    n = 0

    try:
        for fr in frame_generator(ser):
            meta = fr["meta"]
            img = fr["img"]

            # Upscale for readability
            if args.scale > 1:
                img_disp = cv2.resize(img, (img.shape[1]*args.scale, img.shape[0]*args.scale), interpolation=cv2.INTER_NEAREST)
            else:
                img_disp = img

            img_disp = cv2.cvtColor(img_disp, cv2.COLOR_GRAY2BGR)

            # FPS (simple EMA)
            now = time.time()
            dt = now - last_t
            last_t = now
            if dt > 0:
                if n == 0:
                    fps = 1.0 / dt
                else:
                    fps = 0.9 * fps + 0.1 * (1.0 / dt)
            n += 1

            # Overlay
            if not args.no_overlay:
                cls = meta["cls"]
                name = CLASS_NAMES[cls] if 0 <= cls < len(CLASS_NAMES) else f"id{cls}"
                lines = [
                    f"seq: {meta['seq']}  ver: {meta['ver']}  fps: {fps:4.1f}",
                    f"size: {meta['w']}x{meta['h']}",
                    f"class: {cls} ({name})  prob: {meta['prob']:.3f}  time: {meta['ms']:.1f} ms",
                ]
                draw_overlay(img_disp, lines, scale=max(1, args.scale/2))

            cv2.imshow(win, img_disp)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save PNG with metadata in filename
                out_path = args.save_dir / f"frame_seq{meta['seq']:05d}_cls{meta['cls']}_p{int(meta['prob']*1000):04d}.png"
                cv2.imwrite(str(out_path), img)
                print(f"Saved {out_path}")

    except KeyboardInterrupt:
        pass
    except TimeoutError as e:
        print(f"[error] {e}", file=sys.stderr)
    finally:
        try:
            ser.close()
        except Exception:
            pass
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

