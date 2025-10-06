#!/usr/bin/env zsh

source ./pipeline/vars.sh

cd $BASE_DIR/src/backend
uv run backend.py
