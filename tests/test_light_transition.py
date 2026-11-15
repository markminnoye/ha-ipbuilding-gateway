"""Unit tests for Home Assistant transition -> gateway fade support."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ha = pytest.importorskip("homeassistant")
try:
    from homeassistant.components.light import LightEntityFeature
except ModuleNotFoundError:
    pytest.skip(
        "homeassistant.components.light not available",
        allow_module_level=True,
    )

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
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    for dep in ("const", "coordinator", "entity", "hub"):
        _load(dep)
    return _load(name)


def _make_light(*, device_type: str = "dimmer"):
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
    coordinator.async_send_command = AsyncMock(return_value=True)
    return light_mod, light_mod.IPBuildingLight(device, coordinator)


def _make_real_coordinator():
    coord_mod = _load_companion_module("coordinator")
    coord = coord_mod.IPBuildingCoordinator.__new__(coord_mod.IPBuildingCoordinator)
    coord._ws = MagicMock()
    coord._ws.send_json = AsyncMock()
    coord._ws_connected = asyncio.Event()
    coord._ws_connected.set()
    return coord


class TestDimmerSupportedFeatures:
    def test_dimmer_supports_transition(self):
        _, light = _make_light(device_type="dimmer")
        assert light.supported_features & LightEntityFeature.TRANSITION

    def test_relay_does_not_support_transition(self):
        _, light = _make_light(device_type="relay")
        assert not (light.supported_features & LightEntityFeature.TRANSITION)


class TestTransitionToFade:
    def test_provisional_linear_mapping(self):
        light_mod, _ = _make_light(device_type="dimmer")
        assert light_mod.transition_to_fade(0.2) == 1
        assert light_mod.transition_to_fade(1.0) == 5
        assert light_mod.transition_to_fade(2.0, from_level=0, to_level=100) == 10

    def test_clamps_to_zero_for_zero_or_negative(self):
        light_mod, _ = _make_light(device_type="dimmer")
        assert light_mod.transition_to_fade(0.0) == 0
        assert light_mod.transition_to_fade(-3.5) == 0

    def test_clamps_to_255_for_large_transitions(self):
        light_mod, _ = _make_light(device_type="dimmer")
        assert light_mod.transition_to_fade(51.0) == 255
        assert light_mod.transition_to_fade(300.0) == 255


class TestLightTransitionCommands:
    @pytest.mark.asyncio
    async def test_dimmer_turn_on_with_transition_passes_fade(self):
        _, light = _make_light(device_type="dimmer")
        light._update_from_state({"state": "off", "level": 0})
        await light.async_turn_on(brightness=128, transition=2.0)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "DIM", max(1, round(128 * 100 / 255)), fade=10
        )

    @pytest.mark.asyncio
    async def test_dimmer_turn_on_with_zero_transition_passes_fade_zero(self):
        _, light = _make_light(device_type="dimmer")
        await light.async_turn_on(brightness=255, transition=0)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "DIM", 100, fade=0
        )

    @pytest.mark.asyncio
    async def test_dimmer_turn_on_without_transition_omits_fade(self):
        _, light = _make_light(device_type="dimmer")
        await light.async_turn_on(brightness=255)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "DIM", 100
        )

    @pytest.mark.asyncio
    async def test_dimmer_turn_off_with_transition_passes_fade(self):
        _, light = _make_light(device_type="dimmer")
        light._update_from_state({"state": "on", "level": 80})
        await light.async_turn_off(transition=3.0)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "DIM", 0, fade=15
        )

    @pytest.mark.asyncio
    async def test_dimmer_turn_off_without_transition_omits_fade(self):
        _, light = _make_light(device_type="dimmer")
        await light.async_turn_off()
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "DIM", 0
        )

    @pytest.mark.asyncio
    async def test_relay_ignores_transition(self):
        _, light = _make_light(device_type="relay")
        await light.async_turn_on(transition=2.0)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.30-0", "ON"
        )
        light._coordinator.async_send_command.reset_mock()
        await light.async_turn_off(transition=2.0)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.30-0", "OFF"
        )


class TestCoordinatorFadePayload:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action", ["DIM", "ON", "OFF"])
    async def test_fade_included_for_fade_actions(self, action: str):
        coord = _make_real_coordinator()
        ok = await coord.async_send_command(
            "10.10.1.40-0", action, 50 if action == "DIM" else None, fade=12
        )
        assert ok is True
        sent = coord._ws.send_json.await_args.args[0]
        assert sent["fade"] == 12

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action", ["TOGGLE", "DIM_START", "DIM_STOP"])
    async def test_fade_omitted_for_non_fade_actions(self, action: str):
        coord = _make_real_coordinator()
        ok = await coord.async_send_command("10.10.1.40-0", action, fade=12)
        assert ok is True
        sent = coord._ws.send_json.await_args.args[0]
        assert "fade" not in sent

    @pytest.mark.asyncio
    async def test_fade_omitted_when_none(self):
        coord = _make_real_coordinator()
        ok = await coord.async_send_command("10.10.1.40-0", "DIM", 75)
        assert ok is True
        sent = coord._ws.send_json.await_args.args[0]
        assert sent == {"type": "command", "id": "10.10.1.40-0", "action": "DIM", "value": 75}

    @pytest.mark.asyncio
    async def test_bool_fade_rejected(self):
        coord = _make_real_coordinator()
        with pytest.raises(ValueError):
            await coord.async_send_command("10.10.1.40-0", "DIM", 50, fade=True)


class TestDefaultTransitionFallback:
    @pytest.mark.asyncio
    async def test_dimmer_uses_coordinator_default_transition_when_omitted(self):
        _, light = _make_light(device_type="dimmer")
        light._coordinator.default_transition = 6.0
        await light.async_turn_on(brightness=255)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "DIM", 100, fade=30
        )
        light._coordinator.async_send_command.reset_mock()
        await light.async_turn_off()
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "DIM", 0, fade=30
        )

    @pytest.mark.asyncio
    async def test_explicit_zero_overrides_default_transition(self):
        _, light = _make_light(device_type="dimmer")
        light._coordinator.default_transition = 6.0
        await light.async_turn_on(brightness=255, transition=0)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "DIM", 100, fade=0
        )

    @pytest.mark.asyncio
    async def test_zero_default_transition_omits_fade(self):
        _, light = _make_light(device_type="dimmer")
        light._coordinator.default_transition = 0.0
        await light.async_turn_on(brightness=255)
        light._coordinator.async_send_command.assert_awaited_once_with(
            "10.10.1.40-0", "DIM", 100
        )

    def test_coordinator_default_transition_property(self):
        coord = _make_real_coordinator()
        coord._entry = MagicMock()
        coord._entry.options = {}
        assert coord.default_transition == 6.0

        coord._entry.options = {"default_transition": 2.4}
        assert coord.default_transition == 2.4

        coord._entry.options = {"default_transition": 999.0}
        assert coord.default_transition == 51.0

        coord._entry.options = {"default_transition": -1.0}
        assert coord.default_transition == 0.0

        coord._entry.options = {"default_transition": "bad"}
        assert coord.default_transition == 6.0
