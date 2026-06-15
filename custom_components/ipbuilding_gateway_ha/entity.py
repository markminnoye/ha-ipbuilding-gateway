"""Shared helpers for ipbuilding_gateway_ha entities.

Mirrors the HA-IPBuilding button pattern: channels with ``active: false`` in
``devices.json`` are registered in Home Assistant as **disabled and hidden by
default**, so the operator sees them in Instellingen → Apparaten & entiteiten
without them appearing on dashboards or in automations until enabled.
"""

from __future__ import annotations

from typing import Any

from .const import DOMAIN


def apply_active_registry_defaults(entity: Any, device: dict[str, Any]) -> None:
    """Mark ``entity`` disabled+hidden-by-default if the gateway reports it inactive.

    The companion ``coordinator`` also keeps the registry in sync at runtime
    (see ``coordinator._reconcile_active``), but setting these class-level
    attributes here covers the initial ``async_setup_entry`` path for entities
    that are brand new to the entity registry.
    """
    if not device.get("active", True):
        entity._attr_entity_registry_enabled_default = False
        entity._attr_entity_registry_visible_default = False


def build_module_hub_device_info(module: dict[str, Any]) -> dict[str, Any]:
    """Build device_info for a physical field module (IP0200PoE / IP0300PoE / IP1100PoE).

    Used as the ``via_device`` target for channels that roll up to this module.
    The actual registration happens implicitly when the first channel with
    ``via_device=(DOMAIN, module["id"])`` is added to HA.
    """
    info: dict[str, Any] = {
        "identifiers": {(DOMAIN, module["id"])},  # MAC
        "name": module.get("name") or module.get("model") or "IPBuilding module",
        "manufacturer": "IPBuilding",
        "model": module.get("model") or module.get("type"),
    }
    firmware = module.get("firmware")
    if firmware:
        info["sw_version"] = firmware
    # The module-device rolls up to the gateway via hub.py's gateway_device_info.
    # We do not set via_device here; HA infers the chain from the per-entity
    # via_device on the channel pointing at (DOMAIN, module["id"]).
    return info


def build_channel_device_info(
    device: dict[str, Any], module: dict[str, Any] | None
) -> dict[str, Any]:
    """Build device_info for a channel/button/light/switch.

    Uses the parent module's product model (e.g. "IP0200PoE") so HA displays
    the correct hardware, not the semantic_type ("light"/"fan"/"switch").

    The ``via_device`` field automatically causes HA to create the parent
    module-device in the registry on first reference.
    """
    info: dict[str, Any] = {
        "identifiers": {(DOMAIN, device["id"])},
        "name": device.get("name", device["id"]),
        "manufacturer": "IPBuilding",
        "model": (module or {}).get("model") or (module or {}).get("type"),
    }
    if module and module.get("id"):
        info["via_device"] = (DOMAIN, module["id"])  # MAC -> module
    firmware = (module or {}).get("firmware")
    if firmware:
        info["sw_version"] = firmware
    if module and module.get("mac"):
        info["serial_number"] = module["mac"]
    return info
