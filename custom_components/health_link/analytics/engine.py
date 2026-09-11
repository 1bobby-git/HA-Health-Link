"""Observational analytics helpers for HealthLink.

These functions describe associations in the user's own data. They do not infer
medical causation and must not be used as an independent safety-control signal.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime
import math
from statistics import fmean
from typing import Iterable


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    """Pearson association summary."""

    pairs: int
    correlation: float | None
    strength: str
    direction: str


def _as_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _timestamp(value: str) -> float | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def align_previous(
    health_points: Iterable[tuple[str, float]],
    home_points: Iterable[tuple[str, float]],
) -> list[tuple[float, float]]:
    """Pair each health point with the latest home value known at that time.

    Using the previous state avoids look-ahead bias: a future room temperature
    must never be attached to an earlier health measurement.
    """
    home: list[tuple[float, float]] = []
    for stamp, value in home_points:
        ts = _timestamp(stamp)
        number = _as_float(value)
        if ts is not None and number is not None:
            home.append((ts, number))
    home.sort(key=lambda item: item[0])
    if not home:
        return []

    home_times = [item[0] for item in home]
    pairs: list[tuple[float, float]] = []
    for stamp, value in health_points:
        ts = _timestamp(stamp)
        health_value = _as_float(value)
        if ts is None or health_value is None:
            continue
        index = bisect_right(home_times, ts) - 1
        if index >= 0:
            pairs.append((health_value, home[index][1]))
    return pairs


def pearson(pairs: Iterable[tuple[float, float]]) -> CorrelationResult:
    """Return a compact Pearson correlation summary for finite pairs."""
    clean: list[tuple[float, float]] = []
    for x, y in pairs:
        xv = _as_float(x)
        yv = _as_float(y)
        if xv is not None and yv is not None:
            clean.append((xv, yv))

    count = len(clean)
    if count < 3:
        return CorrelationResult(count, None, "insufficient_data", "none")

    mean_x = fmean(x for x, _ in clean)
    mean_y = fmean(y for _, y in clean)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in clean)
    sum_x = sum((x - mean_x) ** 2 for x, _ in clean)
    sum_y = sum((y - mean_y) ** 2 for _, y in clean)
    denominator = math.sqrt(sum_x * sum_y)
    if denominator == 0:
        return CorrelationResult(count, None, "undefined", "none")

    coefficient = max(-1.0, min(1.0, numerator / denominator))
    coefficient = round(coefficient, 4)
    magnitude = abs(coefficient)
    if magnitude >= 0.7:
        strength = "strong"
    elif magnitude >= 0.4:
        strength = "moderate"
    elif magnitude >= 0.2:
        strength = "weak"
    else:
        strength = "negligible"
    direction = "positive" if coefficient > 0 else "negative" if coefficient < 0 else "none"
    return CorrelationResult(count, coefficient, strength, direction)


def _percentile(sorted_values: list[float], fraction: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * fraction
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def observed_best_range(
    pairs: Iterable[tuple[float, float]], *, goal: str = "high"
) -> dict[str, float | int | str] | None:
    """Describe the environment values seen with the best observed outcomes.

    Pair layout is ``(outcome, environment)``. At least eight observations are
    required. The result uses the best quartile of outcomes and the 10th–90th
    percentile environment interval to reduce sensitivity to individual outliers.
    """
    clean: list[tuple[float, float]] = []
    for outcome, environment in pairs:
        ov = _as_float(outcome)
        ev = _as_float(environment)
        if ov is not None and ev is not None:
            clean.append((ov, ev))
    if len(clean) < 8 or goal not in {"high", "low"}:
        return None

    clean.sort(key=lambda item: item[0], reverse=goal == "high")
    selected_count = max(3, math.ceil(len(clean) * 0.25))
    selected = clean[:selected_count]
    environment_values = sorted(environment for _, environment in selected)

    low = _percentile(environment_values, 0.10)
    high = _percentile(environment_values, 0.90)
    return {
        "low": round(low, 4),
        "high": round(high, 4),
        "median": round(_percentile(environment_values, 0.50), 4),
        "samples": selected_count,
        "total_pairs": len(clean),
        "goal": goal,
    }
