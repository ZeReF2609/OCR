import json
import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.schemas import Categoria, Producto


class ProductCategorizer:
    """Clasifica productos en categorías usando embeddings semánticos.

    Soporta:
    - Clasificación por similitud semántica (zero-shot)
    - Fine-tuning supervisado con pares producto→categoría
    - Cache de embeddings para las categorías
    """

    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(
        self,
        categorias: List[Categoria],
        model_path: Optional[str] = None,
        cache_dir: str = "data",
    ):
        self.categorias = categorias
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.model = SentenceTransformer(
            model_path or self.MODEL_NAME
        )
        self.category_names = [c.name for c in categorias]
        self.category_ids = {c.name: c.idCategoria for c in categorias}
        self._build_category_embeddings()

    def _build_category_embeddings(self) -> None:
        cache_file = self.cache_dir / "category_embeddings.pkl"
        if cache_file.exists():
            with open(cache_file, "rb") as f:
                self.category_embeddings = pickle.load(f)
        else:
            self.category_embeddings = self.model.encode(
                self.category_names, convert_to_numpy=True
            )
            with open(cache_file, "wb") as f:
                pickle.dump(self.category_embeddings, f)

    def classify_product(
        self, producto: Producto, threshold: float = 0.3
    ) -> Tuple[str, float]:
        if not producto.nombre.strip():
            return "Sin categoría", 0.0

        product_embedding = self.model.encode(
            [producto.nombre], convert_to_numpy=True
        )
        similarities = cosine_similarity(
            product_embedding, self.category_embeddings
        )[0]
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])

        if best_score < threshold:
            return "Otros", best_score

        return self.categorias[best_idx].name, best_score

    def classify_products(
        self,
        productos: List[Producto],
        threshold: float = 0.3,
    ) -> List[Producto]:
        for p in productos:
            cat_name, conf = self.classify_product(p, threshold)
            p.categoria = cat_name
            p.categoria_id = self.category_ids.get(cat_name)
            p.confianza_categoria = round(conf, 4)
        return productos

    def fine_tune(
        self,
        pairs: List[Tuple[str, str]],
        output_path: str = "models/fine_tuned",
    ) -> None:
        """Entrena con pares (producto, categoria) para ajustar el modelo."""
        valid_categories = set(self.category_names)
        filtered = [
            (prod, cat)
            for prod, cat in pairs
            if cat in valid_categories
        ]
        if not filtered:
            raise ValueError(
                "No hay pares válidos. Las categorías deben existir en la API."
            )

        texts = [p[0] for p in filtered]
        labels_texts = [p[1] for p in filtered]

        label_embeddings = self.model.encode(
            labels_texts, convert_to_numpy=True
        )
        product_embeddings = self.model.encode(
            texts, convert_to_numpy=True
        )

        combined_embeddings = np.vstack(
            [product_embeddings, label_embeddings]
        )
        combined_labels = texts + labels_texts

        from sklearn.linear_model import LogisticRegression

        x_train = product_embeddings
        label_to_idx = {
            name: i for i, name in enumerate(self.category_names)
        }
        y_train = np.array(
            [label_to_idx[cat] for _, cat in filtered]
        )

        clf = LogisticRegression(max_iter=1000, multi_class="multinomial")
        clf.fit(x_train, y_train)

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "classifier.pkl", "wb") as f:
            pickle.dump(
                {
                    "model": clf,
                    "categories": self.category_names,
                    "label_to_idx": label_to_idx,
                },
                f,
            )

        return output_dir
