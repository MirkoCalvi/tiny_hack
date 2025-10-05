import os, json, socket, cv2
from PIL import Image
from focoos import FocoosHUB, ModelManager

HOST, PORT = "192.168.204.232", 9000
API_KEY   = "c6c9d304a1e64419b042d598e7871af1"
MODEL_REF = "hub://a91ce1c3ef164140"
MAX_PER_FRAME = 50

# ---- TCP NDJSON client (persistent connection) ----
class NDJSONClient:
    def __init__(self, host, port, timeout=3.0):
        self.host, self.port, self.timeout = host, port, timeout
        self.sock = None
        self.connect()
    def connect(self):
        if not self.sock:
            self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
    def send(self, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n"
        try:
            self.sock.sendall(data)  # <-- una send per detection
        except (BrokenPipeError, ConnectionResetError, OSError):
            self.close(); self.connect(); self.sock.sendall(data)
    def close(self):
        if self.sock:
            try: self.sock.close()
            finally: self.sock = None

def center_from_xyxy(b):
    x1, y1, x2, y2 = map(int, b)
    return (x1 + x2) // 2, (y1 + y2) // 2

# ---- Setup Focoos + Webcam ----
hub = FocoosHUB(api_key=API_KEY)
model = ModelManager.get(MODEL_REF, hub=hub)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
if not cap.isOpened():
    raise RuntimeError("Webcam not available")

client = NDJSONClient(HOST, PORT)

try:
    print("Streaming active. Press 'q' to stop.")
    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            continue

        pil_img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        res = model.infer(pil_img, threshold=0.5, annotate=False)

        if res.detections:
            for det in sorted(res.detections, key=lambda d: d.conf, reverse=True)[:MAX_PER_FRAME]:
                cx, cy = center_from_xyxy(det.bbox)
                payload = {"type": "detection", "label": str(det.label), "x": cx, "z": cy}
                client.send(payload)
                print("TX:", payload)

        cv2.imshow("cam", frame_bgr)
        if (cv2.waitKey(1) & 0xFF) == ord('q'):
            break

except KeyboardInterrupt:
    pass
finally:
    client.close()
    cap.release()
    cv2.destroyAllWindows()
