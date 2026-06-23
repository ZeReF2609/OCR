# OCR Finanzas360

API de OCR para facturas/boletas con clasificación automática de productos en categorías financieras.

## Arquitectura

```
Imagen/PDF → EasyOCR → Extracción de texto → Parseo de productos → Embeddings → Clasificación por categoría
```

- **OCR**: [EasyOCR](https://github.com/JaidedAI/EasyOCR) (soporta español)
- **Clasificación**: [sentence-transformers](https://www.sbert.net/) (`paraphrase-multilingual-MiniLM-L12-v2`) + cosine similarity
- **Fine-tuning**: LogisticRegression sobre embeddings (aprendizaje supervisado)
- **API**: FastAPI

## Instalación

```bash
pip install -r requirements.txt
```

> **Nota**: En la primera ejecución se descargan automáticamente los modelos de EasyOCR (~15MB) y sentence-transformers (~470MB).

## Uso

```bash
python run.py
```

Servidor en `http://127.0.0.1:8000`

### Endpoints

| Método | Path | Descripción | Parámetros |
|--------|------|-------------|------------|
| `POST` | `/ocr` | Procesa una imagen o PDF y clasifica productos | `file` (form file, requerido), `categoria_ids` (form string, opcional) |
| `POST` | `/entrenar` | Fine-tuning supervisado del clasificador | JSON body `pairs` (lista de pares [producto, categoría], requerido) |
| `GET` | `/categorias` | Lista categorías disponibles | Ninguno |
| `GET` | `/health` | Estado del servicio | Ninguno |

### Endpoint `/ocr`

- Método: `POST`
- Content-Type: `multipart/form-data`
- Parámetros:
  - `file`: archivo de imagen (`jpg`, `png`, etc.) o PDF (`.pdf`). Requerido.
  - `categoria_ids`: cadena opcional separada por comas con IDs de categoría a filtrar (por ejemplo `"cat1,cat2"`).

Ejemplo de petición:

```bash
curl -X POST -F "file=@factura.jpg" http://127.0.0.1:8000/ocr
```

Ejemplo de respuesta:

```json
{
  "documento": {
    "tipo_documento": "Boleta Electrónica",
    "emisor": "Mi Tienda SAC",
    "ruc": "12345678901",
    "fecha": "15/06/2026",
    "total_general": 150.00,
    "productos": [
      {
        "nombre": "Arroz x kg",
        "cantidad": null,
        "precio_unitario": null,
        "total": 4.50,
        "categoria": "Comida",
        "categoria_id": "1",
        "confianza_categoria": 0.82
      }
    ],
    "texto_crudo": "..."
  },
  "categorias_usadas": [
    {
      "idCategoria": "1",
      "name": "Comida",
      "icon": "restaurant",
      "color": "#FF0000",
      "esPersonalizada": false,
      "estado": 1
    }
  ],
  "tiempo_procesamiento_ms": 3450.12
}
```

> Cambios recientes:
> - El endpoint `/ocr` ahora retorna `categoria_id` en cada producto clasificado.
> - Las categorías se obtienen exclusivamente desde el backend configurado en `CATEGORIAS_BACKEND_URL`.
> - Si la conexión al backend no está disponible, el servicio no arranca.

### Endpoint `/entrenar`

- Método: `POST`
- Content-Type: `application/json`
- Body JSON:

```json
{
  "pairs": [["Pan integral", "Comida"], ["Pasaje bus", "Transporte"]]
}
```

- Parámetros:
  - `pairs`: lista de pares `[[nombre_producto, nombre_categoria], ...]`. Requerido.

### Endpoint `/categorias`

- Método: `GET`
- Response: lista de categorías disponibles.

### Endpoint `/health`

- Método: `GET`
- Response: estado del servicio e información de carga.

## Entrenamiento supervisado

Agrega pares producto→categoría en `data/pairs.json` y ejecuta:

```bash
python app/train.py
```

O vía API:

```bash
curl -X POST http://127.0.0.1:8000/entrenar \
  -H "Content-Type: application/json" \
  -d '{"pairs": [["Arroz", "Comida"], ["Taxi", "Transporte"]]}'
```

## Categorías

Usa la API de categorías de tu backend. Si el backend no responde, el servicio no podrá cargar categorías y fallará al iniciar.

Configura la URL de backend en un archivo `.env` o en tu entorno:

```env
CATEGORIAS_BACKEND_URL=https://mi-backend.local/v1/categoria/publico/listar
FINANZAS360_TOKEN=<token_opcional>
CATEGORIAS_VERIFY_SSL=false
```

- `CATEGORIAS_VERIFY_SSL`: `true` o `false`. Útil cuando el backend usa certificado autofirmado.

| Categoría | Icono |
|-----------|-------|
| Comida | restaurant |
| Transporte | directions_car |
| Salud | local_hospital |
| Entretenimiento | movie |
| Servicios | build |
| Educación | school |
| Ropa y Calzado | checkroom |
| Vivienda | home |
| Otros | category |

## Estructura del proyecto

```
├── run.py                     # Inicia el servidor
├── app/
│   ├── main.py                # FastAPI (endpoints)
│   ├── ocr/
│   │   ├── extractor.py       # EasyOCR + parsing de documentos
│   │   └── processor.py       # PDF → imágenes
│   └── classifier/
│       ├── api_client.py      # Cliente API Finanzas360
│       └── categorizer.py     # Clasificador semántico + fine-tuning
├── data/
│   ├── categorias_fallback.json
│   └── pairs.json             # Ejemplos para entrenamiento
└── requirements.txt
```
