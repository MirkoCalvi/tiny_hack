#!/usr/bin/env python3
import argparse, json, os, re, sys
import serial

# Example line:
# [Waste Selector]: idx=2 label=Glass prob=0.873 time=41.2 ms
LINE_RE = re.compile(
    r"\[Waste Selector\]:\s*idx=(?P<idx>\d+)\s+label=(?P<label>\S+)\s+prob=(?P<prob>[0-9]*\.?[0-9]+)\s+time=(?P<ms>[0-9]*\.?[0-9]+)\s*ms",
    re.IGNORECASE,
)

def atomic_write_json(path, obj):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def main():
    ap = argparse.ArgumentParser(description="Nicla → predictions.json")
    ap.add_argument("--port", required=True, help="/dev/ttyACM0 | COMx")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--outfile", default="predictions.json")
    ap.add_argument("--detections", type=int, default=0, help="value for 'detections' field")
    ap.add_argument("--echo", action="store_true", help="print parsed lines")
    args = ap.parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.2)
    except Exception as e:
        print(f"[error] open {args.port}: {e}", file=sys.stderr); sys.exit(1)
    ser.reset_input_buffer()

    print(f"[info] listening on {args.port}@{args.baud}, writing → {args.outfile}")
    try:
        while True:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue
            m = LINE_RE.search(line)
            if not m:
                continue

            idx   = int(m.group("idx"))
            label = m.group("label").lower()  # "Plastic" -> "plastic"
            prob  = float(m.group("prob"))

            payload = {
                "category":   label,
                "confidence": prob,
                "class_id":   idx,
                "detections": args.detections
            }
            atomic_write_json(args.outfile, payload)
            if args.echo:
                print(payload)
    except KeyboardInterrupt:
        pass
    finally:
        try: ser.close()
        except: pass

if __name__ == "__main__":
    main()
