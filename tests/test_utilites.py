# ============================== tests/test_utilities.py ==============================
import pytest
from src.utilities import phone_utils, text_processing

def test_normalize_phone():
    assert phone_utils.normalize("+1 (555) 123-4567") == "+15551234567"

def test_invalid_phone_raises():
    with pytest.raises(ValueError):
        phone_utils.normalize("abcd")

def test_stop_words_removed():
    text = "This is a simple test of the chunking"
    processed = text_processing.remove_stopwords(text)
    assert "is" not in processed

def test_chunking_overlap():
    text = "word " * 1200
    chunks = text_processing.chunk_text(text, max_tokens=1000, overlap=100)
    assert len(chunks) > 1