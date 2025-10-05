#!/usr/bin/env zsh

source ./pipeline/vars.sh

log_message "CLEAN" "INFO" "Starting cleanup pipeline"

if [ -d "$TMP_DIR" ]; then
    log_message "CLEAN" "INFO" "Removing temporary directory"
    rm -rf $TMP_DIR >> "$PIPELINE_LOG" 2>&1
    log_message "CLEAN" "INFO" "Temporary directory removed"
else
    log_message "CLEAN" "INFO" "Temporary directory not found, skipping"
fi

if [ -d "$BASE_DIR/src/lib/build" ]; then
    log_message "CLEAN" "INFO" "Removing build directory"
    rm -rf $BASE_DIR/src/lib/build >> "$PIPELINE_LOG" 2>&1
    log_message "CLEAN" "INFO" "Build directory removed"
else
    log_message "CLEAN" "INFO" "Build directory not found, skipping"
fi

if [ -d "$BASE_DIR/dist" ]; then
    log_message "CLEAN" "INFO" "Removing dist directory"
    rm -rf $BASE_DIR/dist >> "$PIPELINE_LOG" 2>&1
    log_message "CLEAN" "INFO" "Dist directory removed"
else
    log_message "CLEAN" "INFO" "Dist directory not found, skipping"
fi

if [ -f "$BASE_DIR/src/lib/ZantLib/src/cortex-m7/libzant.a" ]; then
    log_message "CLEAN" "INFO" "Removing library archive"
    rm -f $BASE_DIR/src/lib/ZantLib/src/cortex-m7/libzant.a >> "$PIPELINE_LOG" 2>&1
    log_message "CLEAN" "INFO" "Library archive removed"
else
    log_message "CLEAN" "INFO" "Library archive not found, skipping"
fi

log_message "CLEAN" "INFO" "Cleanup pipeline completed"
