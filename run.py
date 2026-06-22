"""
Script principal para ejecutar el servidor OCR.

Uso:
    python run.py                   # Inicia servidor en puerto 8000
    python run.py --port 9000       # Puerto personalizado
    python run.py --host 0.0.0.0    # Accesible desde la red
"""
import argparse
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor OCR Finanzas360")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", default=True)
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
