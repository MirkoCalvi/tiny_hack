from focoos import ModelManager, FocoosHUB
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import random
import time


class ImagePreprocessor:
    """Mirror the gesture training preprocessing (resize, denoise, normalize)."""

    def __init__(self, target_size=(96, 96)):
        self.target_size = target_size

    def augment_image(self, image: Image.Image) -> Image.Image:
        if random.random() > 0.5:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)

        angle = random.uniform(-15, 15)
        image = image.rotate(angle, fillcolor="white")

        image = ImageEnhance.Brightness(image).enhance(random.uniform(0.8, 1.2))
        image = ImageEnhance.Contrast(image).enhance(random.uniform(0.8, 1.2))
        image = ImageEnhance.Sharpness(image).enhance(random.uniform(0.5, 1.5))

        if random.random() > 0.5:
            w, h = image.size
            crop_size = random.uniform(0.8, 0.95)
            new_w, new_h = int(w * crop_size), int(h * crop_size)
            left = random.randint(0, w - new_w)
            top = random.randint(0, h - new_h)
            image = image.crop((left, top, left + new_w, top + new_h)).resize((w, h))

        if random.random() > 0.8:
            image = image.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))

        return image

    def resize_with_padding(self, image: Image.Image) -> Image.Image:
        w, h = image.size
        scale = min(self.target_size[0] / w, self.target_size[1] / h)
        new_w, new_h = int(w * scale), int(h * scale)
        image = image.resize((new_w, new_h), Image.LANCZOS)
        padded = Image.new("RGB", self.target_size, (255, 255, 255))
        paste_x = (self.target_size[0] - new_w) // 2
        paste_y = (self.target_size[1] - new_h) // 2
        padded.paste(image, (paste_x, paste_y))
        return padded

    def denoise(self, image: Image.Image) -> Image.Image:
        return image.filter(ImageFilter.MedianFilter(size=3))

    def normalize_image(self, image: Image.Image) -> Image.Image:
        arr = np.array(image).astype(np.float32) / 255.0
        return Image.fromarray((arr * 255).astype(np.uint8))

    def preprocess(self, image: Image.Image, augment: bool = False) -> Image.Image:
        if augment:
            image = self.augment_image(image)
        image = self.resize_with_padding(image)
        image = self.denoise(image)
        image = self.normalize_image(image)
        return image


hub = FocoosHUB(api_key="c6c9d304a1e64419b042d598e7871af1")
model = ModelManager.get("hub://24b53ce53f284eb4", hub=hub)
preprocessor = ImagePreprocessor(target_size=(96, 96))

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 96)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 96)

if not cap.isOpened():
    raise SystemExit("Unable to open camera 0")

use_bw_mode = True
use_augmentation = False
previous_mask = None

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Camera read failed; exiting.")
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)

        width, height = pil_image.size
        crop_factor = 0.6
        left = int(width * (1 - crop_factor) / 2)
        top = int(height * (1 - crop_factor) / 2)
        right = int(width * (1 + crop_factor) / 2)
        bottom = int(height * (1 + crop_factor) / 2)
        pil_image = pil_image.crop((left, top, right, bottom)).resize((width, height))

        if use_bw_mode:
            gray_image = pil_image.convert("L")

            def quantize_to_5_shades(x):
                if x < 32:
                    return 0
                if x < 96:
                    return 64
                if x < 160:
                    return 128
                if x < 224:
                    return 192
                return 255

            quantized = gray_image.point(quantize_to_5_shades)
            quantized = quantized.point(lambda v: 255 - v)
            pil_image = quantized.convert("RGB")

        processed_image = preprocessor.preprocess(pil_image, augment=use_augmentation)
        processed_frame_bgr = cv2.cvtColor(np.array(processed_image), cv2.COLOR_RGB2BGR)

        gray_for_mask = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(gray_for_mask)
        blurred = cv2.GaussianBlur(enhanced_gray, (5, 5), 0)

        _, mask_otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        adaptive = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 2
        )
        edges = cv2.Canny(blurred, 25, 75)
        mask = cv2.bitwise_or(mask_otsu, adaptive)
        mask = cv2.bitwise_or(mask, edges)

        kernel_close = np.ones((5, 5), np.uint8)
        kernel_open = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open, iterations=1)
        mask = cv2.GaussianBlur(mask, (3, 3), 0)
        _, mask = cv2.threshold(mask, 80, 255, cv2.THRESH_BINARY)
        mask = mask.astype(np.uint8)

        mask = cv2.resize(
            mask,
            (processed_frame_bgr.shape[1], processed_frame_bgr.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        )

        min_area = int(mask.size * 0.01)
        if np.count_nonzero(mask) < min_area and previous_mask is not None and previous_mask.shape == mask.shape:
            mask = previous_mask.copy()

        if previous_mask is not None and previous_mask.shape == mask.shape:
            blended = cv2.addWeighted(
                mask.astype(np.float32), 0.7, previous_mask.astype(np.float32), 0.3, 0
            )
            mask = blended.astype(np.uint8)

        previous_mask = mask.copy()

        processed_frame_bgr = cv2.bitwise_and(processed_frame_bgr, processed_frame_bgr, mask=mask)
        processed_image = Image.fromarray(cv2.cvtColor(processed_frame_bgr, cv2.COLOR_BGR2RGB))

        temp_path = "temp_frame.png"
        processed_image.save(temp_path)

        annotated_frame = processed_frame_bgr.copy()
        try:
            detections = model.infer(temp_path, threshold=0.5, annotate=False)
            if getattr(detections, "image", None) is not None:
                annotated_frame = cv2.cvtColor(detections.image, cv2.COLOR_RGB2BGR)
        except Exception:
            pass

        cv2.imshow("Focoos Model Test - Webcam", annotated_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("s"):
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"webcam_capture_{timestamp}.png"
            cv2.imwrite(filename, annotated_frame)
        if key == ord("b"):
            use_bw_mode = not use_bw_mode
            print(f"5-shade grayscale {'ENABLED' if use_bw_mode else 'DISABLED'}")
        if key == ord("a"):
            use_augmentation = not use_augmentation
            print(f"Augmentation {'ENABLED' if use_augmentation else 'DISABLED'}")

finally:
    cap.release()
    cv2.destroyAllWindows()
