"""Synthetic fixtures only: never publish a user's real health export."""
import asyncio
from contextlib import closing
import io
import json
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import zipfile

import pytest
from defusedxml.common import DefusedXmlException

from custom_components.health_link.health_import import (
    ECG_TYPE, HealthImportError, ecg_csv, ecg_record, finite, json_records, raw_record, read_file, timestamp,
)
from custom_components.health_link.data_features import (
    _import_sync, _ecg_records_sync, _waveform_sync, ecg_snapshot, exposed_types,
    import_uploaded, register_data_services, set_exposure,
)
from custom_components.health_link.storage import HealthLinkStore


def raw(**changes):
    return {"type": "HKQuantityTypeIdentifierStepCount", "sourceName": "Synthetic Watch",
            "startDate": "2026-09-10 12:00:00 +0900", "endDate": "2026-09-10 12:01:00 +0900",
            "unit": "count", "value": "123", **changes}


def ecg(**changes):
    return {"start": "2026-09-10 12:00:00 +0900", "end": "2026-09-10 12:00:01 +0900",
            "source": "Synthetic ECG", "samplingFrequency": 4, "averageHeartRate": 70,
            "classification": "Example source classification", "numberOfVoltageMeasurements": 4,
            "voltageMeasurements": [{"voltage": value, "units": "uV"} for value in [0, 120, -80, 30]], **changes}


def store_at(tmp_path, profile="test"):
    store = HealthLinkStore(None, tmp_path / f"{profile}.db", profile)
    asyncio.run(store.async_initialize(config_entry_id=profile, display_name=profile, timezone_name="Asia/Seoul"))
    return store


def test_raw_intervals_never_alias_labs_totals_or_other_sources():
    item = raw_record(raw())
    assert item["type_id"].startswith("apple_export.HKQuantityTypeIdentifierStepCount.")
    assert item["numeric_value"] == 123
    assert item["start"] == "2026-09-10T03:00:00+00:00"
    assert item["metadata"]["healthkit_sample_timestamp_available"]
    assert raw_record(raw(sourceName="Other Phone"))["type_id"] != item["type_id"]
    assert raw_record(raw(unit="other unit"))["type_id"] != item["type_id"]
    assert raw_record(raw())["sample_uuid"] == item["sample_uuid"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "-Infinity", True, None])
def test_invalid_numbers_are_not_health_values(value):
    with pytest.raises(HealthImportError):
        finite(value)


def test_timezone_is_required_instead_of_assuming_ha_report_time():
    with pytest.raises(HealthImportError, match="timezone_required"):
        timestamp("2026-09-10T12:00:00")


def test_category_values_and_unknown_privacy():
    item = raw_record(raw(type="HKCategoryTypeIdentifierSleepAnalysis", value="HKCategoryValueSleepAnalysisAsleepREM", unit=None))
    assert item["text_value"] == "HKCategoryValueSleepAnalysisAsleepREM"
    assert item["object_kind"] == "category"
    unknown = raw_record(raw(type="HKQuantityTypeIdentifierNewPrivateSignal"))
    assert unknown["privacy_class"] == "sensitive"


def test_ecg_voltages_and_time_offsets_are_exact():
    items = ecg_record(ecg())
    record = next(x for x in items if x["object_kind"] == "ecg")
    chunk = next(x for x in items if x["object_kind"] == "series_chunk")
    assert chunk["points"] == [[0.0, 0.0], [0.25, 0.12], [0.5, -0.08], [0.75, 0.03]]
    assert record["payload"]["classification"] == "Example source classification"
    assert record["payload"]["medical_diagnosis"] is False
    assert record["payload"]["symptoms_status"] is None


@pytest.mark.parametrize("changes", [
    {"numberOfVoltageMeasurements": 9},
    {"samplingFrequency": 0},
    {"voltageMeasurements": [{"voltage": 1}]},
    {"voltageMeasurements": [{"voltage": 1, "units": "V", "time_since_start": -1}]},
    {"end": "2026-09-10 11:59:59 +0900"},
])
def test_invalid_ecg_metadata_is_not_guessed(changes):
    with pytest.raises(HealthImportError):
        ecg_record(ecg(**changes))


