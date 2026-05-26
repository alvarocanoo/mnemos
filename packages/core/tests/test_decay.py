import math
from datetime import datetime, timedelta, timezone

from mnemos.memory.decay import DecayConfig, age_in_days, decay_weight


def test_zero_age_returns_one():
    assert decay_weight(2, 0) == 1.0


def test_negative_age_returns_one():
    assert decay_weight(2, -5) == 1.0


def test_low_decays_faster_than_normal_at_same_age():
    assert decay_weight(1, 14) < decay_weight(2, 14) < decay_weight(3, 14)


def test_half_life_low_around_14_days():
    cfg = DecayConfig()
    expected = math.exp(-cfg.lambda_low * 14)
    assert math.isclose(decay_weight(1, 14, cfg), expected, rel_tol=1e-6)


def test_custom_lambdas_respected():
    fast = DecayConfig(lambda_low=1.0, lambda_normal=1.0, lambda_high=1.0)
    assert math.isclose(decay_weight(2, 1, fast), math.exp(-1.0), rel_tol=1e-6)


def test_lambda_for_clamps_to_low_high():
    cfg = DecayConfig()
    assert cfg.lambda_for(-1) == cfg.lambda_low
    assert cfg.lambda_for(0) == cfg.lambda_low
    assert cfg.lambda_for(5) == cfg.lambda_high
    assert cfg.lambda_for(2) == cfg.lambda_normal


def test_age_in_days_handles_naive_datetime():
    now = datetime(2026, 5, 26, tzinfo=timezone.utc)
    created_naive = datetime(2026, 5, 24)  # no tz
    assert math.isclose(age_in_days(created_naive, now=now), 2.0, abs_tol=1e-6)


def test_age_in_days_with_explicit_now():
    now = datetime.now(timezone.utc)
    created = now - timedelta(days=10, hours=12)
    assert math.isclose(age_in_days(created, now=now), 10.5, abs_tol=1e-3)


def test_age_clamped_at_zero_when_future():
    now = datetime(2026, 5, 26, tzinfo=timezone.utc)
    future = now + timedelta(days=3)
    assert age_in_days(future, now=now) == 0.0
