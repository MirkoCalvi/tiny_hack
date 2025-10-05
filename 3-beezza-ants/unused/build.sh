#! /bin/bash

# ./docker.sh

cd external/Z-Ant/examples/tiny_hack/

arduino-cli compile \
--fqbn "arduino:mbed_nicla:nicla_vision" \
--export-binaries \
--libraries ~/Arduino/libraries \
--build-property "compiler.c.elf.extra_flags=-Wl,-T$PWD/custom.ld"

ls -lash

./flash_nicla_xip.sh

cd ../..
