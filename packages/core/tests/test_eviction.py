import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from mnemos.memory.decay import DecayConfig
from mnemos.memory.eviction import (
    EvictionConfig,
    composite_score,
    score_user_memories,
    select_for_eviction,
)


def test_composite_score_default_weights_basic():
    s = composite_score(importance=2, recency_weight=0.5, access_count=0)
    expected = 1.0 * 2 + 1.0 * 0.5 + 0.5 * math.log1p(0)
    assert math.isclose(s, expected, rel_tol=1e-9)


def test_composite_score_access_count_uses_log1p():
    s = composite_score(importance=0, recency_weight=0, access_count=99)
    expected = 0.5 * math.log1p(99)
    assert math.isclose(s, expected, rel_tol=1e-9)


def test_composite_score_negative_access_clamped_to_zero():
    s = composite_score(importance=0, recency_weight=0, access_count=-5)
    assert s == 0.0


def test_composite_score_custom_weights():
    cfg = EvictionConfig(w_importance=2.0, w_recency=0.0, w_access=0.0)
    assert composite_score(3, 1.0, 0, cfg) == 6.0


def test_high_importance_outranks_low_at_same_recency():
    high = composite_score(3, 0.5, 0)
    low = composite_score(1, 0.5, 0)
    assert high > low


def test_higher_access_count_helps_monotonically():
    base = composite_score(2, 0.5, 0)
    one = composite_score(2, 0.5, 1)
    ten = composite_score(2, 0.5, 10)
    hundred = composite_score(2, 0.5, 100)
    assert one > base
    assert ten > one
    assert hundred > ten


def test_log1p_per_unit_increment_diminishes():
    # The per-unit access-count gain shrinks as the base grows.
    # i.e. going from 0 -> 1 adds more than going from 99 -> 100.
    gain_low = composite_score(0, 0, 1) - composite_score(0, 0, 0)
    gain_high = composite_score(0, 0, 100) - composite_score(0, 0, 99)
    assert gain_low > gain_high


@dataclass
class _FakeRow:
    id: object
    importance: int
    created_at: datetime
    access_count: int


def _mock_session(rows: list[_FakeRow]) -> MagicMock:
    session = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = rows
    result = MagicMock()
    result.scalars.return_value = scalars
    session.execute.return_value = result
    return session


def test_score_user_memories_orders_ascending_by_score():
    now = datetime(2026, 5, 26, tzinfo=timezone.utc)
    rows = [
        _FakeRow(uuid4(), importance=3, created_at=now - timedelta(days=1), access_count=10),
        _FakeRow(uuid4(), importance=1, created_at=now - timedelta(days=200), access_count=0),
        _FakeRow(uuid4(), importance=2, created_at=now - timedelta(days=30), access_count=2),
    ]
    session = _mock_session(rows)

    scored = score_user_memories(session, "u", now=now)
    scores = [s.score for s in scored]
    assert scores == sorted(scores)
    assert scored[0].importance == 1  # the old low-importance one is least valuable
    assert scored[-1].importance == 3


def test_select_for_eviction_returns_bottom_excess():
    now = datetime(2026, 5, 26, tzinfo=timezone.utc)
    rows = [
        _FakeRow(uuid4(), importance=3, created_at=now - timedelta(days=1), access_count=10),
        _FakeRow(uuid4(), importance=1, created_at=now - timedelta(days=200), access_count=0),
        _FakeRow(uuid4(), importance=2, created_at=now - timedelta(days=30), access_count=2),
        _FakeRow(uuid4(), importance=1, created_at=now - timedelta(days=180), access_count=1),
    ]
    session = _mock_session(rows)

    to_evict = select_for_eviction(session, "u", max_count=2, now=now)
    assert len(to_evict) == 2
    # The 2 least valuable should be the old low-importance ones.
    importances_evicted = sorted(s.importance for s in to_evict)
    assert importances_evicted == [1, 1]


def test_select_for_eviction_under_cap_returns_empty():
    now = datetime(2026, 5, 26, tzinfo=timezone.utc)
    rows = [
        _FakeRow(uuid4(), importance=2, created_at=now, access_count=0),
        _FakeRow(uuid4(), importance=2, created_at=now, access_count=0),
    ]
    session = _mock_session(rows)
    assert select_for_eviction(session, "u", max_count=5, now=now) == []


def test_select_for_eviction_max_count_zero_evicts_all():
    now = datetime(2026, 5, 26, tzinfo=timezone.utc)
    rows = [
        _FakeRow(uuid4(), importance=2, created_at=now, access_count=0),
        _FakeRow(uuid4(), importance=3, created_at=now, access_count=10),
    ]
    session = _mock_session(rows)
    assert len(select_for_eviction(session, "u", max_count=0, now=now)) == 2


def test_select_for_eviction_negative_max_count_raises():
    with pytest.raises(ValueError):
        select_for_eviction(_mock_session([]), "u", max_count=-1)


def test_recency_weight_visible_in_scored_memory():
    now = datetime(2026, 5, 26, tzinfo=timezone.utc)
    rows = [
        _FakeRow(uuid4(), importance=2, created_at=now - timedelta(days=30), access_count=0),
    ]
    session = _mock_session(rows)
    cfg = DecayConfig()
    scored = score_user_memories(session, "u", decay_cfg=cfg, now=now)
    assert 0.0 < scored[0].recency_weight < 1.0
    assert scored[0].age_days == 30.0
