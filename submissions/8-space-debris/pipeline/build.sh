#!/usr/bin/env zsh

source ./pipeline/vars.sh

log_message "BUILD" "INFO" "Starting build pipeline"

log_message "BUILD" "INFO" "Changing to Z-Ant directory"
cd $TMP_DIR/Z-Ant

log_message "BUILD" "INFO" "Building library with Zig"
if zig build lib -Dmodel="gruppotto" -Doptimize=ReleaseSmall -Dtarget=thumb-freestanding -Dcpu=cortex_m7 >> "$PIPELINE_LOG" 2>&1; then
    log_message "BUILD" "INFO" "Zig build completed successfully"
else
    log_message "BUILD" "ERROR" "Zig build failed"
    exit 1
fi

log_message "BUILD" "INFO" "Copying library to project"
if cp $TMP_DIR/Z-Ant/zig-out/gruppotto/libzant.a $BASE_DIR/src/lib/ZantLib/src/cortex-m7; then
    log_message "BUILD" "INFO" "Library copied successfully"
else
    log_message "BUILD" "ERROR" "Failed to copy library"
    exit 1
fi

log_message "BUILD" "INFO" "Build pipeline completed"

