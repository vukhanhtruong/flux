import pytest
from flux_core.embeddings.service import EmbeddingService


@pytest.fixture(scope="module")
def embedding_service():
    return EmbeddingService()


def test_embed_returns_384_dimensions(embedding_service):
    result = embedding_service.embed("Lunch at Chipotle $15")
    assert len(result) == 384
    assert all(isinstance(x, float) for x in result)


def test_similar_texts_have_high_similarity(embedding_service):
    e1 = embedding_service.embed("Lunch at restaurant")
    e2 = embedding_service.embed("Dinner at restaurant")
    e3 = embedding_service.embed("Monthly rent payment")

    sim_12 = embedding_service.cosine_similarity(e1, e2)
    sim_13 = embedding_service.cosine_similarity(e1, e3)
    assert sim_12 > sim_13
