"""Robust, non-medical personal baseline calculations."""
from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import fmean, median
from typing import Iterable


@dataclass(frozen=True, slots=True)
class BaselineStats:
    """Summary statistics used by HealthLink's personal baseline engine."""

    count: int
    mean: float | None
    median: float | None
    mad: float | None
    minimum: float | None
    maximum: float | None


def _finite_values(values: Iterable[float | int | None]) -> list[float]:
    result: list[float] = []
    for value in values:
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            result.append(number)
    return result


def robust_baseline(values: Iterable[float | int | None]) -> BaselineStats:
    """Return median/MAD centered statistics while retaining a mean for context."""
    clean = _finite_values(values)
    if not clean:
        return BaselineStats(0, None, None, None, None, None)

    center = float(median(clean))
    deviations = [abs(value - center) for value in clean]
    mad = float(median(deviations))
    return BaselineStats(
        count=len(clean),
        mean=float(fmean(clean)),
        median=center,
        mad=mad,
        minimum=min(clean),
        maximum=max(clean),
    )


def robust_zscore(value: float | int | None, baseline: BaselineStats) -> float | None:
    """Calculate a median absolute deviation based z-score.

    0.67448975 makes the MAD-based score comparable to a standard z-score for
    normally distributed data. A zero/unknown MAD deliberately returns None
    instead of inventing confidence where the baseline has no spread.
    """
    if value is None or baseline.median is None or not baseline.mad:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return (0.67448975 * (number - baseline.median)) / baseline.mad


def relative_change(value: float | int | None, reference: float | int | None) -> float | None:
    """Return percentage change from a reference value."""
    if value is None or reference is None:
        return None
    try:
        current = float(value)
        base = float(reference)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(current) or not math.isfinite(base) or base == 0:
        return None
    return round(((current - base) / abs(base)) * 100.0, 4)
