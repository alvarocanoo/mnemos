from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DecayConfig:
    """Per-importance-tier decay rates (λ) for `w(t) = exp(-λ · Δt_days)`.

    Defaults give intuitive half-lives:
      low (1):    λ=0.05  -> half-life ~14 days  (chatty / one-off memories fade fast)
      normal (2): λ=0.02  -> half-life ~35 days  (typical facts)
      high (3):   λ=0.005 -> half-life ~140 days (key references stay visible long)

    Half-life math: t_½ = ln(2) / λ, so ln(2) ≈ 0.693.

    Tunable via Settings.decay_lambda_{low,normal,high}; weights become an
    explicit eval axis once the temporal dataset grows.
    """

    lambda_low: float = 0.05
    lambda_normal: float = 0.02
    lambda_high: float = 0.005

    def lambda_for(self, importance: int) -> float:
        if importance <= 1:
            return self.lambda_low
        if importance >= 3:
            return self.lambda_high
        return self.lambda_normal


def decay_weight(
    importance: int,
    age_days: float,
    config: DecayConfig | None = None,
) -> float:
    """Exponential decay weight in [0, 1]. age_days < 0 is treated as 0."""
    cfg = config or DecayConfig()
    if age_days <= 0:
        return 1.0
    return math.exp(-cfg.lambda_for(importance) * age_days)


def age_in_days(created_at: datetime, now: datetime | None = None) -> float:
    reference = now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    delta = reference - created_at
    return max(0.0, delta.total_seconds() / 86_400.0)
