import os
from typing import List, Optional

import requests
from dotenv import load_dotenv

from app.models.schemas import Categoria

load_dotenv()


class CategoriaAPIClient:
    """Cliente para la API de categorías del backend."""

    BASE_URL = os.getenv(
        "CATEGORIAS_BACKEND_URL",
        "https://localhost:7123/v1/categoria/publico/listar",
    )

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
    ):
        self.token = token or os.getenv("FINANZAS360_TOKEN")
        self.base_url = base_url or self.BASE_URL
        if verify_ssl is None:
            raw_verify = os.getenv("CATEGORIAS_VERIFY_SSL", "true").strip().lower()
            self.verify_ssl = raw_verify not in ("0", "false", "no")
        else:
            self.verify_ssl = verify_ssl

    def listar_categorias(self) -> List[Categoria]:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = requests.get(
            self.base_url,
            headers=headers or None,
            timeout=10,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        data = response.json()
        return [Categoria(**item) for item in data]
