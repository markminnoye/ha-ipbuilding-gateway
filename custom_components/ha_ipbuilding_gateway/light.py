"""Light entity platform for IPBuilding Open.

Exposes relay channels as ONOFF lights and dimmer channels as
BRIGHTNESS lights based on the semantic_type in devices.json.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SEMANTIC_TYPE_LIGHT
from .coordinator import IPBuildingCoordinator
from .entity import apply_active_registry_defaults, build_channel_device_info, entity_icon

log = logging.getLogger(__name__)

# Key in devices.json that indicates a light
_LIGHT_SEMANTIC_TYPES = {SEMANTIC_TYPE_LIGHT}

# HA service-data keys that mean "turn on at this level/colour", not native
# TOGGLE. ``transition`` is intentionally absent: HA may attach it to every
# ``light.toggle``, and the IP0300PoE has no per-command fade duration on
# UDP/1001 (EEPROM Soft AAN/UIT applies to ``S``/``C`` only).
_TOGGLE_EXPLICIT_ON_KEYS = (
    "brightness",
    "brightness_pct",
    "rgb_color",
    "hs_color",
    "xy_color",
    "rgbw_color",
    "rgbww_color",
    "color_temp",
    "color_temp_kelvin",
    "kelvin",
    "white",
    "effect",
    "profile",
    "flash",
)
_ZERO_MEANS_OFF = frozenset({"brightness", "brightness_pct", "white"})


def _toggle_requests_explicit_on(kwargs: dict[str, Any]) -> bool:
    """True when HA toggle should turn on at a given level/color, not native TOGGLE."""
    for key in _TOGGLE_EXPLICIT_ON_KEYS:
        if key not in kwargs:
            continue
        value = kwargs[key]
        if key in _ZERO_MEANS_OFF and not value:
            continue
        return True
    return False


class IPBuildingLight(LightEntity):
    """A light entity backed by the IPBuilding Gateway via WebSocket."""

    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes: set[ColorMode] = {ColorMode.ONOFF}
    _attr_is_on: bool | None = None

    def __init__(
        self,
        device: dict[str, Any],
        coordinator: IPBuildingCoordinator,
    ) -> None:
        self._device = device
        self._coordinator = coordinator
        self._entity_id = device["id"]
        self._semantic_type: str = device.get("semantic_type", "light")
        # Dimmer modules use DIM commands on the gateway; relays use ON/OFF.
        # Advertise BRIGHTNESS at construct time — HA caches
        # supported_color_modes at registration. Waiting for the first
        # ``level`` (old behaviour) hid the slider whenever status-poll
        # never returned a level (seen on older 0–10V modules).
        self._is_dimmer: bool = device.get("device_type") == "dimmer"
        if self._is_dimmer:
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_unique_id = device["id"]
        # 3-tier device tree: channel rolls up to its parent module via
        # via_device. Module-device is created implicitly by HA on first
        # reference. The module's product model (e.g. "IP0200PoE") takes
        # priority over the channel's semantic_type (e.g. "light").
        module = coordinator.module_for_channel(device)
        self._attr_device_info = build_channel_device_info(device, module)
        # Entity description: name=None + has_entity_name=True makes HA derive
        # the displayed name from the device name in the device registry.
        # ``original_icon`` was removed from ``EntityDescription`` in
        # Home Assistant 2026.3 — set the icon as a class attribute instead.
        self.entity_description = LightEntityDescription(
            key=device["id"],
            name=None,
        )
        self._attr_icon = entity_icon(device)
        # Store the update callback so the entity can be notified
        self._on_update: Callable[[dict], None] | None = None
        apply_active_registry_defaults(self, device)

    async def async_added_to_hass(self) -> None:
        """Register for updates from the coordinator."""
        # Set initial state from coordinator cache
        state = self._coordinator.get_device_state(self._entity_id)
        if state:
            self._update_from_state(state)

        def callback(data: dict) -> None:
            self._update_from_state(data)
            self.async_write_ha_state()

        self._on_update = callback
        self._coordinator.register_entity(self._entity_id, callback)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister the update callback."""
        if self._on_update is not None:
            self._coordinator.unregister_entity(self._entity_id, self._on_update)

    def _update_from_state(self, state: dict) -> None:
        """Update entity state from a gateway state_changed message."""
        raw = state.get("state")
        # Map gateway state to HA: anything other than a real on/off
        # must surface as None so HA shows "Unknown" instead of
        # silently turning the light off. The gateway returns
        # "unknown" right after a restart before the HTTP
        # ``statuses`` hydration lands, and "inactive" for channels
        # disabled in devices.json.
        if raw in (None, "unknown", "inactive"):
            self._attr_is_on = None
        else:
            self._attr_is_on = raw in ("on", "ON")

        # Dimmer-specific: keep brightness in sync. Color modes are set
        # in ``__init__`` (BRIGHTNESS only — HA 2026.3 rejects mixing
        # BRIGHTNESS with ONOFF). Level may be absent after a restart.
        if self._is_dimmer and "level" in state:
            level = state.get("level")
            if level is not None:
                self._attr_brightness = round(255 * level / 100)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        if self._is_dimmer:
            brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness)
            if not brightness:
                level = 100
            else:
                level = max(1, round(brightness * 100 / 255))
            await self._coordinator.async_send_command(
                self._entity_id, "DIM", level
            )
            return
        await self._coordinator.async_send_command(self._entity_id, "ON")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        if self._is_dimmer:
            await self._coordinator.async_send_command(self._entity_id, "DIM", 0)
            return
        await self._coordinator.async_send_command(self._entity_id, "OFF")

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the light.

        Dimmer channels have a native wire toggle (``T<ch>991000``) that flips
        between off and the module's *own* last-level memory — matching the
        physical IPBuilding wall-button (short press). A plain ``light.toggle``
        always uses that frame, even when HA attaches unused params such as
        ``transition``. ``turn_off`` / slider-to-zero stay on ``DIM 0``.

        Exception: a toggle that asks to come *on* at an explicit brightness
        or colour uses ``DIM`` instead of the module's last-level memory.
        Relays fall back to HA's default on/off toggle. Unknown dimmer state
        (``is_on is None``) also uses native ``TOGGLE``.
        """
        if not self._is_dimmer:
            await super().async_toggle(**kwargs)
            return
        if self.is_on is False and _toggle_requests_explicit_on(kwargs):
            await self.async_turn_on(**kwargs)
            return
        await self._coordinator.async_send_command(self._entity_id, "TOGGLE")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up light entities from a config entry."""
    coordinator: IPBuildingCoordinator = hass.data[DOMAIN][entry.entry_id]
    # ``devices_snapshot()`` returns a list and works on every code path:
    # REST fallback (list before v0.3.8), the dict cached after REST, and
    # the WebSocket snapshot. Reading ``coordinator.data`` directly would
    # diverge between those paths and silently create zero entities on
    # first refresh.
    devices = coordinator.devices_snapshot()

    # Track unique_ids we've already added to HA. Re-firing ``async_add_entities``
    # with the same unique_id makes Home Assistant log
    # "does not generate unique IDs" and silently drop the new entity — which
    # happens whenever a previously-inactive channel flips back to active.
    seen_unique_ids: set[str] = set()

    def _add(devices_to_add: list[dict]) -> None:
        new_lights = []
        for device in devices_to_add:
            if device.get("semantic_type") not in _LIGHT_SEMANTIC_TYPES:
                continue
            light = IPBuildingLight(device, coordinator)
            if light._attr_unique_id in seen_unique_ids:
                continue
            seen_unique_ids.add(light._attr_unique_id)
            new_lights.append(light)
        for light in new_lights:
            coordinator.track_platform_entity("light", light._entity_id, light)
        if new_lights:
            async_add_entities(new_lights)

    # Initial setup: also through _add so a subsequent flip-to-active
    # for one of these devices doesn't try to recreate them.
    _add(devices)

    coordinator.register_platform("light", _add)