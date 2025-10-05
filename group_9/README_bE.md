# Hackaton Hands & Gesture Toolkit

This workspace bundles everything we used during the hackathon to capture hand
data, train a Focoos model, deploy it to a Nicla Vision board, and visualise the
predictions inside Unity. The repository is intentionally pragmatic: scripts
are small, easy to tweak, and the build steps are spelled out so you can rerun
them without guesswork.

---
---

## Prerequisites

### Accounts & credentials

* Focoos account with an API key. Export it once before running any scripts:
  ```bash
  export FOCOOS_API_KEY="your-token"
  export FOCOOS_API_TOKEN="$FOCOOS_API_KEY"  # some helpers expect both
  ```

### Tooling

* Python ≥ 3.10
* `pip install focoos opencv-python-headless numpy pillow websockets pyserial tqdm`
* Arduino CLI (for Nicla Vision builds)
* Zig (for Z-Ant codegen) and a working `bash` from Homebrew (`/opt/homebrew/opt/bash/bin/bash`)
* Docker (only needed if you run the optional quantisation/export container steps)

### Hardware

* Arduino Nicla Vision (camera-based gestures)
* Optional: 6‑DoF IMU board speaking over serial for the `arduino_6dof_local.py` pipeline

---

## Data collection & training

1. **Collect new samples (optional).** `collect_hands_dataset.py` creates a
   folder-per-label dataset. Example:
   ```bash
   python collect_hands_dataset.py --dataset data/hands_shaded --labels open pinch fist --camera 0 --five-shades
   ```
   Use the on-screen hotkeys (space to capture, Z/X to change label) to build up
   training images.

2. **Train with Focoos Cloud.** `FOCOOS_HANDS_TRAINING.md` contains the full CLI
   recipe from dataset registration to `model.onnx` export. Follow it when you
   need to retrain or adjust hyperparameters.

3. **Export & place artifacts.** After training, drop the exported `model.onnx`
   into `quantize/export/…` or straight into `Z-Ant/datasets/models/hands/` if
   you plan to regenerate the embedded library immediately.

---

## Embedded Nicla Vision build

The condensed version of `instructions.md` is below. These steps rebuild the
Z-Ant runtime and update the Arduino sketch.

1. **Copy the trained model.**
   ```bash
   cp quantize/export/my_hub_model/model_int8.onnx \
      Z-Ant/datasets/models/hands/hands.onnx
   ```

2. **Regenerate the Z-Ant artefacts.** (Run from `Z-Ant/`)
   ```bash
   /opt/homebrew/opt/bash/bin/bash ./zant input_setter --model hands --shape 1,3,96,96
   /opt/homebrew/opt/bash/bin/bash ./zant shape_thief --model hands
   /opt/homebrew/opt/bash/bin/bash ./zant user_tests_gen --model hands --iterations 20 --normalize
   zig build lib-gen  -Dmodel="hands" -Denable_user_tests -Dxip=true -Dfuse -Ddo_export
   zig build lib-test -Dmodel="hands" -Denable_user_tests
   zig build lib      -Dmodel="hands" -Dtarget=thumb-freestanding -Dcpu=cortex_m7 -Dxip=true
   ```

3. **Install the generated library into Arduino.**
   ```bash
   mkdir -p ~/Documents/Arduino/libraries/ZantLib/src/cortex-m7/fpv5-d16-softfp
   cp Z-Ant/zig-out/hands/libzant.a \
      ~/Documents/Arduino/libraries/ZantLib/src/cortex-m7/fpv5-d16-softfp/ZantLib.a
   cp Z-Ant/generated/hands/lib_hands.h \
      ~/Documents/Arduino/libraries/ZantLib/src/lib_hands.h
   ```

4. **Build and upload the Nicla sketch.**
   ```bash
   arduino-cli compile --fqbn arduino:mbed_nicla:nicla_vision arduinoserver/handsExample
   PORT=/dev/cu.usbmodem1101  # adjust to your board
   arduino-cli upload --fqbn arduino:mbed_nicla:nicla_vision --port "$PORT" arduinoserver/handsExample
   ```

### Sketch preprocessing highlights

`arduinoserver/handsExample/hands.ino` now mirrors the desktop pipeline:

* Converts the RGB565 sensor output to a square crop.
* Resizes to `96×96`, writes separate normalised RGB planes (values 0‑1) into the
  Focoos tensor.
* Runs the `predict` call and streams the highest-confidence gesture as JSON.

---

## Server & visualisation loop

### Python bridge

`arduinoserver/server.py` keeps the Nicla and Unity in sync:

```bash
python arduinoserver/server.py
```

* Listens for newline-delimited JSON on TCP port **9000** (the Nicla sketch
  connects here).
* Mirrors every payload to all **ws://0.0.0.0:8765** WebSocket clients (Unity).
* Maintains a small state snapshot so late-joining Unity instances receive the
  latest gesture straight away.

### Unity scene integration

The `unity/WebSocketObjectSpawner.cs` component is responsible for spawning the
prefabs referenced in `labelPrefabs`.

Key inspector options:

* **Websocket Uri** – defaults to `ws://127.0.0.1:8765`.
* **Label Prefabs** – map gesture labels (as sent by the server) to prefabs.
* **Group By Label** – keeps a single instance per label, preventing duplicate
  objects when the same device updates repeatedly.
* **Debug Controls** (custom inspector):
  * **Spawn All Prefabs** – instantiates every mapped prefab beside the spawner
    using `debugSpawnStart` and `debugSpawnStep` so you can check names/orientations.
  * **Clear Debug Prefabs** – removes the temporary instances.
  * You can optionally assign `debugSpawnRoot` to keep the debug copies inside a
    dedicated parent transform.

At runtime the component maintains a cache keyed by label (or label+device if
you disable grouping) so updates simply reposition the existing GameObject.

---