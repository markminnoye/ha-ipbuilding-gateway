"""Sensor entity platform for IPBuilding Open.

Exposes:
- Power readings (``current_watt``) from channel state_changed events
- Gateway diagnostic status
- Per-module diagnostic sensors (model, firmware, last_seen by gateway)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfPower

from .const import DOMAIN
from .coordinator import IPBuildingCoordinator
from .entity import (
    apply_active_registry_defaults,
    build_channel_device_info,
    build_module_hub_device_info,
    module_device_model,
)
from .hub import gateway_device_info

log = logging.getLogger(__name__)

_STATUS_ICONS = {
    "ok": "mdi:check-circle",
    "degraded": "mdi:alert",
    "unhealthy": "mdi:alert-circle",
}


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp from the gateway into a tz-aware datetime."""
    if not value:
        return None
    text = value
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class IPBuildingGatewayStatusSensor(SensorEntity):
    """Diagnostic sensor for aggregate gateway health."""

    _attr_has_entity_name = True
    _attr_name = "Gateway status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "gateway_status"

    def __init__(self, entry: ConfigEntry, coordinator: IPBuildingCoordinator) -> None:
        self._entry = entry
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_gateway_status"
        self._attr_device_info = gateway_device_info(entry, coordinator)
        self._on_update: Callable[[dict[str, Any]], None] | None = None

    async def async_added_to_hass(self) -> None:
        self._update_from_status(self._coordinator.gateway_status)

        @callback
        def _listener(status: dict[str, Any]) -> None:
            self._update_from_status(status)
            self.async_write_ha_state()

        self._on_update = _listener
        self._coordinator.register_gateway_listener(_listener)

    async def async_will_remove_from_hass(self) -> None:
        if self._on_update is not None:
            self._coordinator.unregister_gateway_listener(self._on_update)

    def _update_from_status(self, status: dict[str, Any]) -> None:
        self._attr_native_value = status.get("status", "unknown")
        self._attr_icon = _STATUS_ICONS.get(str(self._attr_native_value), "mdi:help-circle")
        self._attr_extra_state_attributes = {
            "version": status.get("version"),
            "updated_at": status.get("updated_at"),
            "uptime_seconds": status.get("uptime_seconds"),
            "subsystems": status.get("subsystems"),
            "issues": status.get("issues"),
        }
        if status.get("version"):
            self._attr_device_info = gateway_device_info(self._entry, self._coordinator)


