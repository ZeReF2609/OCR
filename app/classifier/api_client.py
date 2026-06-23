import json
import os
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv

from app.models.schemas import Categoria

load_dotenv()


class CategoriaAPIClient:
    """Cliente para la API pública de categorías de Finanzas360.

    Si la API no está disponible, carga categorías desde el fallback local.
    """

    BASE_URL = "https://localhost:7123/v1/categoria/publico/listar"
    FALLBACK_PATH = Path("data/categorias_fallback.json")

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("FINANZAS360_TOKEN")

    def listar_categorias(self) -> List[Categoria]:
        if self.token:
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = requests.get(
                    self.BASE_URL, headers=headers, timeout=10
                )
                response.raise_for_status()
                data = response.json()
                return [Categoria(**item) for item in data]
            except Exception as e:
                print(f"API categorías no disponible ({e}), usando fallback local")
        else:
            print("Token no configurado, usando categorías fallback local")

        return self._load_fallback()

    @staticmethod
    def _load_fallback() -> List[Categoria]:
        path = CategoriaAPIClient.FALLBACK_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Fallback no encontrado: {path}"
            )
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return [Categoria(**item) for item in data]
