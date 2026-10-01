import pytest

from postpy.core import history
from postpy.core.history import HistoryStore
from postpy.core.models import RequestHistory


def entry(n: int) -> RequestHistory:
    return RequestHistory(
        name=f"r{n}",
        method="GET",
        endpoint=f"/{n}",
        timestamp="2026-01-01T00:00:00",
        status_code=200,
        response_time=0.1,
    )


def test_append_and_read(tmp_path, postpy_home):
    store = HistoryStore(tmp_path / "c.json")
    store.append([entry(1), entry(2)])
    store.append([entry(3)])

    assert [e.name for e in store.read()] == ["r1", "r2", "r3"]
    assert [e.name for e in store.read(limit=2)] == ["r2", "r3"]
    assert store.path.is_relative_to(postpy_home)


def test_collections_have_separate_histories(tmp_path):
    (tmp_path / "a").mkdir()
    first = HistoryStore(tmp_path / "a" / "c.json")
    second = HistoryStore(tmp_path / "c.json")
    first.append([entry(1)])

    assert first.path != second.path
    assert second.read() == []


def test_history_is_trimmed(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "MAX_ENTRIES", 3)
    store = HistoryStore(tmp_path / "c.json")
    store.append([entry(n) for n in range(5)])

    assert [e.name for e in store.read()] == ["r2", "r3", "r4"]


def test_malformed_lines_are_skipped(tmp_path):
    store = HistoryStore(tmp_path / "c.json")
    store.append([entry(1)])
    with store.path.open("a") as f:
        f.write("{broken\n")
    store.append([entry(2)])

    assert [e.name for e in store.read()] == ["r1", "r2"]


def test_empty_append_creates_nothing(tmp_path):
    store = HistoryStore(tmp_path / "c.json")
    store.append([])
    assert not store.path.exists()


@pytest.mark.parametrize("limit", [0, -1])
def test_non_positive_limit(tmp_path, limit):
    store = HistoryStore(tmp_path / "c.json")
    store.append([entry(1)])
    assert store.read(limit=limit) == []