def test_english_ecg_csv_with_decimal_comma_and_no_patient_fields_saved():
    data = ('Name,NOT STORED\nDate of Birth,NOT STORED\nRecorded Date,2026-09-10 12:00:00 +0900\n'
            'Classification,Example only\nSample Rate,4 hertz\nLead,Lead I\nUnit,µV\n\n120,500\n-80,250\n').encode()
    items = ecg_csv(io.BytesIO(data))
    chunk = next(x for x in items if x["object_kind"] == "series_chunk")
    assert chunk["points"][0][1] == 0.1205
    assert "NOT STORED" not in json.dumps(items)


def test_xml_and_zip_are_read_without_extraction(tmp_path):
    document = '<HealthData><Record type="HKQuantityTypeIdentifierStepCount" sourceName="Test" unit="count" value="10" startDate="2026-09-10 12:00:00 +0900" endDate="2026-09-10 12:01:00 +0900"/></HealthData>'
    path = tmp_path / "export.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("apple_health_export/export.xml", document)
    result = list(read_file(path))
    assert len(result) == 1 and result[0]["numeric_value"] == 10
    assert not (tmp_path / "apple_health_export").exists()


def test_zip_path_traversal_and_xml_entity_expansion_rejected(tmp_path):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../export.xml", "<HealthData/>")
    with pytest.raises(HealthImportError, match="unsafe_archive"):
        list(read_file(path))
    xml = tmp_path / "bad.xml"
    xml.write_text('<!DOCTYPE HealthData [<!ENTITY leak SYSTEM "file:///etc/passwd">]><HealthData>&leak;</HealthData>')
    with pytest.raises((DefusedXmlException, HealthImportError)):
        list(read_file(xml))


def test_import_is_atomic_deduplicated_and_does_not_refresh_labs(tmp_path):
    store = store_at(tmp_path)
    with closing(store._connect()) as con, con:
        con.execute("INSERT INTO meta VALUES(?,?,?)", (store.profile_id, "last_sync", "old-live-sync"))
    items = ecg_record(ecg())
    first = _import_sync(store, iter(items), True, "all")
    second = _import_sync(store, iter(items), True, "all")
    assert first["ecg_new"] == 1 and second["ecg_new"] == 0
    assert _ecg_records_sync(store)["count"] == 1
    assert asyncio.run(store.async_status())["last_sync"] == "old-live-sync"
    assert asyncio.run(store.async_catalog())[0]["object_kind"] == "ecg"
    def broken():
        yield raw_record(raw())
        raise HealthImportError("invalid_import_file")
    before = asyncio.run(store.async_status())["sample_count"]
    with pytest.raises(HealthImportError):
        _import_sync(store, broken(), True, "all")
    assert asyncio.run(store.async_status())["sample_count"] == before


def test_sensitive_collection_and_exposure_are_opt_in(tmp_path):
    store = store_at(tmp_path)
    result = _import_sync(store, iter(ecg_record(ecg())), False, "all")
    assert result["empty"] and result["skipped_sensitive"] == 1
    assert _ecg_records_sync(store)["count"] == 0
    _import_sync(store, iter(ecg_record(ecg())), True, "all")
    assert asyncio.run(ecg_snapshot(store, {"enable_sensitive": True})) == {}
    asyncio.run(set_exposure(store, [ECG_TYPE], [ECG_TYPE]))
    assert asyncio.run(exposed_types(store, {"enable_sensitive": False})) == []
    assert asyncio.run(ecg_snapshot(store, {"enable_sensitive": True}))["count"] == 1
    assert asyncio.run(ecg_snapshot(store, {"enable_sensitive": False})) == {}


