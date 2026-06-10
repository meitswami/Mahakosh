import hashlib
import os
from pathlib import Path

from PIL import Image


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}


class DocumentLoader:
    """Loads documents and rasterizes pages for OCR processing."""

    def __init__(self, output_dir: str, dpi: int = 300):
        self.output_dir = output_dir
        self.dpi = dpi
        os.makedirs(output_dir, exist_ok=True)

    def load_pages(self, file_path: str) -> list[str]:
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix in SUPPORTED_IMAGE_EXTENSIONS:
            return [self._prepare_image(str(path))]
        if suffix in SUPPORTED_PDF_EXTENSIONS:
            return self._load_pdf(str(path))
        raise ValueError(f"Unsupported file format: {suffix}")

    def get_page_count(self, file_path: str) -> int:
        return len(self.load_pages(file_path))

    def compute_checksum(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _prepare_image(self, image_path: str) -> str:
        dest = str(Path(self.output_dir) / f"page_0001{Path(image_path).suffix}")
        if image_path != dest:
            with Image.open(image_path) as img:
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                img.save(dest, quality=95)
        return dest

    def _load_pdf(self, pdf_path: str) -> list[str]:
        page_paths: list[str] = []

        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, dpi=self.dpi)
            for idx, image in enumerate(images, start=1):
                dest = str(Path(self.output_dir) / f"page_{idx:04d}.png")
                image.save(dest, "PNG")
                page_paths.append(dest)
            if page_paths:
                return page_paths
        except Exception:
            pass

        import fitz
        doc = fitz.open(pdf_path)
        for idx in range(len(doc)):
            page = doc[idx]
            pix = page.get_pixmap(dpi=self.dpi)
            dest = str(Path(self.output_dir) / f"page_{idx + 1:04d}.png")
            pix.save(dest)
            page_paths.append(dest)
        doc.close()
        return page_paths
