"""
Script de entrenamiento supervisado para el clasificador de productos.

Uso:
    python app/train.py --pairs data/pairs.json --output models/fine_tuned

Formato de pairs.json:
    [
        ["Arroz integral", "Comida"],
        ["Pasaje Metropolitano", "Transporte"],
        ["Consulta médica", "Salud"],
        ...
    ]
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.classifier.api_client import CategoriaAPIClient
from app.classifier.categorizer import ProductCategorizer


def main():
    parser = argparse.ArgumentParser(
        description="Entrenar clasificador de productos por categorías"
    )
    parser.add_argument(
        "--pairs",
        type=str,
        default="data/pairs.json",
        help="JSON con pares [producto, categoria]",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="models/fine_tuned",
        help="Directorio de salida del modelo entrenado",
    )
    args = parser.parse_args()

    client = CategoriaAPIClient()
    categorias = client.listar_categorias()
    print(f"Categorías cargadas: {len(categorias)}")
    for c in categorias:
        print(f"  - {c.name} ({c.idCategoria})")

    categorizer = ProductCategorizer(categorias)

    with open(args.pairs, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    print(f"Entrenando con {len(pairs)} pares...")
    output_dir = categorizer.fine_tune(
        pairs=[(p[0], p[1]) for p in pairs],
        output_path=args.output,
    )
    print(f"Modelo guardado en: {output_dir}")


if __name__ == "__main__":
    main()
