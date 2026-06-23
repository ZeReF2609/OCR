import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from pdf2image import convert_from_path
from PIL import Image


class PDFProcessor:
    """Convierte PDFs a imágenes para procesamiento OCR."""

    POPPLER_PATH = os.getenv("POPPLER_PATH")

    def __init__(self, dpi: int = 300, poppler_path: Optional[str] = None):
        self.dpi = dpi
        self.poppler_path = poppler_path or self.POPPLER_PATH

    def _ensure_poppler(self) -> Optional[str]:
        if self.poppler_path and os.path.exists(self.poppler_path):
            return self.poppler_path
        if shutil.which("pdfinfo"):
            return None
        raise EnvironmentError(
            "Poppler no está disponible. Instala Poppler y configura POPPLER_PATH en el .env "
            "o agrega la ruta de pdfinfo al PATH del sistema."
        )

    def pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
        poppler_path = self._ensure_poppler()
        return convert_from_path(
            pdf_path, dpi=self.dpi, poppler_path=poppler_path
        )

    def pdf_bytes_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            poppler_path = self._ensure_poppler()
            return convert_from_path(
                tmp_path, dpi=self.dpi, poppler_path=poppler_path
            )
        finally:
            os.unlink(tmp_path)

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        gray = image.convert("L")
        return gray
