#!/usr/bin/env python3
import argparse
import platform
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

try:
    import serial
    import serial.tools.list_ports
except Exception as e:
    print("pyserial is required. Install with: pip install pyserial", file=sys.stderr)
    raise

LINE_REGEX = re.compile(
    r"top1:\s*idx=(\d+)\s+label=([^\s]+)\s+prob=([0-9]*\.?[0-9]+)",
    re.IGNORECASE,
)

@dataclass
class Event:
    idx: int
    label: str
    prob: float
    ts: datetime
    raw: str

def parse_line(line: str) -> Optional[Event]:
    m = LINE_REGEX.search(line)
    if not m:
        return None
    try:
        idx = int(m.group(1))
        label = m.group(2)
        prob = float(m.group(3))
        return Event(idx=idx, label=label, prob=prob, ts=datetime.now(), raw=line)
    except Exception:
        return None

def pick_default_port() -> Optional[str]:
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None
    def score(p):
        desc = f"{p.description} {p.manufacturer or ''}".lower()
        dev  = p.device.lower()
        s = 0
        if "arduino" in desc or "nicla" in desc: s += 3
        if "usbmodem" in dev or "usbserial" in dev or "ttyacm" in dev: s += 2
        return s
    ports.sort(key=score, reverse=True)
    return ports[0].device

def play_sound():
    # Cross-platform best-effort sound
    osname = platform.system()
    try:
        if osname == "Darwin":  # macOS
            import subprocess
            subprocess.Popen(["afplay", "/System/Library/Sounds/Ping.aiff"])
            return
        elif osname == "Windows":
            import winsound
            winsound.MessageBeep()
            return
        else:  # Linux/other
            import subprocess
            # Try paplay, then aplay; otherwise fallback to terminal bell
            for cmd in (["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                        ["aplay", "/usr/share/sounds/alsa/Front_Center.wav"]):
                try:
                    subprocess.Popen(cmd)
                    return
                except Exception:
                    continue
    except Exception:
        pass
    # Fallback: terminal bell
    try:
        print("\a", end="", flush=True)
    except Exception:
        pass

class SustainedDetector:
    """Triggers when a (label, prob>=thr) condition holds continuously for sustain_secs.
    Resets when the condition breaks; triggers once per continuous episode (with cooldown)."""
    def __init__(self, target_label: str, prob_thr: float, sustain_secs: float, cooldown_secs: float = 1.0):
        self.target_label = target_label.lower()
        self.prob_thr = prob_thr
        self.sustain = timedelta(seconds=sustain_secs)
        self.cooldown = timedelta(seconds=cooldown_secs)
        self.window_start: Optional[datetime] = None
        self.latched: bool = False
        self.last_trigger_time: Optional[datetime] = None

    def update(self, ev: Event) -> Optional[datetime]:
        ok = ev.label.lower() == self.target_label and ev.prob >= self.prob_thr
        now = ev.ts
        if ok:
            if self.window_start is None:
                self.window_start = now
                self.latched = False  # new episode
            # Check sustained
            if (now - self.window_start) >= self.sustain and not self.latched:
                # Enforce cooldown to avoid bursts
                if self.last_trigger_time is None or (now - self.last_trigger_time) >= self.cooldown:
                    self.latched = True
                    self.last_trigger_time = now
                    return now  # trigger moment
            return None
        else:
            # Condition broken: reset state
            self.window_start = None
            self.latched = False
            return None

def main():
    ap = argparse.ArgumentParser(description="Sustained 'bad' detector with sound alert.")
    ap.add_argument("-p","--port", help="Serial port (auto-pick if omitted).")
    ap.add_argument("-b","--baud", type=int, default=115200, help="Baud rate (default: 115200).")
    ap.add_argument("--no-reset", action="store_true", help="Avoid toggling DTR/RTS to prevent auto-reset.")
    ap.add_argument("--label", default="bad", help="Target label to watch (default: bad).")
    ap.add_argument("-t","--threshold", type=float, default=0.80, help="Probability threshold (default: 0.80).")
    ap.add_argument("--sustain", type=float, default=3.0, help="Seconds the condition must hold (default: 3.0).")
    ap.add_argument("--show", action="store_true", help="Echo device output lines.")
    args = ap.parse_args()

    port = args.port or pick_default_port()
    if not port:
        print("No serial ports found. Try: python -m serial.tools.list_ports -v", file=sys.stderr)
        sys.exit(2)

    ser = serial.Serial()
    ser.port = port
    ser.baudrate = args.baud
    ser.timeout = 0.2
    ser.write_timeout = 0.2
    if args.no_reset:
        ser.dtr = False
        ser.rts = False

    ser.open()
    if not args.no_reset:
        time.sleep(2.0)
    ser.reset_input_buffer()
    print(f"[sustain] Connected to {port} @ {args.baud}. Watching label='{args.label}', thr={args.threshold}, sustain={args.sustain}s", file=sys.stderr)

    detector = SustainedDetector(target_label=args.label, prob_thr=args.threshold, sustain_secs=args.sustain)

    try:
        while True:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if args.show:
                print(line)

            ev = parse_line(line)
            if not ev:
                continue
            ts = detector.update(ev)
            if ts:
                print(f"[ALERT {ts.strftime('%H:%M:%S')}] label={ev.label} prob={ev.prob:.3f} sustained {args.sustain:.1f}s — playing sound", file=sys.stderr)
                play_sound()
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print("[sustain] Disconnected.", file=sys.stderr)

if __name__ == "__main__":
    main()
