#! /bin/bash

set -e

ORIG_DIR="$(pwd)"

# Hardcoded serial ports
PORT_1="/dev/cu.usbmodem11301"
PORT_2="/dev/tty.usbmodem11401"

# Function to show usage
show_usage() {
    echo "Usage: $0 [1|2]"
    echo "  1 - Use $PORT_1"
    echo "  2 - Use $PORT_2"
    exit 1
}

# Parse command line argument
if [ $# -eq 0 ]; then
    echo "Error: Please specify which port to use (1 or 2)"
    show_usage
fi

PORT_SELECTION=$1

case $PORT_SELECTION in
    1)
        ARDUINO_PORT=$PORT_1
        ;;
    2)
        ARDUINO_PORT=$PORT_2
        ;;
    *)
        echo "Error: Invalid port selection '$PORT_SELECTION'"
        show_usage
        ;;
esac

echo "Selected port $PORT_SELECTION: $ARDUINO_PORT"

cd ~/Developer/misc/Z-Ant

git checkout feature
git pull

docker build -t myimage .devcontainer

docker run -it \
    -v "$(pwd):/workspace" \
    -v "$HOME/Arduino:/home/user/Arduino" \
    myimage \
    bash -c "
        cd /workspace &&
        zig build lib-gen \
            -Dmodel=\"cinecla_quant\" \
            -Dxip=true \
            -Ddo_export \
            -Ddynamic \
            -Dfuse \
            -Denable_user_tests &&
        zig build lib-test \
            -Dmodel=\"cinecla_quant\" \
            -Dxip=true \
            -Ddo_export \
            -Ddynamic \
            -Denable_user_tests &&
        zig build lib \
            -Dmodel=\"cinecla_quant\" \
            -Dtarget=thumb-freestanding \
            -Dcpu=cortex_m7 \
            -Dxip=true \
            -freference-trace \
            -Doptimize=ReleaseFast &&
        cp zig-out/cinecla_quant/libzant.a /home/user/Arduino/libraries/ZantLib/src/cortex-m7/libzant.a &&
        echo 'Library built and copied to ~/Arduino/libraries/ZantLib/src/cortex-m7/libzant.a'
    "

cd "$ORIG_DIR"
cd tiny_hack/

arduino-cli compile \
--fqbn "arduino:mbed_nicla:nicla_vision" \
--export-binaries \
--libraries ~/Arduino/libraries \
--build-property "compiler.c.elf.extra_flags=-Wl,-T$PWD/custom.ld"

ls -lash

./flash_nicla_xip.sh

cd "$ORIG_DIR"

echo "PRESS BUTTON ON NICLA NOW"

sleep 6

# screen /dev/tty.usbmodem11301 115200
uv run tv.py --device-id $PORT_SELECTION --serial-port "$ARDUINO_PORT"
