import json
from pathlib import Path

from custom_components.health_link.const import VERSION


def test_v035_versions_match():
    manifest = json.loads((Path(__file__).resolve().parents[1] / 'custom_components/health_link/manifest.json').read_text())
    assert VERSION == '0.3.5'
    assert manifest['version'] == VERSION
