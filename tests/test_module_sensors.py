"""Source-level checks for module diagnostic sensors in sensor.py."""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SENSOR = (
    _REPO / "custom_components" / "ha_ipbuilding_gateway" / "sensor.py"
).read_text(encoding="utf-8")
_STRINGS = (
    _REPO / "custom_components" / "ha_ipbuilding_gateway" / "strings.json"
).read_text(encoding="utf-8")
_NL = (
    _REPO / "custom_components" / "ha_ipbuilding_gateway" / "translations" / "nl.json"
).read_text(encoding="utf-8")
_COORD = (
    _REPO / "custom_components" / "ha_ipbuilding_gateway" / "coordinator.py"
).read_text(encoding="utf-8")


def test_module_sensor_class_exists() -> None:
    assert "class IPBuildingModuleSensor" in _SENSOR


def test_module_sensor_kinds() -> None:
    for kind in ("model", "firmware", "last_seen"):
        assert f'kind="{kind}"' in _SENSOR


def test_module_sensor_unique_id_pattern() -> None:
    assert 'f"{self._mac}_{kind}"' in _SENSOR


def test_module_last_seen_is_timestamp() -> None:
    assert "SensorDeviceClass.TIMESTAMP" in _SENSOR
    assert "last_seen_source" in _SENSOR


def test_module_sensor_translations() -> None:
    for key in ("module_model", "module_firmware", "module_last_seen"):
        assert f'"{key}"' in _STRINGS
        assert f'"{key}"' in _NL


def test_coordinator_notifies_module_listeners() -> None:
    assert "register_module_listener" in _COORD
    assert "_notify_modules" in _COORD
    assert re.search(r"self\._notify_modules\(\)", _COORD)
