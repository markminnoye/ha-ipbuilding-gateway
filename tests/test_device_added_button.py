"""Tests for learn-on-press ``device_added`` handling in the companion."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest


class _StubDataUpdateCoordinator:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __class_getitem__(cls, _item):
        return cls


class _StubConfigEntry:
    def __init__(self) -> None:
        self.data: dict = {}


class _StubConfig:
    language = "en"


class _StubServices:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    async def async_call(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
        blocking: bool = False,
    ) -> None:
        self.calls.append((domain, service, service_data or {}))


class _StubHomeAssistant:
    def __init__(self) -> None:
        self.config = _StubConfig()
        self.services = _StubServices()
        self._tasks: list[Any] = []

    def async_create_task(self, coro: Any) -> None:
        self._tasks.append(coro)

    async def async_block_till_done(self) -> None:
        return None


def _ensure_stub(name: str, **attrs) -> types.ModuleType:
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def _ensure_stub_package(name: str) -> types.ModuleType:
    mod = sys.modules.get(name)
    if not isinstance(mod, types.ModuleType) or not hasattr(mod, "__path__"):
        mod = types.ModuleType(name)
        mod.__path__ = []  # type: ignore[attr-defined]
        sys.modules[name] = mod
    return mod


_ensure_stub("homeassistant.const", CONF_HOST="host", CONF_PORT="port")
_ensure_stub_package("homeassistant.helpers")
_ensure_stub(
    "homeassistant.helpers.update_coordinator",
    DataUpdateCoordinator=_StubDataUpdateCoordinator,
)


class _StubEntityEntry:
    def __init__(self, device_id: str = "ha-device-abc") -> None:
        self.device_id = device_id


class _StubDeviceEntry:
    def __init__(self, device_id: str) -> None:
        self.id = device_id


class _StubEntityRegistry:
    def __init__(self) -> None:
        self._by_entity_id: dict[str, _StubEntityEntry] = {}
        self._by_unique: dict[tuple[str, str, str], str] = {}

    def async_get(self, entity_id: str) -> _StubEntityEntry | None:
        return self._by_entity_id.get(entity_id)

    def async_get_entity_id(
        self, domain: str, platform: str, unique_id: str
    ) -> str | None:
        return self._by_unique.get((domain, platform, unique_id))


class _StubDeviceRegistry:
    def __init__(self) -> None:
        self._by_identifiers: dict[frozenset, _StubDeviceEntry] = {}

    def async_get_device(
        self, identifiers: set[tuple[str, str]] | None = None, **_kwargs: Any
    ) -> _StubDeviceEntry | None:
        if not identifiers:
            return None
        return self._by_identifiers.get(frozenset(identifiers))


_ENTITY_REGISTRY = _StubEntityRegistry()
_DEVICE_REGISTRY = _StubDeviceRegistry()


def _er_async_get(_hass: Any) -> _StubEntityRegistry:
    return _ENTITY_REGISTRY


def _dr_async_get(_hass: Any) -> _StubDeviceRegistry:
    return _DEVICE_REGISTRY


def _get_url(_hass: Any) -> str:
    return "http://homeassistant.local:8123"


_ensure_stub(
    "homeassistant.helpers.entity_registry",
    async_get=_er_async_get,
)
_ensure_stub(
    "homeassistant.helpers.device_registry",
    async_get=_dr_async_get,
)
_ensure_stub(
    "homeassistant.helpers.network",
    get_url=_get_url,
)
# Make ``from homeassistant.helpers import …`` work with our stub package.
_helpers = sys.modules["homeassistant.helpers"]
_helpers.entity_registry = sys.modules["homeassistant.helpers.entity_registry"]
_helpers.device_registry = sys.modules["homeassistant.helpers.device_registry"]
_helpers.network = sys.modules["homeassistant.helpers.network"]

_ensure_stub("homeassistant.config_entries", ConfigEntry=_StubConfigEntry)
_ensure_stub("homeassistant.core", HomeAssistant=_StubHomeAssistant)
_ensure_stub(
    "aiohttp",
    ClientWebSocketResponse=object,
    ClientSession=object,
    ClientConnectionError=type("ClientConnectionError", (Exception,), {}),
    ClientTimeout=lambda total=None: None,
    WSMsgType=types.SimpleNamespace(
        TEXT="text", CLOSE="close", CLOSED="closed", ERROR="error"
    ),
)


@pytest.fixture(autouse=True)
def _restore_registry_stubs() -> None:
    """Keep registry stubs intact if a later test module overwrote them at import."""
    er_mod = _ensure_stub(
        "homeassistant.helpers.entity_registry", async_get=_er_async_get
    )
    dr_mod = _ensure_stub(
        "homeassistant.helpers.device_registry", async_get=_dr_async_get
    )
    net_mod = _ensure_stub(
        "homeassistant.helpers.network", get_url=_get_url
    )
    helpers = _ensure_stub_package("homeassistant.helpers")
    helpers.entity_registry = er_mod
    helpers.device_registry = dr_mod
    helpers.network = net_mod
    _ENTITY_REGISTRY._by_entity_id.clear()
    _ENTITY_REGISTRY._by_unique.clear()
    _DEVICE_REGISTRY._by_identifiers.clear()


_REPO = Path(__file__).resolve().parents[1]
_COMP_DIR = _REPO / "custom_components" / "ha_ipbuilding_gateway"

_pkg = sys.modules.get("ha_ipbuilding_gateway")
if not isinstance(_pkg, types.ModuleType) or not hasattr(_pkg, "__path__"):
    _pkg = types.ModuleType("ha_ipbuilding_gateway")
    sys.modules["ha_ipbuilding_gateway"] = _pkg
_pkg.__path__ = [str(_COMP_DIR)]  # type: ignore[attr-defined]

for _name in ("const", "coordinator"):
    _spec = importlib.util.spec_from_file_location(
        f"ha_ipbuilding_gateway.{_name}", _COMP_DIR / f"{_name}.py"
    )
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = _module
    _spec.loader.exec_module(_module)  # type: ignore[union-attr]

coordinator_mod = sys.modules["ha_ipbuilding_gateway.coordinator"]
DOMAIN = sys.modules["ha_ipbuilding_gateway.const"].DOMAIN


def _seed_button_registries(hw_id: str, ha_device_id: str) -> None:
    """Register stubs so notification resolves a concrete device deep-link."""
    _DEVICE_REGISTRY._by_identifiers[frozenset({(DOMAIN, hw_id)})] = _StubDeviceEntry(
        ha_device_id
    )
    entity_id = f"event.{hw_id}"
    _ENTITY_REGISTRY._by_entity_id[entity_id] = _StubEntityEntry(ha_device_id)
    _ENTITY_REGISTRY._by_unique[("event", DOMAIN, f"event_{hw_id}")] = entity_id


def _build_coordinator() -> Any:
    coord = coordinator_mod.IPBuildingCoordinator.__new__(
        coordinator_mod.IPBuildingCoordinator
    )
    coord.hass = _StubHomeAssistant()
    coord._data = {}
    coord._modules = {}
    coord._known_devices = set()
    coord._platform_callbacks = {}
    coord._platform_entities = {}
    coord._entity_listeners = {}
    coord._host = "127.0.0.1"
    coord._port = 8080
    return coord


async def _drain(hass: _StubHomeAssistant) -> None:
    while hass._tasks:
        coro = hass._tasks.pop(0)
        await coro


def test_button_device_added_creates_entity_and_notification() -> None:
    coord = _build_coordinator()
    added: list[list[dict]] = []
    coord.register_platform("event", lambda devices: added.append(devices))
    _seed_button_registries("2f8185df", "ha-device-abc")

    async def _run() -> None:
        await coord._handle_message(
            {
                "type": "device_added",
                "semantic_type": "button",
                "id": "2f8185190000df",
                "module_id": "00:24:77:52:ad:aa",
                "module_ip": "10.10.1.50",
                "device_type": "input",
                "name": "",
                "room": "",
                "active": True,
                "channel": None,
            }
        )
        await _drain(coord.hass)

    asyncio.run(_run())

    assert "2f8185df" in coord._data
    assert "2f8185190000df" not in coord._data
    assert coord._data["2f8185df"]["semantic_type"] == "button"
    assert coord._data["2f8185df"]["name"] == "Button 2f8185df"
    assert ("2f8185df", True) in coord._known_devices
    assert len(added) == 1
    assert added[0][0]["id"] == "2f8185df"

    assert len(coord.hass.services.calls) == 1
    domain, service, payload = coord.hass.services.calls[0]
    assert domain == "persistent_notification"
    assert service == "create"
    assert payload["notification_id"] == f"{DOMAIN}_button_2f8185df"
    assert "2f8185df" in payload["message"]
    assert payload["title"] == "New IPBuilding button"
    assert (
        "http://homeassistant.local:8123/config/devices/device/ha-device-abc"
        in payload["message"]
    )
    assert "[Open device settings]" in payload["message"]


def test_button_device_added_notification_nl() -> None:
    coord = _build_coordinator()
    coord.hass.config.language = "nl"
    coord.register_platform("event", lambda _devices: None)
    _seed_button_registries("aaaaaaaa", "ha-device-nl")

    async def _run() -> None:
        await coord._handle_message(
            {
                "type": "device_added",
                "semantic_type": "button",
                "id": "aaaaaaaaaaaaaa",
                "active": True,
            }
        )
        await _drain(coord.hass)

    asyncio.run(_run())

    payload = coord.hass.services.calls[0][2]
    assert payload["title"] == "Nieuwe IPBuilding drukknop"
    assert "[Open apparaat-instellingen]" in payload["message"]
    assert (
        "http://homeassistant.local:8123/config/devices/device/ha-device-nl"
        in payload["message"]
    )


def test_module_device_added_ignored() -> None:
    coord = _build_coordinator()
    added: list[list[dict]] = []
    coord.register_platform("event", lambda devices: added.append(devices))

    async def _run() -> None:
        await coord._handle_message(
            {
                "type": "device_added",
                "id": "00:24:77:52:ac:be",
                "ip": "10.10.1.55",
                "mac": "00:24:77:52:ac:be",
            }
        )
        await _drain(coord.hass)

    asyncio.run(_run())

    assert coord._data == {}
    assert added == []
    assert coord.hass.services.calls == []


def test_duplicate_button_device_added_does_not_recreate() -> None:
    coord = _build_coordinator()
    added: list[list[dict]] = []
    coord.register_platform("event", lambda devices: added.append(devices))
    _seed_button_registries("2f8185df", "ha-device-dup")
    msg = {
        "type": "device_added",
        "semantic_type": "button",
        "id": "2f8185190000df",
        "active": True,
    }

    async def _run() -> None:
        await coord._handle_message(msg)
        await _drain(coord.hass)
        await coord._handle_message(msg)
        await _drain(coord.hass)

    asyncio.run(_run())

    assert len(added) == 1
    assert len(coord.hass.services.calls) == 1


def test_button_event_14hex_reaches_8hex_listener() -> None:
    coord = _build_coordinator()
    received: list[dict] = []
    coord.register_entity("button:2f8185df", received.append)

    async def _run() -> None:
        await coord._handle_message(
            {
                "type": "button_event",
                "id": "2f8185190000df",
                "action": "press",
            }
        )

    asyncio.run(_run())

    assert len(received) == 1
    assert received[0]["action"] == "press"


def test_button_event_8hex_reaches_8hex_listener() -> None:
    coord = _build_coordinator()
    received: list[dict] = []
    coord.register_entity("button:2f8185df", received.append)

    async def _run() -> None:
        await coord._handle_message(
            {
                "type": "button_event",
                "id": "2f8185df",
                "action": "press",
            }
        )

    asyncio.run(_run())

    assert len(received) == 1
    assert received[0]["id"] == "2f8185df"


def test_unknown_dialect_notification_en() -> None:
    coord = _build_coordinator()
    coord.register_platform("event", lambda _devices: None)
    _seed_button_registries("dac46cc3", "ha-device-unknown")

    async def _run() -> None:
        await coord._handle_message(
            {
                "type": "device_added",
                "semantic_type": "button",
                "id": "dac46c100000c3",
                "device_type": "input",
                "active": True,
                "dialect_id": "input.unknown.button_event",
                "type_hex": "01",
            }
        )
        await _drain(coord.hass)

    asyncio.run(_run())

    payload = coord.hass.services.calls[0][2]
    assert payload["title"] == "Unknown IPBuilding input type"
    assert "01" in payload["message"]
    assert "dac46cc3" in payload["message"]
    assert payload["notification_id"] == f"{DOMAIN}_button_dac46cc3"


def test_unknown_dialect_notification_nl() -> None:
    coord = _build_coordinator()
    coord.hass.config.language = "nl"
    coord.register_platform("event", lambda _devices: None)
    _seed_button_registries("dac46cc3", "ha-device-unknown-nl")

    async def _run() -> None:
        await coord._handle_message(
            {
                "type": "device_added",
                "semantic_type": "button",
                "id": "dac46cc330",
                "device_type": "input",
                "active": True,
                "dialect_id": "input.unknown.button_event",
                "type_hex": "55",
            }
        )
        await _drain(coord.hass)

    asyncio.run(_run())

    payload = coord.hass.services.calls[0][2]
    assert payload["title"] == "Onbekend IPBuilding inputtype"
    assert "55" in payload["message"]
    assert "typebyte" in payload["message"]
