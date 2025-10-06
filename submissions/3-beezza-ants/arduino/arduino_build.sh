#!/bin/bash

FQBN="arduino:mbed_nicla:nicla_vision"

arduino-cli compile \
  --fqbn "$FQBN" \
  --export-binaries \
  --libraries $HOME/Arduino/libraries \
  --build-property "compiler.c.elf.extra_flags=-Wl,-T$PWD/custom.ld"


# EOF
