from pydantic import BaseModel, Field
from typing import List, Optional


class Categoria(BaseModel):
    idCategoria: str
    name: str
    icon: str
    color: str
    esPersonalizada: bool
    estado: int


class Producto(BaseModel):
    nombre: str
    cantidad: Optional[float] = None
    precio_unitario: Optional[float] = None
    total: Optional[float] = None
    categoria: Optional[str] = None
    categoria_id: Optional[str] = None
    confianza_categoria: Optional[float] = None


class DocumentoProcesado(BaseModel):
    tipo_documento: Optional[str] = None
    emisor: Optional[str] = None
    ruc: Optional[str] = None
    fecha: Optional[str] = None
    total_general: Optional[float] = None
    productos: List[Producto] = []
    texto_crudo: str = ""


class OCRRequest(BaseModel):
    categoria_ids: Optional[List[str]] = None


class OCRResponse(BaseModel):
    documento: DocumentoProcesado
    categorias_usadas: List[Categoria]
    tiempo_procesamiento_ms: float


class EntrenamientoRequest(BaseModel):
    pairs: List[List[str]] = Field(
        ...,
        description="Lista de [nombre_producto, nombre_categoria]",
        example=[["Pan integral", "Comida"], ["Pasaje bus", "Transporte"]],
    )
