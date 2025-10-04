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
uv venv
source .venv/bin/activate
uv pip install onnx onnxruntime
# TODO uv pip install onnx onnxruntime onnxsim
```

<!--
**NOTE**: with base image: `mcr.microsoft.com/devcontainers/base:noble` package `onnxsim` fails to build
-->

**TODO**: Add to `.devcontainer/devcontainer.json`

### Run `./zant create mnist-8`

<!-- (2025-10-03 15:04 CEST) -->

Command:

```bash
uv run ./zant create mnist-8
```

Result:

```text
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ uv run ./zant create mnist-8
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
└─ run test_generated_lib stderr
 ++++++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++ testing mnist-8 ++++++++++++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++
--- Random data Prediction Test ---
Prediction done without errors

--- Wrong Input Shape test ---

--- Empty Input test ---

--- Wrong Number of Dimensions test ---

--- User data Prediction test ---
User tests are disabled for this model
[SUCCESS] Library tests completed
[STEP] Building static library...
[SUCCESS] Static library build completed

======================================
[SUCCESS] Pipeline completed successfully!
======================================
Model: mnist-8
Generated files should be in: generated/mnist-8/
Static library should be in: zig-out/mnist-8/

Additional commands you can run:
  zig build lib-exe -Dmodel=mnist-8    # Run the generated model executable
  zig build benchmark -Dmodel=mnist-8  # Run performance benchmarks
  zig build test -Dmodel=mnist-8       # Run unit tests
======================================
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $
```

<!-- (2025-10-03 15:13 CEST) -->

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

### 2. Build the static library with Zig

#### Run `zig build lib-gen`

<!-- (2025-10-02 15:09 CEST) -->

Command:

```bash
zig build lib-gen \
  -Dmodel="mnist-8" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests
```

Result:

```text
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ zig build lib-gen \
  -Dmodel="mnist-8" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests


codegenOptions: 
     model:mnist-8 
     model_path:datasets/models/mnist-8/mnist-8.onnx 
     generated_path:generated/mnist-8/ 
     user_tests:true 
     log:false 
     shape: 
     type:f32 
     output_type:f32 
     comm:false 
     dynamic:true 
     version:v1 info: 
 .......... file created, path:generated/mnist-8/static_parameters.zig
info: 
 .......... file created, path:generated/mnist-8/lib_mnist-8.zig
info: 

Generated test file: generated/mnist-8/test_mnist-8.zig


=========== ONNX Model Details ===========
Model version: onnx.onnx.Version.IR_VERSION_2019_1_22
Producer: CNTK

Graph Statistics:
  Number of nodes: 8
  Operator distribution:
    Reshape: 1
    Conv: 2
    Gemm: 1
    Relu: 2
    MaxPool: 2

Memory Requirements:
  Total tensors: 9
  Total weight size: 23992 bytes (0.02 MB)
=========================================
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $
```

#### Run `zig build lib-test`

<!-- (2025-10-02 15:09 CEST) -->

```bash
zig build lib-test \
  -Dmodel="mnist-8" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests
```

Result:

```text
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ zig build lib-test \
  -Dmodel="mnist-8" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests
lib-test
└─ run test_generated_lib stderr
 ++++++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++ testing mnist-8 ++++++++++++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++
--- Random data Prediction Test ---
Prediction done without errors:


--- Wrong Input Shape test ---

--- Empty Input test ---

--- Wrong Number of Dimensions test ---

--- User data Prediction test ---
User tests loaded.

        Running user test: mnist-8

 
 expected output  ->  real value      difference  
 -4.1226494e-1 ->  -4.1226524e-1      2.9802322e-7  
 -9.490775e-3 ->  -9.490378e-3      3.9674342e-7  
 6.233672e-1 ->  6.2336653e-1      6.556511e-7  
 6.694817e-1 ->  6.6948164e-1      5.9604645e-8  
 -6.0755527e-1 ->  -6.0755515e-1      1.1920929e-7  
 1.0273058e0 ->  1.0273058e0      0e0  
 -5.273663e-1 ->  -5.273664e-1      1.1920929e-7  
 -1.7929406e-1 ->  -1.7929403e-1      2.9802322e-8  
 -3.159709e-1 ->  -3.159712e-1      2.9802322e-7  
 -8.7684447e-1 ->  -8.7684494e-1      4.7683716e-7 
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $
```

#### Run `zig build lib`

<!-- (2025-10-02 15:10 CEST) -->

```bash
zig build lib \
  -Dmodel="mnist-8" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests
```

Result:

```text
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ zig build lib \
  -Dmodel="mnist-8" \
  -Dxip=true \
  -Ddynamic \
  -Ddo_export \
  -Denable_user_tests
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $
```

This should generate a `libzant.a` (or similar) under your Zig build output.

TODO

### 3. Package as an Arduino library

<!-- (2025-10-03 15:30 CEST) -->

Create an Arduino library folder layout under your Arduino `libraries/` directory:

```bash
# Example path: $HOME/Arduino/libraries/ZantLib
mkdir -p $HOME/Arduino/libraries/ZantLib/src/cortex-m7
```

Copy the produced `.a` into `src/cortex-m7/`:

```bash
cp zig-out/mnist-8/libzant.a \
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
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ cp -av examples/tiny_hack/ZantLib $HOME/Arduino/libraries/
'examples/tiny_hack/ZantLib/library.properties' -> '/home/vscode/Arduino/libraries/ZantLib/library.properties'
'examples/tiny_hack/ZantLib/src/cortex-m7/comments' -> '/home/vscode/Arduino/libraries/ZantLib/src/cortex-m7/comments'
'examples/tiny_hack/ZantLib/src/lib_zant.h' -> '/home/vscode/Arduino/libraries/ZantLib/src/lib_zant.h'
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $
```

Your Arduino libraries directory should look like this:

```text
$HOME/Arduino/libraries/ZantLib
                          |...library.properties
                          |...src
                              |...cortex-m7/libzant.a
                              |...lib_zant.a
