"""Button entity platform for IPBuilding Open.

Exposes physical buttons on IP1100PoE modules as HA EventEntity
instances. Each button press from the gateway triggers a
`button_pressed` event in Home Assistant.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.components.event import EventEntity, EventEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import IPBuildingCoordinator
from .entity import build_channel_device_info
from .hub import gateway_device_info

log = logging.getLogger(__name__)

_BUTTON_EVENT_TYPES = ["press"]


class IPBuildingEventButton(EventEntity):
    """A hardware button exposed as a Home Assistant EventEntity.

    Fires ``ipbuilding_gateway_ha.button_pressed`` events when the gateway
    receives a button press from the IP1100PoE.
    """

    _attr_has_entity_name = True
    _attr_event_types = _BUTTON_EVENT_TYPES

    def __init__(
        self,
        hardware_id: str,
        name: str | None,
        coordinator: IPBuildingCoordinator,
        device_info: dict[str, Any],
    ) -> None:
        self._hardware_id = hardware_id
        self._coordinator = coordinator
        self._attr_unique_id = f"event_{hardware_id}"
        self._attr_device_info = device_info
        self.entity_description = EventEntityDescription(
            name=name or f"Button {hardware_id}",
            event_types=_BUTTON_EVENT_TYPES,
            translation_key="button",
            translation_placeholders={"hardware_id": hardware_id},
        )
        self._on_button_event: Callable[[dict], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Register to receive button events from the coordinator."""
        listener_key = f"button:{self._hardware_id}"

        @callback
        def callback(data: dict) -> None:
            self.async_trigger_event(
                "button_pressed",
                {"hardware_id": self._hardware_id, "action": data.get("action", "press")},
            )

        self._on_button_event = callback
        self._coordinator.register_entity(listener_key, callback)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister the button event listener."""
        if self._on_button_event is not None:
            self._coordinator.unregister_entity(
                f"button:{self._hardware_id}", self._on_button_event
            )


class IPBuildingDiscoverButton(ButtonEntity):
    """Trigger a forced discovery sweep on the gateway."""

    _attr_has_entity_name = True
    _attr_name = "Run discovery sweep"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "discover_sweep"
    _attr_icon = "mdi:radar"

    def __init__(self, entry: ConfigEntry, coordinator: IPBuildingCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_discover"
        self._attr_device_info = gateway_device_info(entry, coordinator)

    async def async_press(self) -> None:
        """Run POST /api/v1/discover on the gateway."""
        await self._coordinator.async_trigger_discover()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button/event entities from a config entry.

    Creates an IPBuildingEventButton for each entry in devices.json that
    represents a physical button (type=input on IP1100PoE).
    """
    coordinator: IPBuildingCoordinator = hass.data[DOMAIN][entry.entry_id]
    devices = coordinator.data if isinstance(coordinator.data, dict) else {}

    async_add_entities([IPBuildingDiscoverButton(entry, coordinator)])

    buttons = []
    for entity_id, device in devices.items():
        # Only create buttons for input channels.
        device_type = device.get("device_type")
        if device_type == "input":
            hardware_id = device["id"]
            name = device.get("name")
            # 3-tier device tree: button is a channel on the IP1100PoE input
            # module. Uses the shared helper so model and via_device chain are
            # consistent with light/switch/sensor. The helper falls back to
            # `type` when no parent module is in the cache, which is fine
            # while companion #4 (button→action wizard) is not yet shipped.
            module = coordinator.module_for_channel(device)
            device_info = build_channel_device_info(device, module)
            buttons.append(IPBuildingEventButton(hardware_id, name, coordinator, device_info))

    async_add_entities(buttons)