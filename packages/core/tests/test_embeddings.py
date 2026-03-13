import pytest
from flux_core.embeddings.service import EmbeddingService


@pytest.fixture(scope="module")
def embedding_service():
    return EmbeddingService()


def test_embed_returns_384_dimensions(embedding_service):
    result = embedding_service.embed("Lunch at Chipotle $15")
    assert len(result) == 384
    assert all(isinstance(x, float) for x in result)