```

Actual result:

```text
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ tree $HOME/Arduino/libraries/ZantLib
/home/vscode/Arduino/libraries/ZantLib
├── library.properties
└── src
    ├── cortex-m7
    │   ├── comments
    │   └── libzant.a
    └── lib_zant.h

2 directories, 4 files
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $
```

**NOTE**: If your Arduino header is `lib_zant.h`, make sure it declares the prediction entry point (e.g. `int predict(float*, uint32_t*, uint32_t, float**);`).
You can find an example at `examples/tiny_hack/ZantLib/src/lib_zant.h`.

### TODO 4. Arduino sketch: enable QSPI XPI and call `predict`

TODO

### TODO 5. Custom linker: map `.flash_weights` to QSPI

TODO

**IMPORTANT**: Your Zig build must emit into a section named `.flash_weights` (or adjust names consistently in both the codegen and this script).
The Arduino sketch exports `flash_weights_base` at `0x90000000` for the Zig library to reference.
So ensure that the flag **-Dxip** is set to true when codegenerating the library.

### TODO: 6. Compile with Arduino CLI using the custom linker

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

<!-- (2025-10-03 15:36 CEST) -->

Result:

```text
(Z-Ant) vscode ➜ /workspaces/Z-Ant (gmacario/dev) $ cd examples/tiny_hack/
(Z-Ant) vscode ➜ /workspaces/Z-Ant/examples/tiny_hack (gmacario/dev) $ FQBN="arduino:mbed_nicla:nicla_vision"
(Z-Ant) vscode ➜ /workspaces/Z-Ant/examples/tiny_hack (gmacario/dev) $ arduino-cli compile \
  --fqbn "$FQBN" \
  --export-binaries \
  --libraries $HOME/Arduino/libraries \
  --build-property "compiler.c.elf.extra_flags=-Wl,-T$PWD/custom.ld"
Downloading index: library_index.tar.bz2 downloaded                                                                   
Downloading index: package_index.tar.bz2 downloaded
Downloading missing tool builtin:ctags@5.8-arduino11...
builtin:ctags@5.8-arduino11 downloaded
Installing builtin:ctags@5.8-arduino11...
Skipping tool configuration....
builtin:ctags@5.8-arduino11 installed
Downloading missing tool builtin:dfu-discovery@0.1.2...
builtin:dfu-discovery@0.1.2 downloaded
Installing builtin:dfu-discovery@0.1.2...
Skipping tool configuration....
builtin:dfu-discovery@0.1.2 installed
Downloading missing tool builtin:mdns-discovery@1.0.9...
builtin:mdns-discovery@1.0.9 downloaded
Installing builtin:mdns-discovery@1.0.9...
Skipping tool configuration....
builtin:mdns-discovery@1.0.9 installed
Downloading missing tool builtin:serial-discovery@1.4.1...
builtin:serial-discovery@1.4.1 downloaded
Installing builtin:serial-discovery@1.4.1...
Skipping tool configuration....
builtin:serial-discovery@1.4.1 installed
Downloading missing tool builtin:serial-monitor@0.15.0...
builtin:serial-monitor@0.15.0 downloaded
Installing builtin:serial-monitor@0.15.0...
Skipping tool configuration....
builtin:serial-monitor@0.15.0 installed
Error during build: Platform 'arduino:mbed_nicla' not found: platform not installed
Try running `arduino-cli core install arduino:mbed_nicla`
(Z-Ant) vscode ➜ /workspaces/Z-Ant/examples/tiny_hack (gmacario/dev) $
```

<!-- (2025-10-03 15:40 CEST) -->

Apply the suggested fix:

```text
(Z-Ant) vscode ➜ /workspaces/Z-Ant/examples/tiny_hack (gmacario/dev) $ arduino-cli core install arduino:mbed_nicla
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
(Z-Ant) vscode ➜ /workspaces/Z-Ant/examples/tiny_hack (gmacario/dev) $
```

<!-- (2025-10-03 15:44 CEST) -->

then retry:

```bash
arduino-cli compile \
  --fqbn "$FQBN" \
  --export-binaries \
  --libraries $HOME/Arduino/libraries \
  --build-property "compiler.c.elf.extra_flags=-Wl,-T$PWD/custom.ld"
```

Result:
```
(Z-Ant) vscode ➜ /workspaces/Z-Ant/examples/tiny_hack (gmacario/dev) $ arduino-cli compile \
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
(Z-Ant) vscode ➜ /workspaces/Z-Ant/examples/tiny_hack (gmacario/dev) $
```

TODO TODO TODO

### TODO 7. Split firmware and weights and flash with DFU

TODO

### TODO 8. Verify at runtime

TODO

### TODO 9. Troubleshooting

TODO

<!-- EOF -->
