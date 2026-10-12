"""Runtime tests for the startup-state "unknown" fix in light.py and switch.py.

These tests instantiate the real ``IPBuildingLight`` / ``IPBuildingSwitch``
classes and assert that ``_update_from_state`` maps gateway states
correctly. Requires a real ``homeassistant`` package; otherwise all
tests in this file are skipped.

Companion-only source-guard tests live in ``test_startup_state.py``;
those run unconditionally and catch the same regressions.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ha = pytest.importorskip("homeassistant")
try:
    from homeassistant.components.light import ColorMode as _ColorMode  # noqa: F401
except ModuleNotFoundError:
    pytest.skip(
        "homeassistant.components.light not available",
        allow_module_level=True,
    )

_REPO = Path(__file__).resolve().parents[1]
_COMP_DIR = _REPO / "custom_components" / "ha_ipbuilding_gateway"


def _load_companion_module(name: str):
    """Load ``ha_ipbuilding_gateway.<name>`` and its minimal dependencies.

    The companion imports a long HA chain; we stub just enough to satisfy
    the entity-class constructors used in these tests. Returns the
    requested module.
    """
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


def _make_light(*, device_type: str = "relay"):
    """Construct an IPBuildingLight for the no-HA part of the test."""
    light_mod = _load_companion_module("light")
    device = {
        "id": "10.10.1.30-0" if device_type == "relay" else "10.10.1.40-0",
        "name": "Keuken LED" if device_type == "relay" else "Zithoek",
        "semantic_type": "light",
        "device_type": device_type,
        "module_id": "00:24:77:52:ac:be",
        "module_ip": "10.10.1.30" if device_type == "relay" else "10.10.1.40",
    }
    coordinator = MagicMock()
    coordinator.module_for_channel.return_value = None
    coordinator.async_send_command = AsyncMock()
    return light_mod.IPBuildingLight(device, coordinator)


def _make_switch(*, device_type: str = "relay"):
    switch_mod = _load_companion_module("switch")
    device = {
        "id": "10.10.1.30-1" if device_type == "relay" else "10.10.1.40-1",
        "name": "Patio" if device_type == "relay" else "Ventilator",
        "semantic_type": "switch" if device_type == "relay" else "fan",
        "device_type": device_type,
        "module_id": "00:24:77:52:ac:be",
        "module_ip": "10.10.1.30" if device_type == "relay" else "10.10.1.40",
    }
    coordinator = MagicMock()
    coordinator.module_for_channel.return_value = None
    coordinator.async_send_command = AsyncMock()
    return switch_mod.IPBuildingSwitch(device, coordinator)


# ---------------------------------------------------------------------------
# light
# ---------------------------------------------------------------------------


class TestLightStartupState:
    def test_unknown_state_maps_to_none(self):
        light = _make_light()
        light._update_from_state({"state": "unknown"})
        assert light._attr_is_on is None

    def test_inactive_state_maps_to_none(self):
        light = _make_light()
        light._update_from_state({"state": "inactive"})
        assert light._attr_is_on is None

    def test_missing_state_maps_to_none(self):
        light = _make_light()
        light._update_from_state({})
        assert light._attr_is_on is None

    def test_on_state_maps_to_true(self):
        light = _make_light()
        light._update_from_state({"state": "on"})
        assert light._attr_is_on is True

    def test_off_state_maps_to_false(self):
        light = _make_light()
        light._update_from_state({"state": "off"})
        assert light._attr_is_on is False

    def test_ON_state_maps_to_true(self):
        # Legacy wire shape uses uppercase
        light = _make_light()
        light._update_from_state({"state": "ON"})
        assert light._attr_is_on is True

    def test_relay_stays_onoff_without_level(self):
        try:
            from homeassistant.components.light import ColorMode
        except ModuleNotFoundError:
            pytest.skip("homeassistant.components.light not available")

        light = _make_light(device_type="relay")
        assert light._attr_supported_color_modes == {ColorMode.ONOFF}
        assert light._attr_color_mode == ColorMode.ONOFF


class TestDimmerColorModes:
    def test_dimmer_advertises_brightness_before_level(self):
        try:
            from homeassistant.components.light import ColorMode
        except ModuleNotFoundError:
            pytest.skip("homeassistant.components.light not available")

        light = _make_light(device_type="dimmer")
        assert light._attr_supported_color_modes == {ColorMode.BRIGHTNESS}
        assert light._attr_color_mode == ColorMode.BRIGHTNESS
        assert getattr(light, "_attr_brightness", None) is None

    def test_dimmer_unknown_state_keeps_brightness_mode(self):
        try:
            from homeassistant.components.light import ColorMode
        except ModuleNotFoundError:
            pytest.skip("homeassistant.components.light not available")

        light = _make_light(device_type="dimmer")
        light._update_from_state({"state": "unknown"})
        assert light._attr_is_on is None
        assert light._attr_supported_color_modes == {ColorMode.BRIGHTNESS}

    def test_dimmer_level_updates_brightness(self):
        light = _make_light(device_type="dimmer")
        light._update_from_state({"state": "on", "level": 40})
        assert light._attr_is_on is True
        assert light._attr_brightness == round(255 * 40 / 100)


class TestDimmerToggle:
    @pytest.mark.asyncio
    async def test_on_plain_toggle_sends_toggle(self):
        light = _make_light(device_type="dimmer")
        light._update_from_state({"state": "on", "level": 100})
        await light.async_toggle()
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "TOGGLE"
        )

    @pytest.mark.asyncio
    async def test_on_toggle_with_transition_sends_toggle(self):
        """HA may attach transition; that must not fall through to DIM 0."""
        light = _make_light(device_type="dimmer")
        light._update_from_state({"state": "on", "level": 100})
        await light.async_toggle(transition=1)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "TOGGLE"
        )

    @pytest.mark.asyncio
    async def test_off_plain_toggle_sends_toggle(self):
        light = _make_light(device_type="dimmer")
        light._update_from_state({"state": "off", "level": 0})
        await light.async_toggle()
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "TOGGLE"
        )

    @pytest.mark.asyncio
    async def test_off_toggle_with_brightness_sends_dim(self):
        light = _make_light(device_type="dimmer")
        light._update_from_state({"state": "off", "level": 0})
        await light.async_toggle(brightness=128)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "DIM", max(1, round(128 * 100 / 255))
        )

    @pytest.mark.asyncio
    async def test_unknown_state_sends_toggle_not_dim(self):
        light = _make_light(device_type="dimmer")
        light._update_from_state({"state": "unknown"})
        await light.async_toggle(transition=1)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "TOGGLE"
        )

    @pytest.mark.asyncio
    async def test_relay_toggle_does_not_send_toggle(self):
        light = _make_light(device_type="relay")
        light._update_from_state({"state": "on"})
        try:
            await light.async_toggle()
        except Exception:
            # LightEntity.async_toggle needs a full HA runtime.
            pass
        for call in light._coordinator.async_send_command.await_args_list:
            assert call.args[1] != "TOGGLE"

    def test_helper_ignores_transition_only(self):
        light_mod = _load_companion_module("light")
        assert light_mod._toggle_requests_explicit_on({"transition": 1}) is False
        assert light_mod._toggle_requests_explicit_on({}) is False
        assert light_mod._toggle_requests_explicit_on({"brightness": 0}) is False
        assert light_mod._toggle_requests_explicit_on({"brightness": 128}) is True
        assert light_mod._toggle_requests_explicit_on({"brightness_pct": 50}) is True


# ---------------------------------------------------------------------------
# switch
# ---------------------------------------------------------------------------


class TestSwitchStartupState:
    def test_unknown_state_maps_to_none(self):
        sw = _make_switch()
        sw._update_from_state({"state": "unknown"})
        assert sw._attr_is_on is None

    def test_inactive_state_maps_to_none(self):
        sw = _make_switch()
        sw._update_from_state({"state": "inactive"})
        assert sw._attr_is_on is None

    def test_missing_state_maps_to_none(self):
        sw = _make_switch()
        sw._update_from_state({})
        assert sw._attr_is_on is None

    def test_on_state_maps_to_true(self):
        sw = _make_switch()
        sw._update_from_state({"state": "on"})
        assert sw._attr_is_on is True

    def test_off_state_maps_to_false(self):
        sw = _make_switch()
        sw._update_from_state({"state": "off"})
        assert sw._attr_is_on is False


class TestDimmerSwitchToggle:
    @pytest.mark.asyncio
    async def test_dimmer_switch_toggle_sends_toggle(self):
        sw = _make_switch(device_type="dimmer")
        sw._update_from_state({"state": "on"})
        await sw.async_toggle()
        sw._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-1", "TOGGLE"
        )
