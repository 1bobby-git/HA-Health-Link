"""Regression tests based on the structure of a real Korean Apple Health export.

Fixtures are synthetic and contain no user health data.
"""
from __future__ import annotations

import io
from zipfile import ZipInfo

from custom_components.health_link.ecg_import_fast import (
    _eligible_ecg_members,
    ecg_csv_localized,
)


def test_korean_apple_ecg_csv_metadata_and_waveform():
    data = (
        '이름,REMOVED\n'
        '생년월일,REMOVED\n'
        '기록된 날짜,2020-11-07 08:46:13 +0900\n'
        '분류,동리듬\n'
        '증상,피로감,가슴의 뻐근함 또는 흉통\n'
        '소프트웨어 버전,1.90\n'
        '기기,"Watch4,3"\n'
        '샘플률,512.555헤르츠\n\n'
        '유도,유도 I\n'
        '단위,µV\n\n'
        '-219.406\n-294.247\n-340.653\n'
    ).encode('utf-8')
    items = ecg_csv_localized(io.BytesIO(data))
    record = next(item for item in items if item['object_kind'] == 'ecg')
    chunk = next(item for item in items if item['object_kind'] == 'series_chunk')
    assert record['payload']['classification'] == '동리듬'
    assert record['payload']['sampling_frequency_hz'] == 512.555
    assert record['payload']['lead'] == '유도 I'
    assert record['source']['name'] == 'Watch4,3'
    assert chunk['points'][0][1] == -0.219406
    assert 'REMOVED' not in str(items)


def test_ecg_scope_ignores_gigabyte_unrelated_health_xml_size():
    huge = ZipInfo('apple_health_export/export.xml')
    huge.file_size = 2 * 1024 * 1024 * 1024
    huge.compress_size = 20 * 1024 * 1024
    ecg = ZipInfo('apple_health_export/electrocardiograms/ecg_2020-11-07.csv')
    ecg.file_size = 120_000
    ecg.compress_size = 52_000
    eligible = _eligible_ecg_members([huge, ecg])
    assert [item.filename for item in eligible] == [ecg.filename]


def test_ecg_scope_matches_folder_case_insensitively():
    ecg = ZipInfo('APPLE_HEALTH_EXPORT/ELECTROCARDIOGRAMS/ECG.CSV')
    ecg.file_size = 500
    ecg.compress_size = 250
    assert _eligible_ecg_members([ecg]) == [ecg]
