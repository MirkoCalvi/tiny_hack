#!/usr/bin/env zsh

source ./pipeline/vars.sh

set -e

log_message "FLASH" "INFO" "Starting flash pipeline"

log_message "FLASH" "INFO" "Changing to library directory"
cd $BASE_DIR/src/lib

log_message "FLASH" "INFO" "Copying ZantLib to Arduino libraries"
cp -r ZantLib $HOME/Arduino/libraries

log_message "FLASH" "INFO" "Compiling with Arduino CLI"
if arduino-cli compile \
  --fqbn "$FQBN" \
  --export-binaries \
  --libraries $HOME/Arduino/libraries \
  --build-property "compiler.c.elf.extra_flags=-Wl,-T$PWD/custom.ld" >> "$PIPELINE_LOG" 2>&1; then
    log_message "FLASH" "INFO" "Arduino compilation completed"
else
    log_message "FLASH" "ERROR" "Arduino compilation failed"
    exit 1
fi

cd $BASE_DIR
mkdir -p $OUT_DIR

# Configuration
ARD="$HOME/.arduino15/packages/arduino/tools/arm-none-eabi-gcc/7-2017q4/bin"
READELF="$ARD/arm-none-eabi-readelf"
OBJCOPY="$ARD/arm-none-eabi-objcopy"
ELF="$BASE_DIR/src/lib/build/arduino.mbed_nicla.nicla_vision/lib.ino.elf"

log_message "FLASH" "INFO" "Nicla Vision XIP Flashing Script"

# Check if ELF exists
if [ ! -f "$ELF" ]; then
    log_message "FLASH" "ERROR" "ELF file not found at $ELF"
    log_message "FLASH" "ERROR" "Make sure you've compiled with Arduino CLI first"
    exit 1
fi

# Check if tools exist
if [ ! -f "$OBJCOPY" ]; then
    log_message "FLASH" "ERROR" "objcopy not found at $OBJCOPY"
    log_message "FLASH" "ERROR" "Check your Arduino installation"
    exit 1
fi

log_message "FLASH" "INFO" "Inspecting ELF sections..."
"$READELF" -S "$ELF" | grep -E "\.flash_weights|\.text|Name" >> "$PIPELINE_LOG" 2>&1 || true

log_message "FLASH" "INFO" "Creating internal firmware binary (without weights)..."
if "$OBJCOPY" -O binary -R .flash_weights "$ELF" $OUT_DIR/nicla_internal.bin >> "$PIPELINE_LOG" 2>&1; then
    log_message "FLASH" "INFO" "Internal firmware binary created"
else
    log_message "FLASH" "ERROR" "Failed to create internal firmware binary"
    exit 1
fi

log_message "FLASH" "INFO" "Creating weights binary..."
if "$OBJCOPY" -O binary -j .flash_weights "$ELF" $OUT_DIR/nicla_weights.bin >> "$PIPELINE_LOG" 2>&1; then
    log_message "FLASH" "INFO" "Weights binary created"
else
    log_message "FLASH" "ERROR" "Failed to create weights binary"
    exit 1
fi

log_message "FLASH" "INFO" "File sizes:"
ls -lh $OUT_DIR/nicla_*.bin | tee -a "$PIPELINE_LOG"

log_message "FLASH" "INFO" "Checking DFU devices..."
sudo dfu-util -l >> "$PIPELINE_LOG" 2>&1

echo "Please put Nicla Vision in DFU mode (double-tap RESET)"
echo "Press Enter when ready..."
read

log_message "FLASH" "INFO" "Flashing internal firmware..."
if sudo dfu-util -a 0 -s 0x08040000:leave -D $OUT_DIR/nicla_internal.bin >> "$PIPELINE_LOG" 2>&1; then
    log_message "FLASH" "INFO" "Internal firmware flashed successfully"
else
    log_message "FLASH" "ERROR" "Failed to flash internal firmware"
    exit 1
fi

echo "Put Nicla Vision in DFU mode again (double-tap RESET)"
echo "Press Enter when ready..."
read 

log_message "FLASH" "INFO" "Flashing weights to external flash..."
if sudo dfu-util -a 1 -s 0x90000000:leave -D $OUT_DIR/nicla_weights.bin >> "$PIPELINE_LOG" 2>&1; then
    log_message "FLASH" "INFO" "Weights flashed successfully"
else
    log_message "FLASH" "ERROR" "Failed to flash weights"
    exit 1
fi

log_message "FLASH" "INFO" "Flashing complete! Your device should now boot with XIP weights."
