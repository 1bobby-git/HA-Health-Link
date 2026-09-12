"""Regression tests for the real ECG import execution path."""
from __future__ import annotations

import inspect

from custom_components.health_link import data_features
from custom_components.health_link import ecg_import_fast


def test_data_features_uses_fast_ecg_reader():
    assert data_features.read_file is ecg_import_fast.read_file


def test_import_does_not_wait_for_full_coordinator_refresh():
    source = inspect.getsource(data_features.import_uploaded)
    assert "_schedule_refresh(hass, entry)" in source
    assert "await entry.runtime_data.coordinator.async_refresh_from_store()" not in source


def test_import_result_contains_phase_timings():
    source = inspect.getsource(data_features._import_sync)
    assert "parse_stage_seconds" in source
    assert "db_write_seconds" in source
