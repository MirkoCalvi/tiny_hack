#! /bin/bash

export FOCOOS_API_KEY=0be697b9077a4e54a034004ece21430a


# uv run focoos export \
#     --model hub://883972ce265d4922 \
#     --format onnx \
#     --output-dir ./exported_models \
#     --device cpu \
#     --overwrite

uv run quantize.py
