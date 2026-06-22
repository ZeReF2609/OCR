import os
import tempfile
from pathlib import Path
from typing import List, Optional

from pdf2image import convert_from_path
from PIL import Image


class PDFProcessor:
    """Convierte PDFs a imágenes para procesamiento OCR."""

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
        return convert_from_path(pdf_path, dpi=self.dpi)

    def pdf_bytes_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            return convert_from_path(tmp_path, dpi=self.dpi)
        finally:
            os.unlink(tmp_path)

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        gray = image.convert("L")
        return gray
