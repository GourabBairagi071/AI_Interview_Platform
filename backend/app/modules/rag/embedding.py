import hashlib
import logging
import os
import re
from typing import Any
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"
VECTOR_DIMENSION = 384


class EmbeddingService:
    _instance = None
    _fastembed_model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self):
        self.provider = os.getenv("EMBEDDING_PROVIDER", "fastembed").lower()
        self.model_name = os.getenv("EMBEDDING_MODEL_NAME", DEFAULT_MODEL_NAME)
        self.dimension = VECTOR_DIMENSION

        if self.provider in ("fastembed", "local"):
            try:
                from fastembed import TextEmbedding
                self._fastembed_model = TextEmbedding(model_name=self.model_name)
                logger.info(f"Initialized FastEmbed TextEmbedding model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Could not load FastEmbed model: {e}. Falling back to deterministic vectorizer.")
                self._fastembed_model = None
        else:
            self._fastembed_model = None

    def _deterministic_embedding(self, text: str) -> list[float]:
        """
        Deterministic, zero-dependency 384-dimensional dense vector fallback.
        Uses multi-salt SHA256 projection + term frequency hashing with L2-normalization.
        Ensures interviews NEVER crash even if external libraries or weights fail.
        """
        vec = np.zeros(self.dimension, dtype=np.float32)
        words = re.findall(r"\w+", text.lower())
        if not words:
            vec[0] = 1.0
            return vec.tolist()

        for word in words:
            # Hash word into bucket indices and sign
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if ((h >> 16) & 1) else -1.0
            vec[idx] += sign

            # Secondary projection
            h2 = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx2 = h2 % self.dimension
            sign2 = 1.0 if ((h2 >> 16) & 1) else -1.0
            vec[idx2] += sign2 * 0.5

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        else:
            vec[0] = 1.0

        return vec.tolist()

    def embed_text(self, text: str) -> list[float]:
        """
        Generates a 384-dimensional normalized float embedding for a single text string.
        """
        if not text or not text.strip():
            # Return unit zero vector
            z = [0.0] * self.dimension
            z[0] = 1.0
            return z

        cleaned = text.strip()

        if self._fastembed_model is not None:
            try:
                embeddings = list(self._fastembed_model.embed([cleaned]))
                if embeddings and len(embeddings) > 0:
                    vec = embeddings[0]
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    return [float(x) for x in vec]
            except Exception as e:
                logger.warning(f"FastEmbed inference error: {e}. Using deterministic fallback.")

        return self._deterministic_embedding(cleaned)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generates embeddings for a batch of texts.
        """
        if not texts:
            return []

        cleaned_texts = [t.strip() if t and t.strip() else "general" for t in texts]

        if self._fastembed_model is not None:
            try:
                embeddings = list(self._fastembed_model.embed(cleaned_texts))
                results = []
                for vec in embeddings:
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    results.append([float(x) for x in vec])
                return results
            except Exception as e:
                logger.warning(f"FastEmbed batch inference error: {e}. Falling back to deterministic.")

        return [self._deterministic_embedding(t) for t in cleaned_texts]


# Global singleton instance
embedding_service = EmbeddingService()
