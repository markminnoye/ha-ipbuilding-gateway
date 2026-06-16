"""Device automation triggers for IPBuilding physical buttons.

Surfaces a native "Button pressed" trigger in the Home Assistant
automation editor for every IP1100PoE button device. The trigger is
backed by the ``ipbuilding_gateway_ha.button_pressed`` bus event that
:class:`button.IPBuildingEventButton` already fires, filtered to the
button's hardware id so each device only reacts to its own press.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.event import DOMAIN as EVENT_DOMAIN
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

TRIGGER_TYPE_PRESSED = "pressed"
TRIGGER_TYPES = {TRIGGER_TYPE_PRESSED}

#: HA bus event fired by IPBuildingEventButton on a physical button press.
EVENT_BUTTON_PRESSED = f"{DOMAIN}.button_pressed"

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES)}
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """Return the list of device triggers for an IPBuilding button device.

    Only devices that own an ``event`` entity from this integration (i.e.
    IP1100PoE physical buttons) get a trigger; relay/dimmer channel devices
    are skipped.
    """
    ent_reg = er.async_get(hass)
    is_button = any(
        entry.domain == EVENT_DOMAIN and entry.platform == DOMAIN
        for entry in er.async_entries_for_device(
            ent_reg, device_id, include_disabled_entities=True
        )
    )
    if not is_button:
        return []
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: TRIGGER_TYPE_PRESSED,
        }
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a device trigger, backed by the button_pressed bus event."""
    hardware_id = _hardware_id_for_device(hass, config[CONF_DEVICE_ID])
    event_data = {"hardware_id": hardware_id} if hardware_id else {}
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_BUTTON_PRESSED,
            event_trigger.CONF_EVENT_DATA: event_data,
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )


def _hardware_id_for_device(hass: HomeAssistant, device_id: str) -> str | None:
    """Resolve a button device's hardware id from its ``(DOMAIN, id)`` identifier.

    The Tier-3 button device is registered with ``identifiers={(DOMAIN,
    hardware_id)}`` and ``IPBuildingEventButton`` fires the bus event with the
    same ``hardware_id``, so the identifier is the routing key.
    """
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for domain, identifier in device.identifiers:
        if domain == DOMAIN:
            return identifier
    return None
