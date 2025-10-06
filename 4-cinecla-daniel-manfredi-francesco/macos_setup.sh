#! /bin/bash

# install homebrew if not available
which brew || bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# install brew packages
/opt/homebrew/bin/brew install arduino-cli zig@0.14 dfu-util uv

/opt/homebrew/bin/arduino-cli core install arduino:mbed_nicla

/opt/homebrew/bin/uv sync

/opt/homebrew/bin/uv run main.py