class IPBuildingModuleSensor(SensorEntity):
    """Diagnostic sensor attached to a physical field module (Tier 2)."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: IPBuildingCoordinator,
        module: dict[str, Any],
        *,
        kind: str,
        translation_key: str,
        icon: str,
        device_class: SensorDeviceClass | None = None,
    ) -> None:
        self._entry = entry
        self._coordinator = coordinator
        self._mac = module["id"]
        self._kind = kind
        self._attr_unique_id = f"{self._mac}_{kind}"
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        if device_class is not None:
            self._attr_device_class = device_class
        self._attr_device_info = self._device_info_for(module)
        self._on_modules: Callable[[dict[str, dict[str, Any]]], None] | None = None
        self._apply_module(module)

    def _device_info_for(self, module: dict[str, Any]) -> dict[str, Any]:
        info = build_module_hub_device_info(module)
        info["via_device"] = (DOMAIN, self._entry.entry_id)
        return info

    async def async_added_to_hass(self) -> None:
        @callback
        def _listener(modules: dict[str, dict[str, Any]]) -> None:
            module = modules.get(self._mac)
            if module is None:
                return
            self._apply_module(module)
            self.async_write_ha_state()

        self._on_modules = _listener
        self._coordinator.register_module_listener(_listener)

    async def async_will_remove_from_hass(self) -> None:
        if self._on_modules is not None:
            self._coordinator.unregister_module_listener(self._on_modules)

    def _apply_module(self, module: dict[str, Any]) -> None:
        self._attr_device_info = self._device_info_for(module)
        if self._kind == "model":
            self._attr_native_value = (
                module_device_model(module) or module.get("type") or None
            )
        elif self._kind == "firmware":
            self._attr_native_value = module.get("firmware") or None
        elif self._kind == "last_seen":
            self._attr_native_value = _parse_iso_timestamp(module.get("last_seen"))
            source = module.get("last_seen_source") or None
            self._attr_extra_state_attributes = (
                {"source": source} if source else {}
            )


def _make_module_sensors(
    entry: ConfigEntry,
    coordinator: IPBuildingCoordinator,
    module: dict[str, Any],
) -> list[IPBuildingModuleSensor]:
    """Create the three diagnostic sensors for one module."""
    return [
        IPBuildingModuleSensor(
            entry,
            coordinator,
            module,
            kind="model",
            translation_key="module_model",
            icon="mdi:chip",
        ),
        IPBuildingModuleSensor(
            entry,
            coordinator,
            module,
            kind="firmware",
            translation_key="module_firmware",
            icon="mdi:memory",
        ),
        IPBuildingModuleSensor(
            entry,
            coordinator,
            module,
            kind="last_seen",
            translation_key="module_last_seen",
            icon="mdi:clock-check-outline",
            device_class=SensorDeviceClass.TIMESTAMP,
        ),
    ]


def _make_power_description(device: dict[str, Any]) -> SensorEntityDescription:
    """Build a SensorEntityDescription for a power sensor."""
    # ``original_icon`` was removed from ``EntityDescription`` in
    # Home Assistant 2026.3. The icon is set as a class attribute on the
    # entity itself in IPBuildingPowerSensor.
    # name="Power" + _attr_has_entity_name=True makes HA derive the displayed
    # name from the device registry name (e.g. "achterdeur_licht"), giving
    # "achterdeur_licht Power" → sensor.achterdeur_licht_power. Embedding
    # the device name here (as a previous version did) caused it to be
    # appended twice.
    return SensorEntityDescription(
        key=f"{device['id']}_power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=None,
    )


class IPBuildingPowerSensor(SensorEntity):
    """A power sensor reporting current_watt from the gateway.

    Updated whenever the gateway emits a state_changed event for the
    associated entity_id.
    """

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER

    def __init__(
        self,
        device: dict[str, Any],
        coordinator: IPBuildingCoordinator,
    ) -> None:
        self._device = device
        self._coordinator = coordinator
        self._entity_id = device["id"]
        self._attr_unique_id = f"{device['id']}_power"
        # Power sensor rolls up to the same parent module as the light/switch
        # for this channel. Use the helper so the model and via_device chain
        # stay in sync.
        module = coordinator.module_for_channel(device)
        self._attr_device_info = build_channel_device_info(device, module)
        self.entity_description = _make_power_description(device)
        self._attr_icon = "mdi:flash"
        self._on_update: Callable[[dict], None] | None = None
        apply_active_registry_defaults(self, device)

    async def async_added_to_hass(self) -> None:
        """Register for updates from the coordinator."""
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
        """Update the sensor value from a gateway state_changed message."""
        self._attr_native_value = state.get("current_watt", 0)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up power and diagnostic sensor entities from a config entry."""
    coordinator: IPBuildingCoordinator = hass.data[DOMAIN][entry.entry_id]

    hub_entities = [
        IPBuildingGatewayStatusSensor(entry, coordinator),
    ]
    async_add_entities(hub_entities)

    known_module_macs: set[str] = set()

    def _add_module_sensors(modules: dict[str, dict[str, Any]]) -> None:
        new_sensors: list[IPBuildingModuleSensor] = []
        for mac, module in modules.items():
            if not mac or mac in known_module_macs:
                continue
            known_module_macs.add(mac)
            new_sensors.extend(_make_module_sensors(entry, coordinator, module))
        if new_sensors:
            async_add_entities(new_sensors)

    _add_module_sensors(coordinator.modules)
    coordinator.register_module_listener(_add_module_sensors)

    devices = coordinator.devices_snapshot()

    seen_unique_ids: set[str] = set()

    def _add(devices_to_add: list[dict]) -> None:
        new_sensors = []
        for device in devices_to_add:
            if device.get("device_type") not in ("relay", "dimmer"):
                continue
            sensor = IPBuildingPowerSensor(device, coordinator)
            if sensor._attr_unique_id in seen_unique_ids:
                continue
            seen_unique_ids.add(sensor._attr_unique_id)
            new_sensors.append(sensor)
        for sensor in new_sensors:
            coordinator.track_platform_entity("sensor", sensor._entity_id, sensor)
        if new_sensors:
            async_add_entities(new_sensors)

    # Initial setup: also through _add so a subsequent flip-to-active
    # device doesn't try to recreate an already-registered power sensor.
    _add(devices)

    coordinator.register_platform("sensor", _add)
