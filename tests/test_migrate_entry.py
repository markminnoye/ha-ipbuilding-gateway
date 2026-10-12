"""Tests for config-entry version 2 button-id registry migration."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_COMP_DIR = _REPO / "custom_components" / "ha_ipbuilding_gateway"

_pkg = sys.modules.get("ha_ipbuilding_gateway")
if not isinstance(_pkg, types.ModuleType) or not hasattr(_pkg, "__path__"):
    _pkg = types.ModuleType("ha_ipbuilding_gateway")
    sys.modules["ha_ipbuilding_gateway"] = _pkg
_pkg.__path__ = [str(_COMP_DIR)]  # type: ignore[attr-defined]

_spec = importlib.util.spec_from_file_location(
    "ha_ipbuilding_gateway.button_id", _COMP_DIR / "button_id.py"
)
_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)  # type: ignore[union-attr]

apply_registry_migration = _module.apply_registry_migration
migrated_event_unique_id = _module.migrated_event_unique_id
migrated_device_identifier = _module.migrated_device_identifier

DOMAIN = "ha_ipbuilding_gateway"
ENTRY_ID = "config-entry-1"


class _Entity:
    def __init__(self, entity_id: str, unique_id: str, config_entry_id: str) -> None:
        self.entity_id = entity_id
        self.unique_id = unique_id
        self.config_entry_id = config_entry_id


class _EntityRegistry:
    def __init__(self, entries: list[_Entity]) -> None:
        self.entities = {e.entity_id: e for e in entries}
        self.updates: list[tuple[str, dict[str, Any]]] = []

    def async_update_entity(self, entity_id: str, **kwargs: Any) -> None:
        if "new_entity_id" in kwargs:
            raise AssertionError("migration must not touch entity_id")
        self.updates.append((entity_id, dict(kwargs)))
        entity = self.entities[entity_id]
        if "new_unique_id" in kwargs:
            entity.unique_id = kwargs["new_unique_id"]


class _Device:
    def __init__(
        self,
        device_id: str,
        identifiers: set[tuple[str, str]],
        config_entry_id: str,
    ) -> None:
        self.id = device_id
        self.identifiers = set(identifiers)
        self.config_entries = {config_entry_id}


class _DeviceRegistry:
    def __init__(self, entries: list[_Device]) -> None:
        self.devices = {d.id: d for d in entries}
        self.updates: list[tuple[str, dict[str, Any]]] = []

    def async_update_device(self, device_id: str, **kwargs: Any) -> None:
        self.updates.append((device_id, dict(kwargs)))
        device = self.devices[device_id]
        if "new_identifiers" in kwargs:
            device.identifiers = set(kwargs["new_identifiers"])


def _registries() -> tuple[_EntityRegistry, _DeviceRegistry]:
    ent_reg = _EntityRegistry(
        [
            _Entity("event.dac46cc330", "event_dac46cc330", ENTRY_ID),  # 10-hex
            _Entity(
                "event.2f8185190000df", "event_2f8185190000df", ENTRY_ID
            ),  # 14-hex
            _Entity("event.dac46cc3", "event_dac46cc3", ENTRY_ID),  # already 8
            _Entity("light.keuken", "10.10.1.30-0", ENTRY_ID),  # channel
            _Entity("event.other_install", "event_aaaaaaaaaa", "other-entry"),
        ]
    )
    dev_reg = _DeviceRegistry(
        [
            _Device("dev-10", {(DOMAIN, "dac46cc330")}, ENTRY_ID),
            _Device("dev-14", {(DOMAIN, "2f8185190000df")}, ENTRY_ID),
            _Device("dev-8", {(DOMAIN, "dac46cc3")}, ENTRY_ID),
            _Device("dev-relay", {(DOMAIN, "10.10.1.30-0")}, ENTRY_ID),
            _Device(
                "dev-module",
                {(DOMAIN, "00:24:77:52:ad:aa")},
                ENTRY_ID,
            ),
        ]
    )
    return ent_reg, dev_reg


def test_migrated_event_unique_id_only_10_and_14() -> None:
    assert migrated_event_unique_id("event_dac46cc330") == "event_dac46cc3"
    assert migrated_event_unique_id("event_2f8185190000df") == "event_2f8185df"
    assert migrated_event_unique_id("event_dac46cc3") is None
    assert migrated_event_unique_id("10.10.1.30-0") is None
    assert migrated_event_unique_id("event_nothex") is None


def test_migrated_device_identifier_only_10_and_14() -> None:
    assert migrated_device_identifier("dac46cc330") == "dac46cc3"
    assert migrated_device_identifier("2f8185190000df") == "2f8185df"
    assert migrated_device_identifier("dac46cc3") is None
    assert migrated_device_identifier("10.10.1.30-0") is None
    assert migrated_device_identifier("00:24:77:52:ad:aa") is None


def test_migrate_entry_rewrites_10_and_14_hex_keeps_entity_id() -> None:
    ent_reg, dev_reg = _registries()
    apply_registry_migration(
        ent_reg, dev_reg, config_entry_id=ENTRY_ID, domain=DOMAIN
    )

    ten = ent_reg.entities["event.dac46cc330"]
    assert ten.entity_id == "event.dac46cc330"
    assert ten.unique_id == "event_dac46cc3"

    fourteen = ent_reg.entities["event.2f8185190000df"]
    assert fourteen.entity_id == "event.2f8185190000df"
    assert fourteen.unique_id == "event_2f8185df"

    eight = ent_reg.entities["event.dac46cc3"]
    assert eight.unique_id == "event_dac46cc3"
    assert eight.entity_id == "event.dac46cc3"

    channel = ent_reg.entities["light.keuken"]
    assert channel.unique_id == "10.10.1.30-0"

    other = ent_reg.entities["event.other_install"]
    assert other.unique_id == "event_aaaaaaaaaa"

    assert dev_reg.devices["dev-10"].identifiers == {(DOMAIN, "dac46cc3")}
    assert dev_reg.devices["dev-14"].identifiers == {(DOMAIN, "2f8185df")}
    assert dev_reg.devices["dev-8"].identifiers == {(DOMAIN, "dac46cc3")}
    assert dev_reg.devices["dev-relay"].identifiers == {(DOMAIN, "10.10.1.30-0")}
    assert dev_reg.devices["dev-module"].identifiers == {
        (DOMAIN, "00:24:77:52:ad:aa")
    }

    for _entity_id, kwargs in ent_reg.updates:
        assert "new_entity_id" not in kwargs
        assert "new_unique_id" in kwargs


def test_migrate_entry_second_run_is_noop() -> None:
    ent_reg, dev_reg = _registries()
    apply_registry_migration(
        ent_reg, dev_reg, config_entry_id=ENTRY_ID, domain=DOMAIN
    )
    n_ent = len(ent_reg.updates)
    n_dev = len(dev_reg.updates)

    apply_registry_migration(
        ent_reg, dev_reg, config_entry_id=ENTRY_ID, domain=DOMAIN
    )

    assert len(ent_reg.updates) == n_ent
    assert len(dev_reg.updates) == n_dev
    assert ent_reg.entities["event.dac46cc330"].entity_id == "event.dac46cc330"
    assert ent_reg.entities["event.2f8185190000df"].entity_id == (
        "event.2f8185190000df"
    )


def test_config_flow_version_is_2() -> None:
    text = (_COMP_DIR / "config_flow.py").read_text(encoding="utf-8")
    assert "VERSION = 2" in text


def test_async_migrate_entry_exists() -> None:
    text = (_COMP_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "async def async_migrate_entry(" in text
    assert "apply_registry_migration(" in text
    assert "version=2" in text
