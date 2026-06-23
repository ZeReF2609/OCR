import re
from typing import List, Optional

import numpy as np
from PIL import Image

from app.models.schemas import DocumentoProcesado, Producto

try:
    import easyocr

    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False


_NUM = r"\d+[.,]\d*"
_TOTAL_PATTERNS = [
    re.compile(rf"(?:total|importe\s*total|monto\s*total)\s*:?\s*[S/$.\s]*({_NUM})", re.IGNORECASE),
    re.compile(rf"total\s*:?\s*s/?\.?\s*({_NUM})", re.IGNORECASE),
    re.compile(rf"total\s*[S/$]*\s*[']?\s*({_NUM})", re.IGNORECASE),
]


class OCRExtractor:
    """Extractor OCR usando EasyOCR para documentos (facturas/boletas)."""

    def __init__(self, lang: str = "es", use_gpu: bool = False):
        if not _EASYOCR_AVAILABLE:
            raise ImportError(
                "EasyOCR no está instalado. "
                "Ejecuta: pip install easyocr"
            )
        self.lang = [lang, "en"]
        self.use_gpu = use_gpu
        self.reader = None

    def _get_reader(self):
        if self.reader is None:
            self.reader = easyocr.Reader(
                self.lang, gpu=self.use_gpu, verbose=False
            )
        return self.reader

    def extract_text_from_image(self, image: Image.Image) -> str:
        reader = self._get_reader()
        img_array = np.array(image.convert("RGB"))
        result = reader.readtext(img_array)
        lines = []
        for bbox, text, confidence in result:
            if confidence > 0.3:
                lines.append(text)
        return "\n".join(lines)

    def extract_text_from_path(self, image_path: str) -> str:
        reader = self._get_reader()
        result = reader.readtext(image_path)
        lines = []
        for bbox, text, confidence in result:
            if confidence > 0.3:
                lines.append(text)
        return "\n".join(lines)

    def extract_document(self, image: Image.Image) -> DocumentoProcesado:
        texto = self.extract_text_from_image(image)
        doc = DocumentoProcesado(texto_crudo=texto)
        self._parse_documento(doc, texto)
        return doc

    def _parse_documento(
        self, doc: DocumentoProcesado, texto: str
    ) -> None:
        lines = [l.strip() for l in texto.split("\n") if l.strip()]

        doc.tipo_documento = self._detect_tipo(texto)
        doc.emisor = self._extract_field(lines, ["razon social", "empresa", "emisor", "proveedor"])
        doc.ruc = self._extract_ruc(texto)
        doc.fecha = self._extract_date(texto)
        doc.total_general = self._extract_total(texto)
        doc.metodo_pago = self._extract_payment_method(lines)
        doc.productos = self._extract_products(lines)

    def _detect_tipo(self, texto: str) -> str:
        t = texto.lower()
        if "boleta" in t and "electrónica" in t:
            return "Boleta Electrónica"
        if "factura" in t and "electrónica" in t:
            return "Factura Electrónica"
        if "boleta" in t:
            return "Boleta"
        if "factura" in t:
            return "Factura"
        return "Documento"

    def _extract_field(
        self, lines: List[str], keywords: List[str]
    ) -> Optional[str]:
        for line in lines:
            if re.search("|".join(keywords), line, re.IGNORECASE):
                parts = re.split(r"[:]\s*", line, maxsplit=1)
                if len(parts) > 1:
                    return parts[1].strip()
        return None

    def _extract_ruc(self, texto: str) -> Optional[str]:
        match = re.search(r"\b\d{11}\b", texto)
        return match.group(0) if match else None

    def _extract_date(self, texto: str) -> Optional[str]:
        for p in [r"\b\d{2}[/\.]\d{2}[/\.]\d{4}\b", r"\b\d{4}-\d{2}-\d{2}\b"]:
            match = re.search(p, texto)
            if match:
                return match.group(0)
        match = re.search(r"\b(\d{2})[,.](\d{2})['](\d{4})\b", texto)
        if match:
            return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
        return None

    def _extract_total(self, texto: str) -> Optional[float]:
        for pat in _TOTAL_PATTERNS:
            match = pat.search(texto)
            if match:
                val = self._parse_number(match.group(1))
                if val is not None:
                    return val
        return None

    def _extract_payment_method(self, lines: List[str]) -> Optional[str]:
        """Extrae método de pago: efectivo, bcp, débito o yape."""
        valid_methods = {"efectivo", "bcp", "débito", "debito", "yape"}
        
        for line in lines:
            line_lower = line.lower()
            # Buscar métodos válidos directamente
            for method in valid_methods:
                if method in line_lower:
                    # Normalizar: "débito" -> "débito", "debito" -> "débito"
                    if method in ("débito", "debito"):
                        return "BCP Débito"
                    return method.capitalize()
        return None

    def _extract_products(self, lines: List[str]) -> List[Producto]:
        productos = []

        num_info = [(i, self._parse_number(l)) for i, l in enumerate(lines)]
        skip_keywords = re.compile(
            r"(total|subtotal|igv|impuesto|ruc|fecha|empresa|razon\s*social|boleta|factura|electr.nica)",
            re.IGNORECASE,
        )
        header_keywords = re.compile(
            r"(cant|cantidad|descripci.n|producto|item|c.digo)",
            re.IGNORECASE,
        )

        price_indices = set()
        for i, p in num_info:
            if p is None or p >= 1_000_000:
                continue
            if skip_keywords.search(lines[i]):
                continue
            price_indices.add(i)

        total_idx = self._find_total_line(lines)

        seen_names = set()
        for i in sorted(price_indices):
            if total_idx is not None and i >= total_idx:
                break
            price = num_info[i][1]
            name = self._find_product_name(lines, i, seen_names, skip_keywords, header_keywords)
            if name and price is not None:
                productos.append(Producto(nombre=name, total=price))
                seen_names.add(name.lower())

        return productos

    def _find_total_line(self, lines: List[str]) -> Optional[int]:
        for i, l in enumerate(lines):
            if re.search(r"total", l, re.IGNORECASE) and self._parse_number(l) is not None:
                return i
        return None

    def _find_product_name(
        self, lines: List[str], price_idx: int, seen_names: set,
        skip_keywords, header_keywords,
    ) -> Optional[str]:
        candidates = []
        n = len(lines)
        for j in range(price_idx - 1, max(price_idx - 5, -1), -1):
            candidates.append(j)
        for j in range(price_idx + 1, min(price_idx + 5, n)):
            candidates.append(j)

        for j in candidates:
            candidate = lines[j]
            if self._parse_number(candidate) is not None:
                continue
            if skip_keywords.search(candidate):
                continue
            if header_keywords.search(candidate):
                continue
            cleaned = re.sub(r"^[\d\s.,/#\-]+", "", candidate).strip()
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if len(cleaned) > 2 and cleaned.lower() not in seen_names:
                return cleaned
        return None

    @staticmethod
    def _parse_number(text: str) -> Optional[float]:
        text = text.strip().replace(" ", "")
        text = text.replace("'", "").replace(",", ".")
        match = re.search(r"\d+\.?\d*", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None
