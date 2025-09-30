# ============================== tests/test_performance.py ==============================
import pytest
import time
from src.services.embedding_service import EmbeddingService


@pytest.mark.asyncio
async def test_embedding_large_document(monkeypatch):
    service = EmbeddingService()
    monkeypatch.setattr(service, "embed_text", lambda text: [0.1, 0.2, 0.3])
    text = "word " * 12000  # long content
    start = time.time()
    _ = await service.create_embedding(text)
    elapsed = time.time() - start
    assert elapsed < 2  # embedding should be fast enough