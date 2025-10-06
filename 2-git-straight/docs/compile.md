Compilation:
```sh
docker build -t zant 
```

After having copied over the model in onnx format to `datasets/models/$MODEL_NAME/$MODEL_NAME`:
```sh
export MODEL_NAME="model-name"
./zant input_setter --model $MODEL_NAME --shape 1,3,96,96
./zant user_tests_gen --model $MODEL_NAME
```

```sh
zig build lib-gen \
    -Dmodel=$MODEL_NAME \
    -Dxip=true \
    -Ddo_export \
    -Dfuse \
    -Denable_user_tests
zig build lib-test \
    -Dmodel=$MODEL_NAME \
    -Dxip=true \
    -Ddo_export \
    -Ddynamic \
    -Denable_user_tests
zig build lib \
    -Dmodel=$MODEL_NAME \
    -Dtarget=thumb-freestanding \
    -Dcpu=cortex_m7 \
    -Dxip=true \
    -freference-trace \
    -Doptimize=ReleaseFast
```

```sh
arduino-cli compile \
  --fqbn "arduino:mbed_nicla:nicla_vision" \
  --export-binaries \
  --libraries $ARDUINO_LIBS \
  --build-property "compiler.c.elf.extra_flags=-Wl,-T$PWD/custom.ld"
```
Flashing script:
```sh
./flash.sh
```
