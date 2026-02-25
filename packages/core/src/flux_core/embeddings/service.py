import math
from typing import Protocol

try:
    from fastembed import TextEmbedding

    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False
    TextEmbedding = None  # type: ignore


class EmbeddingService:
    """Generate embeddings using fastembed (ONNX-based, no PyTorch required).

    Requires fastembed to be installed:
        pip install flux-core[embeddings]
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        if not FASTEMBED_AVAILABLE:
            raise ImportError(
                "fastembed is not installed. "
                "Install it with: pip install flux-core[embeddings]"
            )
        self._model = TextEmbedding(model_name=model_name)

    def embed(self, text: str) -> list[float]:
        embeddings = list(self._model.embed([text]))
        return embeddings[0].tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [e.tolist() for e in self._model.embed(texts)]

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class EmbeddingProvider(Protocol):
    """Structural type for services that can generate embeddings."""

    def embed(self, text: str) -> list[float]:
        ...
