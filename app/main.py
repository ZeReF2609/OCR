import io
import os
import time
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.classifier.api_client import CategoriaAPIClient
from app.classifier.categorizer import ProductCategorizer
from app.models.schemas import (
    Categoria,
    DocumentoProcesado,
    EntrenamientoRequest,
    OCRResponse,
    Producto,
)
from app.ocr.extractor import OCRExtractor
from app.ocr.processor import PDFProcessor

app = FastAPI(
    title="OCR Finanzas360",
    description="API de OCR para facturas/boletas con clasificación automática en categorías",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ocr_extractor: Optional[OCRExtractor] = None
pdf_processor: Optional[PDFProcessor] = None
categorizer: Optional[ProductCategorizer] = None
categorias_cache: List[Categoria] = []


@app.on_event("startup")
async def startup():
    global ocr_extractor, pdf_processor, categorizer, categorias_cache
    try:
        ocr_extractor = OCRExtractor(lang="es", use_gpu=False)
    except ImportError as e:
        print(f"WARNING: {e}")
        ocr_extractor = None
    pdf_processor = PDFProcessor(dpi=300)
    try:
        client = CategoriaAPIClient()
        categorias_cache = client.listar_categorias()
        categorizer = ProductCategorizer(
            categorias_cache, cache_dir="data"
        )
        print(f"Categorías cargadas: {len(categorias_cache)}")
    except Exception as e:
        print(f"WARNING: No se pudieron cargar categorías: {e}")


@app.post("/ocr", response_model=OCRResponse)
async def procesar_documento(
    file: UploadFile = File(...),
    categoria_ids: Optional[str] = Form(None),
):
    if ocr_extractor is None:
        raise HTTPException(
            status_code=500,
            detail="OCR no disponible. Verifica la instalación de EasyOCR.",
        )

    start = time.time()
    contenido = await file.read()

    if file.filename and file.filename.lower().endswith(".pdf"):
        images = pdf_processor.pdf_bytes_to_images(contenido)
        doc = DocumentoProcesado(texto_crudo="")
        for img in images:
            page_doc = ocr_extractor.extract_document(img)
            doc.texto_crudo += page_doc.texto_crudo + "\n"
            if not doc.emisor:
                doc.emisor = page_doc.emisor
            if not doc.ruc:
                doc.ruc = page_doc.ruc
            if not doc.fecha:
                doc.fecha = page_doc.fecha
            if not doc.total_general:
                doc.total_general = page_doc.total_general
            doc.productos.extend(page_doc.productos)
        doc.tipo_documento = doc.tipo_documento or "Documento PDF"
    else:
        image = _load_image(contenido)
        doc = ocr_extractor.extract_document(image)

    categorias_usadas = categorias_cache
    if categorizer:
        doc.productos = categorizer.classify_products(doc.productos)
        cats_in_use = set(
            p.categoria for p in doc.productos if p.categoria
        )
        categorias_usadas = [
            c
            for c in categorias_cache
            if c.name in cats_in_use
        ] or categorias_cache

    elapsed_ms = round((time.time() - start) * 1000, 2)
    return OCRResponse(
        documento=doc,
        categorias_usadas=categorias_usadas,
        tiempo_procesamiento_ms=elapsed_ms,
    )


@app.post("/entrenar")
async def entrenar_clasificador(req: EntrenamientoRequest):
    if categorizer is None:
        raise HTTPException(
            status_code=500,
            detail="Clasificador no disponible. Verifica las categorías.",
        )
    try:
        output = categorizer.fine_tune(
            pairs=[(p[0], p[1]) for p in req.pairs]
        )
        return {
            "mensaje": "Modelo entrenado correctamente",
            "pares_entrenados": len(req.pairs),
            "output_path": str(output),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/categorias", response_model=List[Categoria])
async def listar_categorias():
    return categorias_cache or []


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ocr_disponible": ocr_extractor is not None,
        "categorias_cargadas": len(categorias_cache),
    }


def _load_image(data: bytes):
    from PIL import Image
    return Image.open(io.BytesIO(data))
