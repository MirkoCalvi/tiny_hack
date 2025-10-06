FQBN ?= arduino:mbed_nicla:nicla_vision
SKETCH_DIR ?= src/MoodSip
SKETCH ?= MoodSip.ino
BUILD_DIR ?= build
ARDUINO_CLI ?= arduino-cli
PORT ?= # empty
BAUD ?= 115200
LIB_DIR ?= ~/programming/Arduino/libraries

.PHONY: compile upload launch

compile:
	@echo "=== Compiling $(SKETCH) for $(FQBN) ==="
	@arduino-cli compile --fqbn $(FQBN) --export-binaries --libraries $(LIB_DIR) --build-property "compiler.c.elf.extra_flags=-Wl, -T$(SKETCH_DIR)/custom.ld" --build-path $(SKETCH_DIR)/$(BUILD_DIR) $(SKETCH_DIR)/$(SKETCH)

upload:
	@SKETCH_DIR=$(SKETCH_DIR) $(SKETCH_DIR)/flash_nicla_xip.sh

launch:
	compile
	upload
