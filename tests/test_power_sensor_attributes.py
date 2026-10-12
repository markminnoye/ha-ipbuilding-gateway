"""Runtime tests for Power sensor attributes (max_watt).

Requires a real ``homeassistant`` package; otherwise skipped.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ha = pytest.importorskip("homeassistant")

_REPO = Path(__file__).resolve().parents[1]
_COMP_DIR = _REPO / "custom_components" / "ha_ipbuilding_gateway"


def _load_companion_module(name: str):
    """Load ``ha_ipbuilding_gateway.<name>`` and its minimal dependencies."""
    if "ha_ipbuilding_gateway" not in sys.modules:
        pkg = types.ModuleType("ha_ipbuilding_gateway")
        pkg.__path__ = [str(_COMP_DIR)]
        sys.modules["ha_ipbuilding_gateway"] = pkg

    def _load(mod_name: str):
        spec = importlib.util.spec_from_file_location(
            f"ha_ipbuilding_gateway.{mod_name}", _COMP_DIR / f"{mod_name}.py"
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        try:
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        except Exception as exc:
            pytest.skip(f"companion.{mod_name} failed to import: {exc}")
        return mod

    for dep in ("const", "coordinator", "entity", "hub"):
        _load(dep)
    return _load(name)


def _make_power_sensor():
    sensor_mod = _load_companion_module("sensor")
    device = {
        "id": "10.10.1.30-0",
        "name": "Keuken LED",
        "semantic_type": "light",
        "device_type": "relay",
        "module_id": "00:24:77:52:ac:be",
        "module_ip": "10.10.1.30",
        "max_watt": 60,
    }
    coordinator = MagicMock()
    coordinator.module_for_channel.return_value = None
    return sensor_mod.IPBuildingPowerSensor(device, coordinator)


class TestPowerSensorAttributes:
    def test_max_watt_attribute_from_state(self):
        sensor = _make_power_sensor()
        sensor._update_from_state({"current_watt": 60, "max_watt": 60})
        assert sensor._attr_native_value == 60
        assert sensor._attr_extra_state_attributes == {"max_watt": 60}

    def test_max_watt_attribute_missing_is_none(self):
        sensor = _make_power_sensor()
        sensor._update_from_state({"current_watt": 0})
        assert sensor._attr_native_value == 0
        assert sensor._attr_extra_state_attributes == {"max_watt": None}
