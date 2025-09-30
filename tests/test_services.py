# ============================== tests/test_services.py ==============================
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.database_service import DatabaseService
from src.services.embedding_service import EmbeddingService
from src.services.context_service import ContextService


@pytest.mark.asyncio
async def test_database_connect_disconnect():
    service = DatabaseService()
    service.client = MagicMock()
    await service.connect()
    await service.disconnect()
    service.client.close.assert_called()


@pytest.mark.asyncio
async def test_embedding_service_success(monkeypatch):
    service = EmbeddingService()
    monkeypatch.setattr(service, "embed_text", lambda text: [0.1, 0.2])
    vec = await service.create_embedding("hello")
    assert vec == [0.1, 0.2]


@pytest.mark.asyncio
async def test_embedding_service_fallback(monkeypatch):
    service = EmbeddingService()
    monkeypatch.setattr(service, "embed_text", lambda text: 1/0)  # force error
    vec = await service.create_embedding("hello")
    assert all(v == 0.0 for v in vec)