def test_waveform_pagination_and_profile_isolation(tmp_path):
    store = store_at(tmp_path)
    _import_sync(store, iter(ecg_record(ecg())), True, "all")
    identifier = _ecg_records_sync(store)["records"][0]["object_uuid"]
    page = _waveform_sync(store, identifier, 1, 2)
    assert page["points"] == [[0.25, 0.12], [0.5, -0.08]]
    assert page["next_offset"] == 3
    other = store_at(tmp_path, "other")
    with pytest.raises(HealthImportError, match="ecg_not_found"):
        _waveform_sync(other, identifier, 0, 4)


def test_native_image_is_png_without_patient_information():
    from PIL import Image
    from custom_components.health_link.image import render_waveform
    data = render_waveform([[0.0, 0.0], [0.25, 0.12], [0.5, -0.08]])
    with Image.open(io.BytesIO(data)) as image:
        assert image.format == "PNG"
        assert image.size == (1200, 360)
        image.verify()


def test_real_ha_services_and_uploaded_file_cleanup(tmp_path):
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.core import Context, HomeAssistant
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.components.file_upload import FileUploadData
    async def run():
        hass = HomeAssistant(str(tmp_path))
        store = HealthLinkStore(hass, tmp_path / "native.db", "native")
        await store.async_initialize(config_entry_id="native", display_name="Synthetic", timezone_name="UTC")
        entry = NS(entry_id="native", title="Synthetic", data={"profile_id": "native"},
                   options={"enable_sensitive": True}, state=ConfigEntryState.LOADED, disabled_by=None,
                   runtime_data=NS(store=store, coordinator=NS(async_refresh_from_store=AsyncMock())))
        hass.config_entries = NS(async_entries=lambda domain: [entry])
        register_data_services(hass)
        result = await hass.services.async_call("health_link", "get_ecg_records", {}, blocking=True, return_response=True)
        assert result["count"] == 0
        directory = tmp_path / "uploads"; file_id = "synthetic_upload"
        (directory / file_id).mkdir(parents=True)
        (directory / file_id / "ecg.json").write_text(json.dumps(ecg()))
        hass.data["file_upload"] = FileUploadData(directory, {file_id: "ecg.json"})
        result = await import_uploaded(hass, entry, file_id, include_sensitive=True)
        assert result["ecg_new"] == 1
        assert not (directory / file_id).exists()
        hass.auth.async_get_user = AsyncMock(return_value=NS(is_admin=False))
        with pytest.raises(HomeAssistantError, match="Administrator"):
            await hass.services.async_call("health_link", "get_ecg_records", {}, blocking=True,
                                           return_response=True, context=Context(user_id="non_admin"))
    asyncio.run(run())


def test_purge_also_removes_expired_waveform_chunks(tmp_path):
    store = store_at(tmp_path)
    record = ecg(start="2000-01-01T00:00:00+00:00", end="2000-01-01T00:00:01+00:00")
    _import_sync(store, iter(ecg_record(record)), True, "all")
    asyncio.run(store.async_purge(1))
    with closing(store._connect()) as con:
        assert con.execute("SELECT COUNT(*) FROM series_chunks").fetchone()[0] == 0


def test_ecg_scalars_are_not_the_waveform_in_attributes(tmp_path):
    from custom_components.health_link.ecg_entities import ecg_sensors
    from homeassistant.core import HomeAssistant
    async def run():
        hass = HomeAssistant(str(tmp_path))
        store = HealthLinkStore(hass, tmp_path / "sensors.db", "sensor_profile")
        await store.async_initialize(config_entry_id="sensors", display_name="Synthetic", timezone_name="UTC")
        coordinator = NS(data={"ecg": {"count": 1, "latest": {"average_heart_rate": 70, "object_uuid": "test"}}},
                         last_update_success=True, async_contexts=lambda: set())
        runtime = NS(store=store, coordinator=coordinator)
        entry = NS(entry_id="sensors", title="Synthetic", options={"enable_sensitive": True})
        entities = ecg_sensors(runtime, entry)
        assert len(entities) == 6
        assert all("points" not in (entity.extra_state_attributes or {}) for entity in entities)
        assert next(entity for entity in entities if entity.field == "average_heart_rate").native_value == 70
    asyncio.run(run())
