"""Wellness-only daily context and goal helpers for HealthLink.

These helpers intentionally describe personal records and user-defined goals. They do
not diagnose conditions, prescribe treatment, or apply population health thresholds.
"""
from __future__ import annotations
from statistics import median
from typing import Any

GOAL_KEYS = {
    "steps": "goal_steps",
    "exercise_minutes": "goal_exercise_minutes",
    "active_energy": "goal_active_energy",
    "water_ml": "goal_water_ml",
    "sleep_minutes": "goal_sleep_minutes",
}


def positive_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def progress(value: Any, target: Any) -> float | None:
    target_num = positive_number(target)
    if target_num is None or value is None:
        return None
    try:
        value_num = max(0.0, float(value))
    except (TypeError, ValueError):
        return None
    return round(value_num / target_num * 100.0, 1)


def relative_to_median(value: Any, history: list[float]) -> float | None:
    if value is None or not history:
        return None
    base = median(history)
    if base == 0:
        return None
    return round((float(value) - base) / abs(base) * 100.0, 1)


def build_daily_context(snapshot: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    """Build non-medical goal progress and a concise automation-safe context."""
    values = {
        "steps": snapshot.get("steps_today"),
        "exercise_minutes": snapshot.get("exercise_time_today"),
        "active_energy": snapshot.get("active_energy_today"),
        "water_ml": snapshot.get("water_today"),
        "sleep_minutes": snapshot.get("sleep_duration"),
    }
    goals: dict[str, dict[str, Any]] = {}
    for name, option_key in GOAL_KEYS.items():
        target = positive_number(options.get(option_key))
        if target is None:
            continue
        current = values.get(name)
        pct = progress(current, target)
        goals[name] = {
            "target": target,
            "current": current,
            "progress": pct,
            "reached": bool(pct is not None and pct >= 100),
        }

    active_progress = [item["progress"] for item in goals.values() if item["progress"] is not None]
    if not goals:
        goal_context = "not_configured"
    elif active_progress and all(value >= 100 for value in active_progress) and len(active_progress) == len(goals):
        goal_context = "all_reached"
    elif active_progress:
        goal_context = "in_progress"
    else:
        goal_context = "waiting_for_data"

    focus = "none"
    incomplete = [(name, item["progress"]) for name, item in goals.items() if item["progress"] is not None and item["progress"] < 100]
    if incomplete:
        focus = min(incomplete, key=lambda item: item[1])[0]
    elif snapshot.get("recovery_below_baseline") and (snapshot.get("recovery_confidence") or 0) >= 60:
        focus = "recovery_context"

    return {"goals": goals, "goal_context": goal_context, "daily_focus": focus}


def report_payload(snapshot: dict[str, Any], options: dict[str, Any], *, profile: str) -> dict[str, Any]:
    context = build_daily_context(snapshot, options)
    highlights: list[dict[str, Any]] = []
    if snapshot.get("data_stale"):
        highlights.append({"code": "data_stale", "severity": "info"})
    if snapshot.get("recovery_below_baseline") and (snapshot.get("recovery_confidence") or 0) >= 60:
        highlights.append({
            "code": "recovery_below_personal_baseline",
            "severity": "notice",
            "confidence": snapshot.get("recovery_confidence"),
        })
    same_time = snapshot.get("steps_vs_same_time_baseline")
    if same_time is not None and same_time <= -20:
        highlights.append({"code": "activity_below_same_time_baseline", "severity": "info", "change_percent": same_time})
    if context["goal_context"] == "all_reached":
        highlights.append({"code": "configured_daily_goals_reached", "severity": "positive"})
    if not highlights:
        highlights.append({"code": "no_priority_highlight", "severity": "neutral"})
    return {
        "profile": profile,
        "wellness_only": True,
        "medical_diagnosis": False,
        "source": "home_assistant_ios_apple_health_sensors_labs",
        "data_confidence": snapshot.get("data_confidence"),
        "last_sync": snapshot.get("last_sync"),
        "highlights": highlights,
        **context,
        "metrics": {
            "steps_today": snapshot.get("steps_today"),
            "steps_vs_same_time_baseline": same_time,
            "active_energy_today": snapshot.get("active_energy_today"),
            "exercise_time_today": snapshot.get("exercise_time_today"),
            "water_today": snapshot.get("water_today"),
            "sleep_duration": snapshot.get("sleep_duration"),
            "sleep_efficiency": snapshot.get("sleep_efficiency"),
            "recovery_context": snapshot.get("recovery_context"),
            "recovery_confidence": snapshot.get("recovery_confidence"),
        },
    }
