import os
from pathlib import Path

from focoos import FocoosHUB, ModelManager, RuntimeType
from focoos.infer.quantizer import OnnxQuantizer, QuantizationCfg

CURR_DIR = Path(os.path.dirname(__file__))
MODEL_NAME = "my_model"


def main():
    # TODO: make them args
    model_ref = "fbe6e0ff46e742f7"
    api_key = os.environ.get("FOCOOS_API_KEY", None)
    image_size = 96
    # Calibration images: use validation set
    calibration_images_folder = CURR_DIR / "datasets/calibrate"
    out_dir = CURR_DIR / "out" / MODEL_NAME

    if api_key is None:
        raise ValueError("No API key provided for Focoos")

    # hub = FocoosHUB(api_key=api_key)
    model = ModelManager.get("fai-cls-n-coco")

    exported_model = model.export(
        runtime_type=RuntimeType.ONNX_CPU,
        image_size=image_size,
        dynamic_axes=False,
        simplify_onnx=True,  # simplify and optimize onnx model graph
        onnx_opset=18,
        out_dir=str(out_dir),
    )

    quantization_cfg = QuantizationCfg(
        size=image_size,  # input size: must be same as exported model
        calibration_images_folder=str(calibration_images_folder),
        format="QO",  # QO (QOperator): All the quantized operators have their own ONNX definitions, like QLinearConv, MatMulInteger etc.
        # QDQ (Quantize-DeQuantize): inserts DeQuantizeLinear(QuantizeLinear(tensor)) between the original operators to simulate the quantization and dequantization process.
        per_channel=False,  # Per-channel quantization: each channel has its own scale/zero-point → more accurate,
        # especially for convolutions, at the cost of extra memory and computation.
        normalize_images=True,  # normalize images during preprocessing: some models have normalization outside of model forward
    )

    quantizer = OnnxQuantizer(
        input_model_path=exported_model.model_path, cfg=quantization_cfg
    )
    model_path = quantizer.quantize(
        benchmark=True  # benchmark bot fp32 and int8 models
    )


if __name__ == "__main__":
    main()
