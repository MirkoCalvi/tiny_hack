#!/usr/bin/env zsh

export BASE_DIR=$PWD
export TMP_DIR=/tmp/groupotto
export SHAPE=1,3,96,96
export FQBN="arduino:mbed_nicla:nicla_vision"
export OUT_DIR="./dist"
export PIPELINE_LOG="$BASE_DIR/pipeline.log"

log_message() {
    local stage="$1"
    local level="$2"
    local message="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$stage] [$level] $message" | tee -a "$PIPELINE_LOG"
}
