"""Canonical 8-hex button ids.

Duplicated from the gateway ``button_id`` helper (no cross-repo import).
The four accepted forms collapse to the manufacturer's 4-byte IPA key:

- 16 hex (HTTP ``getButtons``, type byte + wire) → strip 2, then as 14
- 14 hex (UDP ``B…E`` wire) → ``s[0:6] + s[12:14]``
- 10 hex (legacy IPA-derived ``devices.json``) → ``s[0:8]``
- 8 hex (already canonical) → unchanged
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

_HEX = frozenset("0123456789abcdef")

# ``event_<hardware_id>`` unique_id prefix used by IPBuildingEventButton.
_EVENT_UNIQUE_PREFIX = "event_"


def canonical_button_id(raw: str) -> str | None:
    """Return the 8-hex canonical id, or None when the input is not a known form."""
    if not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    if not s or any(c not in _HEX for c in s):
        return None
    n = len(s)
    if n == 16:
        s = s[2:]
        n = 14
    if n == 14:
        return s[0:6] + s[12:14]
    if n == 10:
        return s[0:8]
    if n == 8:
        return s
    return None


def canonicalise_button_device(device: dict[str, Any]) -> dict[str, Any]:
    """Return ``device`` with a canonical button ``id`` when it is an input/button.

    Channel devices (relay/dimmer ids like ``10.10.1.30-0``) are returned
    unchanged. If ``canonical_button_id`` returns None, the original id is
    kept — never overwritten with None.
    """
    if not isinstance(device, dict):
        return device
    if device.get("device_type") != "input" and device.get("semantic_type") != "button":
        return device
    raw = device.get("id")
    if not raw:
        return device
    canonical = canonical_button_id(str(raw))
    if canonical is None or canonical == raw:
        return device
    updated = dict(device)
    updated["id"] = canonical
    return updated


def migrated_event_unique_id(unique_id: str) -> str | None:
    """Return ``event_<8 hex>`` when ``unique_id`` is ``event_<10 or 14 hex>``.

    Already-canonical (8-hex) ids, channel unique_ids, and non-hex values
    return None so the caller leaves the registry entry alone.
    """
    if not unique_id.startswith(_EVENT_UNIQUE_PREFIX):
        return None
    raw = unique_id[len(_EVENT_UNIQUE_PREFIX) :]
    if len(raw) not in (10, 14):
        return None
    canonical = canonical_button_id(raw)
    if canonical is None:
        return None
    return f"{_EVENT_UNIQUE_PREFIX}{canonical}"


def migrated_device_identifier(identifier: str) -> str | None:
    """Return the 8-hex id when ``identifier`` is a 10- or 14-hex button id."""
    if len(identifier) not in (10, 14):
        return None
    return canonical_button_id(identifier)


def apply_registry_migration(
    entity_registry: Any,
    device_registry: Any,
    *,
    config_entry_id: str,
    domain: str,
) -> None:
    """Rewrite 10-/14-hex button unique_ids and device identifiers to 8-hex.

    ``entity_id`` is never changed. Idempotent: already-canonical ids produce
    no registry writes, so a second run is a no-op.
    """
    entities = getattr(entity_registry, "entities", None)
    if entities is not None:
        for entity in list(entities.values()):
            if not _belongs_to_entry(entity, config_entry_id):
                continue
            unique_id = getattr(entity, "unique_id", "") or ""
            new_uid = migrated_event_unique_id(unique_id)
            if new_uid is None or new_uid == unique_id:
                continue
            try:
                entity_registry.async_update_entity(
                    entity.entity_id, new_unique_id=new_uid
                )
            except Exception:
                log.warning(
                    "Could not migrate unique_id %s → %s",
                    unique_id,
                    new_uid,
                    exc_info=True,
                )

    devices = getattr(device_registry, "devices", None)
    if devices is None:
        return
    for device in list(devices.values()):
        if not _device_belongs_to_entry(device, config_entry_id):
            continue
        identifiers = set(getattr(device, "identifiers", ()) or ())
        new_identifiers: set[tuple[str, str]] = set()
        changed = False
        for ident_domain, ident in identifiers:
            if ident_domain == domain:
                new_ident = migrated_device_identifier(ident)
                if new_ident is not None and new_ident != ident:
                    new_identifiers.add((ident_domain, new_ident))
                    changed = True
                    continue
            new_identifiers.add((ident_domain, ident))
        if not changed:
            continue
        try:
            device_registry.async_update_device(
                device.id, new_identifiers=new_identifiers
            )
        except Exception:
            log.warning(
                "Could not migrate device identifiers %s → %s",
                identifiers,
                new_identifiers,
                exc_info=True,
            )


def _belongs_to_entry(entity: Any, config_entry_id: str) -> bool:
    if getattr(entity, "config_entry_id", None) == config_entry_id:
        return True
    entries = getattr(entity, "config_entries", None)
    return bool(entries) and config_entry_id in entries


def _device_belongs_to_entry(device: Any, config_entry_id: str) -> bool:
    entries = getattr(device, "config_entries", None)
    if entries is not None:
        return config_entry_id in entries
    return getattr(device, "config_entry_id", None) == config_entry_id
