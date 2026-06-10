import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance


def _cv2():
    import cv2
    return cv2

from backend.services.document_intelligence.types import PreprocessedPage


class ImagePreprocessor:
    """Preprocessing pipeline optimized for Indian business document scans."""

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}

    def preprocess_page(
        self,
        image_path: str,
        output_dir: str,
        page_number: int,
    ) -> PreprocessedPage:
        cv2 = _cv2()
        image = cv2.imread(image_path)
        if image is None:
            pil_image = Image.open(image_path).convert("RGB")
            image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        transforms: list[str] = []
        height, width = image.shape[:2]

        image, applied = self._auto_rotate(image)
        transforms.extend(applied)

        image, applied = self._deskew(image)
        transforms.extend(applied)

        image, applied = self._remove_shadows(image)
        transforms.extend(applied)

        image, applied = self._low_light_correction(image)
        transforms.extend(applied)

        image, applied = self._denoise(image)
        transforms.extend(applied)

        image, applied = self._enhance_contrast(image)
        transforms.extend(applied)

        image, applied = self._sharpen(image)
        transforms.extend(applied)

        image, applied = self._adaptive_threshold(image)
        transforms.extend(applied)

        os.makedirs(output_dir, exist_ok=True)
        output_path = str(Path(output_dir) / f"page_{page_number:04d}_processed.png")
        _cv2().imwrite(output_path, image)

        return PreprocessedPage(
            page_number=page_number,
            original_path=image_path,
            processed_path=output_path,
            width=image.shape[1],
            height=image.shape[0],
            transforms_applied=transforms,
        )

    def _auto_rotate(self, image: np.ndarray) -> tuple[np.ndarray, list[str]]:
        cv2 = _cv2()
        try:
            osd = pytesseract_osd(image)
            if osd and osd.get("rotate", 0) != 0:
                angle = osd["rotate"]
                rotated = self._rotate_image(image, angle)
                return rotated, [f"auto_rotation_{angle}"]
        except Exception:
            pass

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        coords = np.column_stack(np.where(gray < 200))
        if len(coords) < 100:
            return image, []

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) > 0.5:
            rotated = self._rotate_image(image, angle)
            return rotated, [f"orientation_correction_{angle:.1f}"]
        return image, []

    def _deskew(self, image: np.ndarray) -> tuple[np.ndarray, list[str]]:
        cv2 = _cv2()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 50:
            return image, []

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 0.3:
            return image, []

        rotated = self._rotate_image(image, angle)
        return rotated, [f"deskew_{angle:.2f}"]

    def _remove_shadows(self, image: np.ndarray) -> tuple[np.ndarray, list[str]]:
        cv2 = _cv2()
        if len(image.shape) == 2:
            rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            rgb = image.copy()

        lab = cv2.cvtColor(rgb, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)
        merged = cv2.merge((cl, a_channel, b_channel))
        result = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        return result, ["shadow_removal_clahe"]

    def _low_light_correction(self, image: np.ndarray) -> tuple[np.ndarray, list[str]]:
        cv2 = _cv2()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        mean_brightness = np.mean(gray)
        if mean_brightness >= 100:
            return image, []

        gamma = 1.5 if mean_brightness < 60 else 1.2
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
        corrected = cv2.LUT(image, table)
        return corrected, [f"low_light_gamma_{gamma}"]

    def _denoise(self, image: np.ndarray) -> tuple[np.ndarray, list[str]]:
        cv2 = _cv2()
        denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        return denoised, ["denoise_nlmeans"]

    def _enhance_contrast(self, image: np.ndarray) -> tuple[np.ndarray, list[str]]:
        cv2 = _cv2()
        pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Contrast(pil)
        enhanced = enhancer.enhance(1.3)
        result = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
        return result, ["contrast_enhancement"]

    def _sharpen(self, image: np.ndarray) -> tuple[np.ndarray, list[str]]:
        cv2 = _cv2()
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpened = cv2.filter2D(image, -1, kernel)
        return sharpened, ["sharpening"]

    def _adaptive_threshold(self, image: np.ndarray) -> tuple[np.ndarray, list[str]]:
        cv2 = _cv2()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        result = cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR)
        blended = cv2.addWeighted(image, 0.7, result, 0.3, 0)
        return blended, ["adaptive_threshold_blend"]

    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        cv2 = _cv2()
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        cos = abs(matrix[0, 0])
        sin = abs(matrix[0, 1])
        new_w = int((height * sin) + (width * cos))
        new_h = int((height * cos) + (width * sin))
        matrix[0, 2] += (new_w / 2) - center[0]
        matrix[1, 2] += (new_h / 2) - center[1]
        return cv2.warpAffine(
            image, matrix, (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )


def pytesseract_osd(image: np.ndarray) -> dict | None:
    try:
        import pytesseract
        cv2 = _cv2()
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        osd = pytesseract.image_to_osd(rgb, output_type=pytesseract.Output.DICT)
        return osd
    except Exception:
        return None
