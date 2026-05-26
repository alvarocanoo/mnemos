import pytest
from mnemos.models import MemoryWrite, SearchQuery
from pydantic import ValidationError


def test_memory_write_defaults():
    m = MemoryWrite(content="hello")
    assert m.importance == 2
    assert m.user_id == "default"
    assert m.metadata == {}


def test_memory_write_importance_bounds():
    with pytest.raises(ValidationError):
        MemoryWrite(content="x", importance=0)
    with pytest.raises(ValidationError):
        MemoryWrite(content="x", importance=4)


def test_memory_write_content_min_length():
    with pytest.raises(ValidationError):
        MemoryWrite(content="")


def test_search_query_limit_bounds():
    assert SearchQuery(query="x").limit == 10
    with pytest.raises(ValidationError):
        SearchQuery(query="x", limit=0)
    with pytest.raises(ValidationError):
        SearchQuery(query="x", limit=101)
