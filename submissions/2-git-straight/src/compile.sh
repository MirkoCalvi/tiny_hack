arduino-cli compile \
  --fqbn "arduino:mbed_nicla:nicla_vision" \
  --export-binaries \
  --libraries $ARDUINO_LIBS \
  --build-property "compiler.c.elf.extra_flags=-Wl,-T$PWD/custom.ld" \
  --output-dir build
