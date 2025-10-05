## setup

git clone https://github.com/ZantFoundation/Z-Ant.git or fork 

Zig 0.14 → https://ziglang.org/learn/getting-started/ 
arduino-cli → https://docs.arduino.cc/arduino-cli/ 
dfu-utils

FocoosAI Setup:
Python: >=3.10 and <=3.12
Install SDK:
uv pip install 'focoos[onnx-cpu] @ git+https://github.com/FocoosAI/focoos.git
(For GPU or Colab: use focoos[onnx] instead)

Docs: https://focoosai.github.io/focoos/
Platform Account: Sign up at Focoos AI Platform (free GPU training quotas available!)

## training

recommended model: fai-cls-n-coco

resolution: 96
crop size: 96

data: roboflow.com

## quantization

use real-world dataset for quantization

## compiling

input shape: netron.app

[docs](https://github.com/ZantFoundation/Z-Ant/blob/main/docs/tiny_hack)

[example repo](https://github.com/ZantFoundation/Z-Ant/tree/main/examples/tiny_hack)

max 1.8MB for the model

## ideas

https://chatgpt.com/c/68de368c-b13c-8321-a1ae-b3376f5def54

## steps

1. pick task

2. fine-tune model

3. export onnx

4. quantize

5. compile model for microcontroller

6. make the model run on the microcontroller

7. web interface

8. slides

9. winning

## rating

1. completezza
2. creatività/impatto/simpatia
3. docs/pulizia del codice

