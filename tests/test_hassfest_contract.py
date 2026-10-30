"""Hassfest rules that the daily Validate run enforces (v0.3.10)."""
import json
import re
from pathlib import Path

INTEGRATION = Path(__file__).resolve().parents[1] / "custom_components/health_link"


def test_requirements_use_a_minimum_version_for_packages_home_assistant_ships():
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    assert "defusedxml>=0.7.1" in manifest["requirements"]
    assert not any(item.startswith("defusedxml==") for item in manifest["requirements"])


def test_async_setup_declares_a_config_entry_only_schema():
    source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    assert "async def async_setup(" in source
    assert re.search(r"^CONFIG_SCHEMA = cv\.config_entry_only_config_schema\(DOMAIN\)$", source, re.M)
