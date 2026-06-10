import time
from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from PIL import Image

from backend.services.document_intelligence.types import BoundingBox, OCREngineOutput, OCRPageOutput, OCRToken


class BaseOCREngine(ABC):
    """Pluggable OCR engine interface for future engines (EasyOCR, Tesseract, Azure, etc.)."""

    name: str = "base"
    supported_languages: list[str] = []

    @abstractmethod
    def extract(self, image_paths: list[str], language: str = "en") -> OCREngineOutput:
        pass

    def is_available(self) -> bool:
        return True


class PaddleOCREngine(BaseOCREngine):
    name = "paddleocr"
    supported_languages = ["en", "hi", "en+hi"]

    def __init__(self) -> None:
        self._ocr = None

    def _get_engine(self, language: str):
        if self._ocr is None:
            from paddleocr import PaddleOCR

            lang = "en" if language in ("en", "en+hi") else language.split("+")[0]
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
                show_log=False,
                use_gpu=False,
            )
        return self._ocr

    def extract(self, image_paths: list[str], language: str = "en+hi") -> OCREngineOutput:
        start = time.perf_counter()
        ocr = self._get_engine(language)
        pages: list[OCRPageOutput] = []

        for idx, path in enumerate(image_paths, start=1):
            with Image.open(path) as img:
                width, height = img.size

            result = ocr.ocr(path, cls=True)
            tokens: list[OCRToken] = []
            lines: list[str] = []

            if result and result[0]:
                for line_id, line in enumerate(result[0]):
                    if not line or len(line) < 2:
                        continue
                    bbox_points, (text, conf) = line[0], line[1]
                    xs = [p[0] for p in bbox_points]
                    ys = [p[1] for p in bbox_points]
                    bbox = BoundingBox(min(xs), min(ys), max(xs), max(ys))
                    tokens.append(OCRToken(text=text, confidence=float(conf), bbox=bbox, line_id=line_id))
                    lines.append(text)

            pages.append(OCRPageOutput(
                page_number=idx,
                width=width,
                height=height,
                tokens=tokens,
                full_text="\n".join(lines),
                metadata={"engine": self.name, "language": language},
            ))

        elapsed = int((time.perf_counter() - start) * 1000)
        return OCREngineOutput(engine_name=self.name, pages=pages, processing_time_ms=elapsed)


class SuryaOCREngine(BaseOCREngine):
    name = "surya"
    supported_languages = ["en", "hi", "en+hi"]

    def __init__(self) -> None:
        self._det_predictor = None
        self._rec_predictor = None

    def _load_models(self) -> None:
        if self._det_predictor is None:
            from surya.detection import DetectionPredictor
            from surya.recognition import RecognitionPredictor

            self._det_predictor = DetectionPredictor()
            self._rec_predictor = RecognitionPredictor()

    def extract(self, image_paths: list[str], language: str = "en+hi") -> OCREngineOutput:
        start = time.perf_counter()
        self._load_models()

        from surya.foundation import FoundationPredictor
        from surya.recognition import RecognitionPredictor
        from surya.detection import DetectionPredictor

        images = [Image.open(p).convert("RGB") for p in image_paths]
        langs = [["en", "hi"]] * len(images) if language == "en+hi" else [[language]] * len(images)

        det_predictor = DetectionPredictor()
        foundation_predictor = FoundationPredictor()
        rec_predictor = RecognitionPredictor(foundation_predictor)

        det_results = det_predictor(images)
        rec_results = rec_predictor(images, det_results, langs)

        pages: list[OCRPageOutput] = []
        for idx, (image, rec_result) in enumerate(zip(images, rec_results), start=1):
            width, height = image.size
            tokens: list[OCRToken] = []
            lines: list[str] = []

            for line_id, line in enumerate(rec_result.text_lines):
                text = line.text
                conf = float(line.confidence) if hasattr(line, "confidence") else 0.85
                bbox_obj = line.bbox if hasattr(line, "bbox") else [0, 0, width, height]
                if hasattr(bbox_obj, "polygon"):
                    xs = [p[0] for p in bbox_obj.polygon]
                    ys = [p[1] for p in bbox_obj.polygon]
                elif isinstance(bbox_obj, (list, tuple)) and len(bbox_obj) >= 4:
                    xs = [bbox_obj[0], bbox_obj[2]]
                    ys = [bbox_obj[1], bbox_obj[3]]
                else:
                    xs, ys = [0, width], [0, height]

                bbox = BoundingBox(min(xs), min(ys), max(xs), max(ys))
                tokens.append(OCRToken(text=text, confidence=conf, bbox=bbox, line_id=line_id))
                lines.append(text)

            pages.append(OCRPageOutput(
                page_number=idx,
                width=width,
                height=height,
                tokens=tokens,
                full_text="\n".join(lines),
                metadata={"engine": self.name, "language": language},
            ))

        for img in images:
            img.close()

        elapsed = int((time.perf_counter() - start) * 1000)
        return OCREngineOutput(engine_name=self.name, pages=pages, processing_time_ms=elapsed)


class OCREngineRegistry:
    """Registry for pluggable OCR engines."""

    def __init__(self) -> None:
        self._engines: dict[str, BaseOCREngine] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(PaddleOCREngine())
        self.register(SuryaOCREngine())

    def register(self, engine: BaseOCREngine) -> None:
        self._engines[engine.name] = engine

    def get(self, name: str) -> BaseOCREngine:
        if name not in self._engines:
            raise KeyError(f"OCR engine '{name}' not registered")
        return self._engines[name]

    def list_engines(self) -> list[str]:
        return list(self._engines.keys())

    def extract_parallel(
        self,
        engine_names: list[str],
        image_paths: list[str],
        language: str = "en+hi",
    ) -> dict[str, OCREngineOutput]:
        results: dict[str, OCREngineOutput] = {}
        for name in engine_names:
            engine = self.get(name)
            results[name] = engine.extract(image_paths, language)
        return results


ocr_engine_registry = OCREngineRegistry()
