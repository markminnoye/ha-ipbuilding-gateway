"""Shared helpers for ipbuilding_gateway_ha entities.

Mirrors the HA-IPBuilding button pattern: channels with ``active: false`` in
``devices.json`` are registered in Home Assistant as **disabled and hidden by
default**, so the operator sees them in Instellingen → Apparaten & entiteiten
without them appearing on dashboards or in automations until enabled.
"""

from __future__ import annotations

from typing import Any


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
