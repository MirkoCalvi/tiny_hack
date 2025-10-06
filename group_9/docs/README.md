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

## Desktop inference workflows

### Live webcam test (`webcam_test.py`)

* Provides a tight feedback loop during modelling.
* Mirrors the embedded preprocessing (centre crop, five-shade grayscale with
  inversion, denoise, normalise, black background mask) before sending a frame
  to Focoos.
* Hotkeys:
  * `b` – toggle the five-shade grayscale path
  * `a` – toggle augmentation (brightness/contrast jitter, crops, blur)
  * `s` – save an annotated frame
  * `q` – quit

Run it with:
```bash
python webcam_test.py
```

### Batch a dataset snapshot (`local_hands_object_detection.py`)

Iterates through a directory of images (for example the downloads from your
training run), runs the Focoos model, and writes a JSON report of detections.

```bash
python local_hands_object_detection.py \
  --model ~/Downloads/hands_model.onnx \
  --images-root data/hands_shaded/valid \
  --output workspace_hands/local_predictions.json \
  --show --pause 0.05
```

### 6‑DoF IMU pipeline (`arduino_6dof_local.py`)

Streams accelerometer/gyroscope windows off a serial port, feeds them through a
Focoos classification model, and logs results. Works with either a hub ID or a
local ONNX file.

```bash
python arduino_6dof_local.py --port /dev/cu.usbmodem1101 --model hub://your-imu-model --normalize
```

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

`arduinoserver/handsExample/handsExample.ino` now mirrors the desktop pipeline:

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

## Troubleshooting

| Issue | Check |
| --- | --- |
| Focoos import errors | Verify `pip install focoos` and that `FOCOOS_API_KEY` is set. |
| Webcam feed is dark | Toggle `b` to disable the five-shade mode or improve lighting; the background mask relies on decent contrast. |
| Nicla build fails | Make sure the Zig steps completed without errors and the copied `libzant.a`/`lib_hands.h` overwrite the Arduino versions. |
| Unity spawns duplicates | Ensure **Group By Label** is checked on `WebSocketObjectSpawner`. |
| Unity debug prefabs stay in scene | Hit **Clear Debug Prefabs** in the inspector before saving the scene. |

---

## Useful scripts at a glance

* `hands_pipeline.py` – minimal camera loop kept for reference; `webcam_test.py`
  is the recommended entry point.
* `convert_to_grayscale.py` – utilities used during dataset prep.
* `split_hands_dataset.py` – simple train/val/test splitter if you collect new data.
* `local_hands_object_detection.py` – handy for regression tests after retraining.

Feel free to tailor the scripts to your setup; most of them are deliberately
short and self-documenting.

