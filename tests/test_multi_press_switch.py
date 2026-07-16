"""Source-level checks for the button multi-press CONFIG switch."""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_COMP = _REPO / "custom_components" / "ha_ipbuilding_gateway"
_SWITCH_SOURCE = (_COMP / "switch.py").read_text(encoding="utf-8")
_COORD_SOURCE = (_COMP / "coordinator.py").read_text(encoding="utf-8")


def test_multi_press_switch_class_is_config_entity() -> None:
    assert "class IPBuildingMultiPressSwitch" in _SWITCH_SOURCE
    assert "EntityCategory.CONFIG" in _SWITCH_SOURCE
    assert '_attr_translation_key = "multi_press"' in _SWITCH_SOURCE
    assert 'unique_id = f"{self._hardware_id}_multi_press"' in _SWITCH_SOURCE


def test_multi_press_switch_patches_gateway() -> None:
    assert 'async_patch_device' in _SWITCH_SOURCE
    assert '{"multi_press": True}' in _SWITCH_SOURCE or '{"multi_press": True}' in _SWITCH_SOURCE.replace(
        " ", ""
    )
    # turn on / off both go through PATCH
    assert re.search(
        r'async_patch_device\(\s*self\._hardware_id\s*,\s*\{\s*["\']multi_press["\']\s*:\s*True',
        _SWITCH_SOURCE,
    )
    assert re.search(
        r'async_patch_device\(\s*self\._hardware_id\s*,\s*\{\s*["\']multi_press["\']\s*:\s*False',
        _SWITCH_SOURCE,
    )


def test_coordinator_has_async_patch_device() -> None:
    assert "async def async_patch_device" in _COORD_SOURCE
    assert "/api/v1/devices/" in _COORD_SOURCE
    assert "session.patch" in _COORD_SOURCE


def test_switch_setup_registers_input_buttons() -> None:
    assert "DEVICE_TYPE_INPUT" in _SWITCH_SOURCE
    assert "IPBuildingMultiPressSwitch" in _SWITCH_SOURCE


def test_i18n_has_multi_press_switch_name() -> None:
    import json

    for path in (
        _COMP / "strings.json",
        _COMP / "translations" / "en.json",
        _COMP / "translations" / "nl.json",
    ):
        data = json.loads(path.read_text(encoding="utf-8"))
        name = data["entity"]["switch"]["multi_press"]["name"]
        assert name
    nl = json.loads(
        (_COMP / "translations" / "nl.json").read_text(encoding="utf-8")
    )
    assert "Dubbel" in nl["entity"]["switch"]["multi_press"]["name"]
