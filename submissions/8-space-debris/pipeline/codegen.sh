#!/usr/bin/env zsh

source ./pipeline/vars.sh

log_message "GEN" "INFO" "Starting code generation pipeline"

log_message "GEN" "INFO" "Creating temporary directory"
mkdir -p $TMP_DIR >> "$PIPELINE_LOG" 2>&1

log_message "GEN" "INFO" "Cloning Z-Ant repository"
if git clone --depth 1 https://github.com/ZantFoundation/Z-Ant.git $TMP_DIR/Z-Ant >> "$PIPELINE_LOG" 2>&1; then
    log_message "GEN" "INFO" "Repository cloned successfully"
else
    log_message "GEN" "ERROR" "Failed to clone repository"
    exit 1
fi

log_message "GEN" "INFO" "Setting up model directory"
mkdir -p $TMP_DIR/Z-Ant/datasets/models/gruppotto >> "$PIPELINE_LOG" 2>&1
cp $BASE_DIR/src/model.onnx $TMP_DIR/Z-Ant/datasets/models/gruppotto/gruppotto.onnx

cd $TMP_DIR/Z-Ant

log_message "GEN" "INFO" "Initializing Python environment"
uv init >> "$PIPELINE_LOG" 2>&1
uv venv >> "$PIPELINE_LOG" 2>&1
source $TMP_DIR/Z-Ant/.venv/bin/activate

log_message "GEN" "INFO" "Installing Python dependencies"
if uv add onnx onnxsim onnxruntime >> "$PIPELINE_LOG" 2>&1; then
    log_message "GEN" "INFO" "Dependencies installed successfully"
else
    log_message "GEN" "ERROR" "Failed to install dependencies"
    exit 1
fi

log_message "GEN" "INFO" "Running input setter"
if ./zant input_setter --model gruppotto --shape $SHAPE >> "$PIPELINE_LOG" 2>&1; then
    log_message "GEN" "INFO" "Input setter completed"
else
    log_message "GEN" "ERROR" "Input setter failed"
    exit 1
fi

log_message "GEN" "INFO" "Generating user tests"
if ./zant user_tests_gen --model gruppotto >> "$PIPELINE_LOG" 2>&1; then
    log_message "GEN" "INFO" "User tests generated"
else
    log_message "GEN" "ERROR" "User tests generation failed"
    exit 1
fi

log_message "GEN" "INFO" "Building library generation"
if zig build lib-gen -Dmodel="gruppotto" -Denable_user_tests -Dxip=true -Ddo_export >> "$PIPELINE_LOG" 2>&1; then
    log_message "GEN" "INFO" "Library generation completed"
else
    log_message "GEN" "ERROR" "Library generation failed"
    exit 1
fi

log_message "GEN" "INFO" "Running library tests"
if zig build lib-test -Dmodel="gruppotto" -Denable_user_tests -Ddo_export >> "$PIPELINE_LOG" 2>&1; then
    log_message "GEN" "INFO" "Library tests completed successfully"
else
    log_message "GEN" "WARN" "Library tests failed but continuing"
fi

log_message "GEN" "INFO" "Code generation pipeline completed"
