# HOWTO Deploy BeezzaAnts on Nicla Vision

<!-- (2025-10-04 17:28 CEST) -->

## Reference Documents

- <https://zantfoundation.github.io/Website/>
- <https://github.com/ZantFoundation/Z-Ant>
- [Tiny_Hack Guide: XIP Weights on Nicla Vision (STM32H747) with Zig + Arduino](https://github.com/ZantFoundation/Z-Ant/blob/tiny_hack/docs/tiny_hack/Guide_XIP_NICLA.pdf) - Team tiny\_hack, 2025-09-04 (PDF, 8 pages)
- [MindBigData 2023 MNIST-8B The 8 billion datapoints Multimodal Dataset of Brain Signals](https://arxiv.org/abs/2306.00455) (PDF, 9 pages)
 
## Step-by-step instructions

<!-- (2025-10-04 17:29 CEST) -->

1. Launch Visual Studio Code

2. VS Code Command Palette: Remote-SSH: Connect to Host...

   - Host: `gmacario@labai-ubnt02`

3. VS Code Command Palette: Git: Clone

   - Repository: Clone from GitHub
   - Repository Name: `B-AROL-O/BeezzaAnts`

4. When asked for "Would you like to open the cloned repository?" click **Open**.

5. When asked for "Do you trust the authors of the files in this folder?" click **Yes, I trust the authors**.

6. VS Code Command Palette: Dev Containers: Rebuild Container Without Cache

7. Select a branch to checkout: `gmacario/dev`

8. VS Code: Terminal > New Terminal

### Make sure that submodules are checked out

Logged in as `vscode@container`

```bash
git submodule update --init --recursive
```

### Verify prerequisites

Logged in as `vscode@container`, make sure that all the prerequisites are met:

```bash
echo $SHELL
python --version
pip --version
uv --version
zig version
arduino-cli version
dfu-util --version
# TODO ./zant
```

<!-- 2025-10-04 17:32 CEST -->

Result:

```text
vscode ➜ /workspaces/BeezzaAnts (gmacario/dev) $ echo $SHELL
/bin/bash
vscode ➜ /workspaces/BeezzaAnts (gmacario/dev) $ python --version
Python 3.10.12
vscode ➜ /workspaces/BeezzaAnts (gmacario/dev) $ pip --version
pip 22.0.2 from /usr/lib/python3/dist-packages/pip (python 3.10)
vscode ➜ /workspaces/BeezzaAnts (gmacario/dev) $ uv --version
uv 0.8.22
vscode ➜ /workspaces/BeezzaAnts (gmacario/dev) $ zig version
0.14.0
vscode ➜ /workspaces/BeezzaAnts (gmacario/dev) $ arduino-cli version
arduino-cli  Version: 1.3.1 Commit: 08ff7e2b Date: 2025-08-28T13:51:45Z
vscode ➜ /workspaces/BeezzaAnts (gmacario/dev) $ dfu-util --version
dfu-util 0.9

Copyright 2005-2009 Weston Schmidt, Harald Welte and OpenMoko Inc.
Copyright 2010-2016 Tormod Volden and Stefan Schmidt
This program is Free Software and has ABSOLUTELY NO WARRANTY
Please report bugs to http://sourceforge.net/p/dfu-util/tickets/

vscode ➜ /workspaces/BeezzaAnts (gmacario/dev) 
```

### Install Python dependencies

```bash
sudo apt update && sudo apt -y install cmake
# cd /workspaces/BeezzaAnts
uv venv
source .venv/bin/activate
uv pip install onnx onnxruntime onnxsim
```

<!--
**NOTE**: with base image: `mcr.microsoft.com/devcontainers/base:noble` package `onnxsim` fails to build
-->

**TODO**: Add to `.devcontainer/devcontainer.json`

### Change working directory

```bash
cd external/Z-Ant
```

### Run `./zant input_setter`

```bash
./zant input_setter \
  --model mnist-8 \
  --shape 1,3,224,224
```

<!-- (2025-10-04 18:53 CEST) -->

Result:

```text
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $ ./zant input_setter \
  --model mnist-8 \
  --shape 1,3,224,224
Executing: python3 src/onnx/input_setter.py --model mnist-8 --shape 1,3,224,224

Processing: datasets/models/mnist-8/mnist-8.onnx
Target shape: [1, 3, 224, 224]
✅ Model loaded successfully
Original model: 8 nodes, 7 initializers

1. Fixing initializer validation issues...
Creating dummy inputs for 7 initializers...
Added 7 dummy inputs for initializers

2. Setting input shape...
Warning: Input 'data' not found. Available inputs:
  - Input3
  - Parameter87
  - Parameter5
  - Pooling160_Output_0_reshape0_shape
  - Parameter194
  - Parameter193_reshape1
  - _v_23
  - _v_24
Using first input: Input3
Updated input 'Input3' shape to: [1, 3, 224, 224]

3. Running shape inference...
✅ Shape inference successful

4. Simplifying model...
Attempting model simplification...
✅ Standard simplification successful!

5. Saving model to: datasets/models/mnist-8/mnist-8.onnx
✅ Model saved successfully!

Final model: 8 nodes, 7 initializers

🎉 Model processing completed successfully!
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $
```

### Run `./zant create mnist-8`

Command:

```bash
./zant create mnist-8
```

<!-- (2025-10-04 18:54 CEST) -->

Result:

```text
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $ ./zant create mnist-8
======================================
Model Pipeline for: mnist-8
Model path: datasets/models/mnist-8/mnist-8.onnx
Build arguments: -Dmodel=mnist-8
======================================
[STEP] Skipping user test generation (--skip-user-tests specified)
[STEP] Skipping node extraction and testing (--skip-extract specified)
[STEP] Generating main library code...


codegenOptions: 
     model:mnist-8 
     model_path:datasets/models/mnist-8/mnist-8.onnx 
     generated_path:generated/mnist-8/ 
     user_tests:false 
     log:false 
     shape: 
     type:f32 
     output_type:f32 
     comm:false 
     dynamic:true 
     version:v1 

 --- Linearized Graph post fusion : 
  Convolution28 
  ReLU32 
  Pooling66 
  Convolution110 
  ReLU114 
  Pooling160 
  Times212_reshape0 
  unnamed 

 Pre-Fusion nodes: 8 
 Post-Fusion nodes: 8
info: 
 .......... file created, path:generated/mnist-8/static_parameters.zig
info: 
 .......... file created, path:generated/mnist-8/lib_mnist-8.zig
info: Attempting to build ExecutionPlan with 8 nodes...
info: ExecutionPlan built successfully with 8 steps!


graph.deinit() ------------- 
  Convolution28.deinit()  
  ReLU32.deinit()  
  Pooling66.deinit()  
  Convolution110.deinit()  
  ReLU114.deinit()  
  Pooling160.deinit()  
  Times212_reshape0.deinit()  
  unnamed.deinit()  info: 

Generated test file: generated/mnist-8/test_mnist-8.zig

[SUCCESS] Library code generation completed
[STEP] Testing generated library...
lib-test
└─ run test_generated_lib 5/6 passed, 1 failed
--- Wrong Input Shape test ---

--- Empty Input test ---

--- Wrong Number of Dimensions test ---

--- User data Prediction test ---
User tests are disabled for this model
error: 'test_mnist-8.test.Static Library - Random data Prediction Test' failed:  ++++++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++ testing mnist-8 ++++++++++++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++
--- Random data Prediction Test ---expected 0, found -1
/opt/zig/lib/std/testing.zig:103:17: 0x10e406c in expectEqualInner__anon_19082 (test_generated_lib)
                return error.TestExpectedEqual;
                ^
/workspaces/BeezzaAnts/external/Z-Ant/generated/mnist-8/test_mnist-8.zig:126:5: 0x10e4552 in test.Static Library - Random data Prediction Test (test_generated_lib)
    try std.testing.expectEqual(0, return_code);
    ^
error: while executing test 'test_mnist-8.test.Static Library - User data Prediction Test', the following test command failed:
/workspaces/BeezzaAnts/external/Z-Ant/.zig-cache/o/82ae57f721908fbeff2d5cc7fac20a27/test_generated_lib --seed=0x9a8188a6 --cache-dir=/workspaces/BeezzaAnts/external/Z-Ant/.zig-cache --listen=- 
Build Summary: 3/5 steps succeeded; 1 failed; 5/6 tests passed; 1 failed
lib-test transitive failure
└─ run test_generated_lib 5/6 passed, 1 failed
error: the following build command failed with exit code 1:
/workspaces/BeezzaAnts/external/Z-Ant/.zig-cache/o/7f05b28ce341a8b494228600978483eb/build /opt/zig/zig /opt/zig/lib /workspaces/BeezzaAnts/external/Z-Ant /workspaces/BeezzaAnts/external/Z-Ant/.zig-cache /home/vscode/.cache/zig --seed 0x9a8188a6 -Zefe428e8f8a3674e lib-test -Dmodel=mnist-8
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $
```

<!--
Verify the Zig source code which has been generated:

```text
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ ls -la generated
total 12
drwxr-xr-x  3 vscode vscode 4096 Oct  3 13:05 .
drwxrwxr-x 18 vscode vscode 4096 Oct  3 13:05 ..
drwxr-xr-x  2 vscode vscode 4096 Oct  3 13:05 mnist-8
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ ls -la generated/mnist-8/
total 120
drwxr-xr-x 2 vscode vscode  4096 Oct  3 13:05 .
drwxr-xr-x 3 vscode vscode  4096 Oct  3 13:05 ..
-rw-r--r-- 1 vscode vscode  7853 Oct  3 13:05 lib_mnist-8.zig
-rw-r--r-- 1 vscode vscode   417 Oct  3 13:05 model_options.zig
-rw-r--r-- 1 vscode vscode 88132 Oct  3 13:05 static_parameters.zig
-rw-r--r-- 1 vscode vscode 12116 Oct  3 13:05 test_mnist-8.zig
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $
```

Verify the compiled library which has been generated:

```text
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ ls -la zig-out/
total 12
drwxr-xr-x  3 vscode vscode 4096 Oct  3 13:05 .
drwxrwxr-x 18 vscode vscode 4096 Oct  3 13:05 ..
drwxr-xr-x  2 vscode vscode 4096 Oct  3 13:05 mnist-8
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ ls -la zig-out/mnist-8/
total 2432
drwxr-xr-x 2 vscode vscode    4096 Oct  3 13:05 .
drwxr-xr-x 3 vscode vscode    4096 Oct  3 13:05 ..
-rw-r--r-- 1 vscode vscode 2481996 Oct  3 13:05 libzant.a
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ ar tvf zig-out/mnist-8/libzant.a 
rw-r--r-- 0/0 2481672 Jan  1 00:00 1970 /workspaces/Z-Ant/.zig-cache/o/b860c1ea062ab417c4cf633b4dd1e351/libzant.a.o
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $
```
-->

### 2. Build the static library of model "beer" with Zig

<!-- (2025-10-04 18:55 CEST) -->

TODO

```bash
TODO
```

#### Run `zig build lib-gen`

Command:

```bash
zig build lib-gen \
  -Dmodel="beer" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests
```

<!-- (2025-10-04 17:45 CEST) -->

Result:

```text
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $ zig build lib-gen \
  -Dmodel="beer" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests


codegenOptions: 
     model:beer 
     model_path:datasets/models/beer/beer.onnx 
     generated_path:generated/beer/ 
     user_tests:true 
     log:false 
     shape: 
     type:f32 
     output_type:f32 
     comm:false 
     dynamic:true 
     version:v1 

 --- Linearized Graph post fusion : 
  model_1/Conv1_relu/Relu6;model_1/bn_Conv1/FusedBatchNormV3;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D;model_1/Conv1/Conv2D__40 
  model_1/Conv1_relu/Relu6;model_1/bn_Conv1/FusedBatchNormV3;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D;model_1/Conv1/Conv2D__40_0_QuantizeLinear 
  model_1/Conv1_relu/Relu6;model_1/bn_Conv1/FusedBatchNormV3;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D;model_1/Conv1/Conv2D_quant 
  model_1/Conv1_relu/Relu6;model_1/bn_Conv1/FusedBatchNormV3;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D;model_1/Conv1/Conv2D_DequantizeLinear 
  Relu6__5 
  Relu6__5_0_QuantizeLinear 
  model_1/expanded_conv_depthwise_relu/Relu6;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D_quant 
  model_1/expanded_conv_depthwise_relu/Relu6;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D_DequantizeLinear 
  Relu6__7 
  Relu6__7_0_QuantizeLinear 
  model_1/expanded_conv_project_BN/FusedBatchNormV3;model_1/block_2_project/Conv2D;model_1/expanded_conv_project/Conv2D1_quant 
  model_1/block_1_expand_relu/Relu6;model_1/block_1_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_1_expand/Conv2D_quant 
  model_1/block_1_expand_relu/Relu6;model_1/block_1_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_1_expand/Conv2D_DequantizeLinear 
  Relu6__10 
  Relu6__10_0_QuantizeLinear 
  model_1/block_1_depthwise_relu/Relu6;model_1/block_1_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_1_depthwise/depthwise_quant 
  model_1/block_1_depthwise_relu/Relu6;model_1/block_1_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_1_depthwise/depthwise_DequantizeLinear 
  Relu6__12 
  Relu6__12_0_QuantizeLinear 
  model_1/block_1_project_BN/FusedBatchNormV3;model_1/block_2_project/Conv2D;model_1/block_1_project/Conv2D1_quant 
  model_1/block_1_project_BN/FusedBatchNormV3;model_1/block_2_project/Conv2D;model_1/block_1_project/Conv2D1_DequantizeLinear 
  model_1/block_2_expand_relu/Relu6;model_1/block_2_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_2_expand/Conv2D_quant 
  model_1/block_2_expand_relu/Relu6;model_1/block_2_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_2_expand/Conv2D_DequantizeLinear 
  Relu6__15 
  Relu6__15_0_QuantizeLinear 
  model_1/block_2_depthwise_relu/Relu6;model_1/block_2_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_2_depthwise/depthwise_quant 
  model_1/block_2_depthwise_relu/Relu6;model_1/block_2_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_2_depthwise/depthwise_DequantizeLinear 
  Relu6__17 
  Relu6__17_0_QuantizeLinear 
  model_1/block_2_project_BN/FusedBatchNormV3;model_1/block_2_project/Conv2D1_quant 
  model_1/block_2_project_BN/FusedBatchNormV3;model_1/block_2_project/Conv2D1_DequantizeLinear 
  model_1/block_2_add/add 
  model_1/block_2_add/add_QuantizeLinear 
  model_1/block_3_expand_relu/Relu6;model_1/block_3_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_3_expand/Conv2D_quant 
  model_1/block_3_expand_relu/Relu6;model_1/block_3_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_3_expand/Conv2D_DequantizeLinear 
  Relu6__20 
  Relu6__20_0_QuantizeLinear 
  model_1/block_3_depthwise_relu/Relu6;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise_quant 
  model_1/block_3_depthwise_relu/Relu6;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise_DequantizeLinear 
  Relu6__22 
  Relu6__22_0_QuantizeLinear 
  model_1/block_3_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D;model_1/block_3_project/Conv2D1_quant 
  model_1/block_3_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D;model_1/block_3_project/Conv2D1_DequantizeLinear 
  model_1/block_4_expand_relu/Relu6;model_1/block_4_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_4_expand/Conv2D_quant 
  model_1/block_4_expand_relu/Relu6;model_1/block_4_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_4_expand/Conv2D_DequantizeLinear 
  Relu6__25 
  Relu6__25_0_QuantizeLinear 
  model_1/block_4_depthwise_relu/Relu6;model_1/block_4_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_4_depthwise/depthwise_quant 
  model_1/block_4_depthwise_relu/Relu6;model_1/block_4_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_4_depthwise/depthwise_DequantizeLinear 
  Relu6__27 
  Relu6__27_0_QuantizeLinear 
  model_1/block_4_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D;model_1/block_4_project/Conv2D1_quant 
  model_1/block_4_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D;model_1/block_4_project/Conv2D1_DequantizeLinear 
  model_1/block_4_add/add 
  model_1/block_4_add/add_QuantizeLinear 
  model_1/block_5_expand_relu/Relu6;model_1/block_5_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_5_expand/Conv2D_quant 
  model_1/block_5_expand_relu/Relu6;model_1/block_5_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_5_expand/Conv2D_DequantizeLinear 
  Relu6__30 
  Relu6__30_0_QuantizeLinear 
  model_1/block_5_depthwise_relu/Relu6;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D_quant 
  model_1/block_5_depthwise_relu/Relu6;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D_DequantizeLinear 
  Relu6__32 
  Relu6__32_0_QuantizeLinear 
  model_1/block_5_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D1_quant 
  model_1/block_5_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D1_DequantizeLinear 
  model_1/block_5_add/add 
  model_1/block_5_add/add_QuantizeLinear 
  model_1/block_6_expand_relu/Relu6;model_1/block_6_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D_quant 
  model_1/block_6_expand_relu/Relu6;model_1/block_6_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D_DequantizeLinear 
  Relu6__35 
  Relu6__35_0_QuantizeLinear 
  model_1/head/Relu;model_1/head/BiasAdd;model_1/head/Conv2D;head/bias_quant 
  model_1/head/Relu;model_1/head/BiasAdd;model_1/head/Conv2D;head/bias_DequantizeLinear 
  Relu__37 
  Relu__37_0_QuantizeLinear 
  model_1/logits/BiasAdd;model_1/logits/Conv2D;logits/bias1_quant 
  model_1/logits/BiasAdd;model_1/logits/Conv2D;logits/bias1_DequantizeLinear 
  StatefulPartitionedCall:0 
  model_1/logits/BiasAdd;model_1/logits/Conv2D;logits/bias1__142 

 Pre-Fusion nodes: 79 
 Post-Fusion nodes: 79
info: 
 .......... file created, path:generated/beer/static_parameters.zig
info: 
 .......... file created, path:generated/beer/lib_beer.zig
info: Attempting to build ExecutionPlan with 79 nodes...
info: ExecutionPlan built successfully with 79 steps!


graph.deinit() ------------- 
  model_1/Conv1_relu/Relu6;model_1/bn_Conv1/FusedBatchNormV3;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D;model_1/Conv1/Conv2D__40.deinit()  
  model_1/Conv1_relu/Relu6;model_1/bn_Conv1/FusedBatchNormV3;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D;model_1/Conv1/Conv2D__40_0_QuantizeLinear.deinit()  
  model_1/Conv1_relu/Relu6;model_1/bn_Conv1/FusedBatchNormV3;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D;model_1/Conv1/Conv2D_quant.deinit()  
  model_1/Conv1_relu/Relu6;model_1/bn_Conv1/FusedBatchNormV3;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D;model_1/Conv1/Conv2D_DequantizeLinear.deinit()  
  Relu6__5.deinit()  
  Relu6__5_0_QuantizeLinear.deinit()  
  model_1/expanded_conv_depthwise_relu/Relu6;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D_quant.deinit()  
  model_1/expanded_conv_depthwise_relu/Relu6;model_1/expanded_conv_depthwise_BN/FusedBatchNormV3;model_1/expanded_conv_depthwise/depthwise;model_1/block_5_project/Conv2D_DequantizeLinear.deinit()  
  Relu6__7.deinit()  
  Relu6__7_0_QuantizeLinear.deinit()  
  model_1/expanded_conv_project_BN/FusedBatchNormV3;model_1/block_2_project/Conv2D;model_1/expanded_conv_project/Conv2D1_quant.deinit()  
  model_1/block_1_expand_relu/Relu6;model_1/block_1_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_1_expand/Conv2D_quant.deinit()  
  model_1/block_1_expand_relu/Relu6;model_1/block_1_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_1_expand/Conv2D_DequantizeLinear.deinit()  
  Relu6__10.deinit()  
  Relu6__10_0_QuantizeLinear.deinit()  
  model_1/block_1_depthwise_relu/Relu6;model_1/block_1_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_1_depthwise/depthwise_quant.deinit()  
  model_1/block_1_depthwise_relu/Relu6;model_1/block_1_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_1_depthwise/depthwise_DequantizeLinear.deinit()  
  Relu6__12.deinit()  
  Relu6__12_0_QuantizeLinear.deinit()  
  model_1/block_1_project_BN/FusedBatchNormV3;model_1/block_2_project/Conv2D;model_1/block_1_project/Conv2D1_quant.deinit()  
  model_1/block_2_expand_relu/Relu6;model_1/block_2_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_2_expand/Conv2D_quant.deinit()  
  model_1/block_1_project_BN/FusedBatchNormV3;model_1/block_2_project/Conv2D;model_1/block_1_project/Conv2D1_DequantizeLinear.deinit()  
  model_1/block_2_expand_relu/Relu6;model_1/block_2_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_2_expand/Conv2D_DequantizeLinear.deinit()  
  Relu6__15.deinit()  
  Relu6__15_0_QuantizeLinear.deinit()  
  model_1/block_2_depthwise_relu/Relu6;model_1/block_2_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_2_depthwise/depthwise_quant.deinit()  
  model_1/block_2_depthwise_relu/Relu6;model_1/block_2_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_2_depthwise/depthwise_DequantizeLinear.deinit()  
  Relu6__17.deinit()  
  Relu6__17_0_QuantizeLinear.deinit()  
  model_1/block_2_project_BN/FusedBatchNormV3;model_1/block_2_project/Conv2D1_quant.deinit()  
  model_1/block_2_project_BN/FusedBatchNormV3;model_1/block_2_project/Conv2D1_DequantizeLinear.deinit()  
  model_1/block_2_add/add.deinit()  
  model_1/block_2_add/add_QuantizeLinear.deinit()  
  model_1/block_3_expand_relu/Relu6;model_1/block_3_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_3_expand/Conv2D_quant.deinit()  
  model_1/block_3_expand_relu/Relu6;model_1/block_3_expand_BN/FusedBatchNormV3;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise;model_1/block_3_expand/Conv2D_DequantizeLinear.deinit()  
  Relu6__20.deinit()  
  Relu6__20_0_QuantizeLinear.deinit()  
  model_1/block_3_depthwise_relu/Relu6;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise_quant.deinit()  
  model_1/block_3_depthwise_relu/Relu6;model_1/block_3_depthwise_BN/FusedBatchNormV3;model_1/block_3_depthwise/depthwise_DequantizeLinear.deinit()  
  Relu6__22.deinit()  
  Relu6__22_0_QuantizeLinear.deinit()  
  model_1/block_3_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D;model_1/block_3_project/Conv2D1_quant.deinit()  
  model_1/block_4_expand_relu/Relu6;model_1/block_4_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_4_expand/Conv2D_quant.deinit()  
  model_1/block_3_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D;model_1/block_3_project/Conv2D1_DequantizeLinear.deinit()  
  model_1/block_4_expand_relu/Relu6;model_1/block_4_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_4_expand/Conv2D_DequantizeLinear.deinit()  
  Relu6__25.deinit()  
  Relu6__25_0_QuantizeLinear.deinit()  
  model_1/block_4_depthwise_relu/Relu6;model_1/block_4_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_4_depthwise/depthwise_quant.deinit()  
  model_1/block_4_depthwise_relu/Relu6;model_1/block_4_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_4_depthwise/depthwise_DequantizeLinear.deinit()  
  Relu6__27.deinit()  
  Relu6__27_0_QuantizeLinear.deinit()  
  model_1/block_4_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D;model_1/block_4_project/Conv2D1_quant.deinit()  
  model_1/block_4_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D;model_1/block_4_project/Conv2D1_DequantizeLinear.deinit()  
  model_1/block_4_add/add.deinit()  
  model_1/block_4_add/add_QuantizeLinear.deinit()  
  model_1/block_5_expand_relu/Relu6;model_1/block_5_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_5_expand/Conv2D_quant.deinit()  
  model_1/block_5_expand_relu/Relu6;model_1/block_5_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D;model_1/block_5_expand/Conv2D_DequantizeLinear.deinit()  
  Relu6__30.deinit()  
  Relu6__30_0_QuantizeLinear.deinit()  
  model_1/block_5_depthwise_relu/Relu6;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D_quant.deinit()  
  model_1/block_5_depthwise_relu/Relu6;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D_DequantizeLinear.deinit()  
  Relu6__32.deinit()  
  Relu6__32_0_QuantizeLinear.deinit()  
  model_1/block_5_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D1_quant.deinit()  
  model_1/block_5_project_BN/FusedBatchNormV3;model_1/block_5_project/Conv2D1_DequantizeLinear.deinit()  
  model_1/block_5_add/add.deinit()  
  model_1/block_5_add/add_QuantizeLinear.deinit()  
  model_1/block_6_expand_relu/Relu6;model_1/block_6_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D_quant.deinit()  
  model_1/block_6_expand_relu/Relu6;model_1/block_6_expand_BN/FusedBatchNormV3;model_1/block_5_depthwise_BN/FusedBatchNormV3;model_1/block_5_depthwise/depthwise;model_1/block_6_expand/Conv2D_DequantizeLinear.deinit()  
  Relu6__35.deinit()  
  Relu6__35_0_QuantizeLinear.deinit()  
  model_1/head/Relu;model_1/head/BiasAdd;model_1/head/Conv2D;head/bias_quant.deinit()  
  model_1/head/Relu;model_1/head/BiasAdd;model_1/head/Conv2D;head/bias_DequantizeLinear.deinit()  
  Relu__37.deinit()  
  Relu__37_0_QuantizeLinear.deinit()  
  model_1/logits/BiasAdd;model_1/logits/Conv2D;logits/bias1_quant.deinit()  
  model_1/logits/BiasAdd;model_1/logits/Conv2D;logits/bias1_DequantizeLinear.deinit()  
  StatefulPartitionedCall:0.deinit()  
  model_1/logits/BiasAdd;model_1/logits/Conv2D;logits/bias1__142.deinit()  info: 

Generated test file: generated/beer/test_beer.zig

(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $
```

#### Run `zig build lib-test`

```bash
zig build lib-test \
  -Dmodel="beer" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests
```

<!-- (2025-10-04 18:58 CEST) -->

Result:

```text
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $ zig build lib-test \
  -Dmodel="beer" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests
lib-test
└─ run test_generated_lib stderr
 +++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++ testing beer ++++++++++++++++++
+++++++++++++++++++++++++++++++++++++++++++++++++++
--- Random data Prediction Test ---
Prediction done without errors

--- Wrong Input Shape test ---

--- Empty Input test ---

--- Wrong Number of Dimensions test ---

--- User data Prediction test ---
User tests loaded.

        Running user test: beer
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $
```

#### Run `zig build lib`

```bash
zig build lib \
  -Dmodel="beer" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests
```

<!-- (2025-10-04 18:58 CEST) -->

Result:

```text
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $ zig build lib \
  -Dmodel="beer" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $
```

Inspect generated code:

```text
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $ ls -la generated/beer/
total 612
drwxr-xr-x 2 vscode vscode   4096 Oct  4 16:02 .
drwxr-xr-x 4 vscode vscode   4096 Oct  4 16:02 ..
-rw-r--r-- 1 vscode vscode 145536 Oct  4 16:55 lib_beer.zig
-rw-r--r-- 1 vscode vscode    408 Oct  4 16:55 model_options.zig
-rw-r--r-- 1 vscode vscode 198516 Oct  4 16:55 static_parameters.zig
-rw-r--r-- 1 vscode vscode  12116 Oct  4 16:55 test_beer.zig
-rw-r--r-- 1 vscode vscode 253848 Oct  4 16:55 user_tests.json
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $
```

This should also generate a `libzant.a` (or similar) under your Zig build output.

```text
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $ ls -la zig-out/beer/
total 3640
drwxr-xr-x 2 vscode vscode    4096 Oct  4 16:58 .
drwxr-xr-x 4 vscode vscode    4096 Oct  4 16:58 ..
-rw-r--r-- 1 vscode vscode 3716476 Oct  4 16:58 libzant.a
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $
```

Inspect the library with the following command

```bash
nm zig-out/beer/libzant.a
```

Sample output:

```text
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $ nm zig-out/beer/libzant.a

/workspaces/BeezzaAnts/external/Z-Ant/.zig-cache/o/3a3d805baf815b5283c58bf35436102b/libzant.a.o:
                 U abort
0000000000006505 r __anon_10015
00000000000005b5 r __anon_10603
00000000000005e0 r __anon_10625
00000000000005f2 r __anon_11122
00000000000005f7 r __anon_11125
0000000000006b40 r __anon_13504
0000000000006e60 r __anon_14587
...
000000000001a902 r posix.use_libc
0000000000020350 t posix.write
                 U pread64
00000000000be4b0 T predict
000000000001aedd r process.Child.native_os
000000000001aee0 r process.Child.ResourceUsageStatistics.rusage_init
0000000000020cc0 t process.hasNonEmptyEnvVarConstant__anon_5645
...
000000000005c020 t __zig_is_named_enum_value_@typeInfo(debug.Dwarf.EntryHeader__union_4181).@"union".tag_type.?
0000000000088be0 t __zig_is_named_enum_value_@typeInfo(debug.Dwarf.expression.StackMachine(.{ .addr_size = 8, .endian = .little, .call_frame_context = true }).Operand).@"union".tag_type.?
0000000000063a70 t __zig_is_named_enum_value_@typeInfo(debug.Dwarf.expression.StackMachine(.{ .addr_size = 8, .endian = .little, .call_frame_context = true }).Value).@"union".tag_type.?
00000000000164d0 t __zig_is_named_enum_value_@typeInfo(debug.Dwarf.FormValue).@"union".tag_type.?
000000000004f8e0 t __zig_is_named_enum_value_@typeInfo(debug.SelfInfo.VirtualMachine.RegisterRule).@"union".tag_type.?
0000000000021e00 t __zig_lt_errors_len
                 U __zig_probe_stack
000000000005c050 t __zig_tag_name_@typeInfo(debug.Dwarf.EntryHeader__union_4181).@"union".tag_type.?
0000000000088c10 t __zig_tag_name_@typeInfo(debug.Dwarf.expression.StackMachine(.{ .addr_size = 8, .endian = .little, .call_frame_context = true }).Operand).@"union".tag_type.?
0000000000063aa0 t __zig_tag_name_@typeInfo(debug.Dwarf.expression.StackMachine(.{ .addr_size = 8, .endian = .little, .call_frame_context = true }).Value).@"union".tag_type.?
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $
```

### 3. Package as an Arduino library

<!-- (2025-10-04 19:11 CEST) -->

Create an Arduino library folder layout under your Arduino `libraries/` directory:

```bash
# Example path: $HOME/Arduino/libraries/ZantLib
mkdir -p $HOME/Arduino/libraries/ZantLib/src/cortex-m7
```

Copy the produced `.a` into `src/cortex-m7/`:

```bash
cp zig-out/beer/libzant.a \
    $HOME/Arduino/libraries/ZantLib/src/cortex-m7
```

Add a `library.properties` file (you can find it at `examples/tiny_hack/ZantLib/library.properties`) at the library root:

```text
# library.properties (example)
name=Zant
version=1.0.0
author=AnonymousZanter <AnonymousZanter@zant.com>
maintainer=AnonymousZanter <AnonymousZanter@zant.com>
sentence=Static Cortex-M7 library
paragraph=Library description
category=Uncategorized
url=https://zantfoundation.github.io/Website/
architectures=mbed_nicla
precompiled=full
includes=lib_zant.h
precompiled=true
ldflags=-lzant
```

Command:

```bash
cp -av \
    examples/tiny_hack/ZantLib \
    $HOME/Arduino/libraries/
```

Result:

```text
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $ cp -av \
    examples/tiny_hack/ZantLib \
    $HOME/Arduino/libraries/
'examples/tiny_hack/ZantLib/library.properties' -> '/home/vscode/Arduino/libraries/ZantLib/library.properties'
'examples/tiny_hack/ZantLib/src/cortex-m7/comments' -> '/home/vscode/Arduino/libraries/ZantLib/src/cortex-m7/comments'
'examples/tiny_hack/ZantLib/src/lib_zant.h' -> '/home/vscode/Arduino/libraries/ZantLib/src/lib_zant.h'
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $
```

Verify the structure of your Arduino library with the following command:

```bash
tree $HOME/Arduino/libraries/ZantLib
```

Actual result:

<!-- (2025-10-04 19:13 CEST) -->

```text
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $ tree $HOME/Arduino/libraries/ZantLib
/home/vscode/Arduino/libraries/ZantLib
├── library.properties
└── src
    ├── cortex-m7
    │   ├── comments
    │   └── libzant.a
    └── lib_zant.h

2 directories, 4 files
(BeezzaAnts) vscode ➜ /workspaces/BeezzaAnts/external/Z-Ant (gmacario/dev) $
```

Your Arduino libraries directory should look like this:

```text
$HOME/Arduino/libraries/ZantLib
                          |...library.properties
                          |...src
                              |...cortex-m7/libzant.a
                              |...lib_zant.a
```

**NOTE**: If your Arduino header is `lib_zant.h`, make sure it declares the prediction entry point (e.g. `int predict(float*, uint32_t*, uint32_t, float**);`).
You can find an example at `examples/tiny_hack/ZantLib/src/lib_zant.h`.

### 4. Arduino sketch: enable QSPI XPI and call `predict`

<!-- (2025-10-04 19:15 CEST) -->

See example in <https://github.com/ZantFoundation/Z-Ant/blob/main/examples/tiny_hack/tiny_hack.ino>

### TODO 5. Custom linker: map `.flash_weights` to QSPI

See example in <https://github.com/ZantFoundation/Z-Ant/blob/main/examples/tiny_hack/custom.ld>

**IMPORTANT**: Your Zig build must emit into a section named `.flash_weights` (or adjust names consistently in both the codegen and this script).
The Arduino sketch exports `flash_weights_base` at `0x90000000` for the Zig library to reference.
So ensure that the flag **-Dxip** is set to true when codegenerating the library.

### 5b. Make sure that the required Arduino core is installed

```bash
arduino-cli core install arduino:mbed_nicla
```

Result:

```text
(BeezzaAnts) vscode ➜ .../external/Z-Ant/examples/tiny_hack (gmacario/dev) $ arduino-cli core install arduino:mbed_nicla
Downloading packages...
arduino:arm-none-eabi-gcc@7-2017q4 downloaded                                                                                                                                                                                                                         
arduino:bossac@1.9.1-arduino2 downloaded                                                                                                                                                                                                                              
arduino:dfu-util@0.10.0-arduino1 downloaded                                                                                                                                                                                                                           
arduino:openocd@0.11.0-arduino2 downloaded                                                                                                                                                                                                                            
arduino:rp2040tools@1.0.6 downloaded                                                                                                                                                                                                                                  
arduino:mbed_nicla@4.4.1 downloaded                                                                                                                                                                                                                                   
Installing arduino:arm-none-eabi-gcc@7-2017q4...
Configuring tool....
arduino:arm-none-eabi-gcc@7-2017q4 installed
Installing arduino:bossac@1.9.1-arduino2...
Configuring tool....
arduino:bossac@1.9.1-arduino2 installed
Installing arduino:dfu-util@0.10.0-arduino1...
Configuring tool....
arduino:dfu-util@0.10.0-arduino1 installed
Installing arduino:openocd@0.11.0-arduino2...
Configuring tool....
arduino:openocd@0.11.0-arduino2 installed
Installing arduino:rp2040tools@1.0.6...
Configuring tool....
arduino:rp2040tools@1.0.6 installed
Installing platform arduino:mbed_nicla@4.4.1...
Configuring platform....

You might need to configure permissions for uploading.
To do so, run the following command from the terminal:
sudo "/home/vscode/.arduino15/packages/arduino/hardware/mbed_nicla/4.4.1/post_install.sh"


Platform arduino:mbed_nicla@4.4.1 installed
(BeezzaAnts) vscode ➜ .../external/Z-Ant/examples/tiny_hack (gmacario/dev) $
```

### 6. Compile with Arduino CLI using the custom linker

From the sketch folder containing `tiny_hack.ino` and `custom.ld`:

```bash
cd examples/tiny_hack
FQBN="arduino:mbed_nicla:nicla_vision"

arduino-cli compile \
  --fqbn "$FQBN" \
  --export-binaries \
  --libraries $HOME/Arduino/libraries \
  --build-property "compiler.c.elf.extra_flags=-Wl,-T$PWD/custom.ld"
```

<!-- (2025-10-04 19:27 CEST) -->

Result:

```text
(BeezzaAnts) vscode ➜ .../external/Z-Ant/examples/tiny_hack (gmacario/dev) $ arduino-cli compile \
  --fqbn "$FQBN" \
  --export-binaries \
  --libraries $HOME/Arduino/libraries \
  --build-property "compiler.c.elf.extra_flags=-Wl,-T$PWD/custom.ld"
Library Zant has been declared precompiled:
Precompiled library in "/home/vscode/Arduino/libraries/ZantLib/src/cortex-m7/fpv5-d16-softfp" not found
Using precompiled library in /home/vscode/Arduino/libraries/ZantLib/src/cortex-m7
/home/vscode/Arduino/libraries/ZantLib/src/cortex-m7/libzant.a: error adding symbols: File format not recognized
collect2: error: ld returned 1 exit status

Used library Version Path
Zant         1.0.0   /home/vscode/Arduino/libraries/ZantLib

Used platform      Version Path
arduino:mbed_nicla 4.4.1   /home/vscode/.arduino15/packages/arduino/hardware/mbed_nicla/4.4.1
Error during build: exit status 1
(BeezzaAnts) vscode ➜ .../external/Z-Ant/examples/tiny_hack (gmacario/dev) $
```

TODO TODO TODO

### TODO 7. Split firmware and weights and flash with DFU

TODO

### TODO 8. Verify at runtime

TODO

### TODO 9. Troubleshooting

TODO

<!-- EOF -->
