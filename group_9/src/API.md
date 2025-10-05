# API Overview
## Serial/TCP (device → server)

* **Transport:** TCP line protocol on port `9000` (the Arduino sketch uses a Wi‑Fi
  client object but any newline-delimited TCP sender works).
* **Message shape:**
  ```json
  {
    "type": "hand",
    "device": "nicla-vision-hands",
    "id": "hand",
    "gesture": "1",
    "confidence": 0.87,
    "x": 0.0,
    "y": 0.0,
    "z": 0.0
  }
  ```
* Additional message types:
  * `hello` – sent on connection: `{"type":"hello","device":"nicla-vision-hands"}`
  * `error` – when inference fails: `{"type":"error","device":"...","code":<int>}`

## WebSocket (server ↔ Unity)

* **Endpoint:** `ws://<server-host>:8765`
* On connection the server pushes a snapshot:
  ```json
  {
    "source": "snapshot",
    "payload": {
      "last_hello": 1716049000.0,
      "last_message": { ... latest payload ... },
      "detections": [ { ... latest detection ... } ]
    }
  }
  ```
* Live device messages are wrapped as:
  ```json
  {
    "source": "client",
    "payload": { ... same object the device sent ... }
  }
  ```