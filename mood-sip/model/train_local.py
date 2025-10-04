import os
from pprint import pprint

from focoos import ASSETS_DIR, ModelManager, RuntimeType
from focoos.infer.quantizer import OnnxQuantizer, QuantizationCfg
from PIL import Image
from focoos import InferModel

model_name = "fai-cls-n-coco"  # you can also take model from focoos hub with "hub://YOUR_MODEL_REF"

model = ModelManager.get(model_name)
pprint(model.model_info)

image_size = 96  # 96px input size

exported_model = model.export(
    runtime_type=RuntimeType.ONNX_CPU,  # optimized for edge or cpu
    image_size=image_size,
    dynamic_axes=False,  # quantization need static axes!
    simplify_onnx=True,  # simplify and optimize onnx model graph
    onnx_opset=18,
    out_dir=os.path.join("export/", "my_pretrained_model"),
)  # save to models dir

# benchmark onnx model
exported_model.benchmark(iterations=100)

# test onnx model
im = ASSETS_DIR / "federer.jpg"
result = exported_model.infer(im, annotate=True, threshold=0.65)
Image.fromarray(result.image)

quantization_cfg = QuantizationCfg(
    size=image_size,  # input size: must be same as exported model
    calibration_images_folder=str(
        "/home/ubuntu/focoos/datasets/coco/val2017"
    ),  # Calibration images folder: It is strongly recommended
    # to use the dataset validation split on which the model was trained.
    # Here, for example, we will use the assets folder.
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

# infer on cpu
quantized_model = InferModel(model_path, runtime_type=RuntimeType.ONNX_CPU)

res = quantized_model.infer(im, annotate=True)
Image.fromarray(res.image)
