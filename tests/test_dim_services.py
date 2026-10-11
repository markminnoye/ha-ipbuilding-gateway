"""Hold-to-dim services must survive the HA 2026.10 helper signature.

Home Assistant 2026.10 removed the ``hass`` argument from
``async_extract_entity_ids``. The helper now reads ``service_call.hass``.
Calling it as ``async_extract_entity_ids(hass, call)`` therefore treats the
``HomeAssistant`` object as the service call and raises
``'HomeAssistant' object has no attribute 'hass'``.

These tests build a ``ServiceCall`` the way Home Assistant does (``.hass``
is the Home Assistant object) and a helper with the current signature.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_COMP_DIR = _REPO / "custom_components" / "ha_ipbuilding_gateway"
_ENTITY_ID = "light.dimmer_channel"
_DEVICE_ID = "dimmer-channel-1"

# Modules this file may create. Restored after each test so other modules
# keep the stubs they installed at import time.
_STUB_NAMES = (
    "homeassistant",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.config_validation",
    "homeassistant.helpers.entity_registry",
    "homeassistant.helpers.service",
    "ha_ipbuilding_gateway",
    "ha_ipbuilding_gateway.const",
    "ha_ipbuilding_gateway.services",
)


class HomeAssistant:
    """Home Assistant stand-in: has ``data`` (like core) and no ``hass``."""

    def __init__(self) -> None:
        self.data: dict = {}
        self.services = _ServiceRegistry()


class ServiceCall:
    """Mimic of ``homeassistant.core.ServiceCall`` as of HA 2026.10.

    The constructor stores the Home Assistant object on ``.hass``. That is
    the attribute the current extraction helper reads.
    """

    def __init__(self, hass: HomeAssistant, domain: str, service: str, data: dict | None = None) -> None:
        self.hass = hass
        self.domain = domain
        self.service = service
        self.data = dict(data or {})
        self.context = None
        self.return_response = False


class _ServiceRegistry:
    def __init__(self) -> None:
        self._handlers: dict[tuple[str, str], object] = {}

    def has_service(self, domain: str, service: str) -> bool:
        return (domain, service) in self._handlers

    def async_register(self, domain: str, service: str, handler, schema=None) -> None:
        self._handlers[(domain, service)] = handler

    def async_remove(self, domain: str, service: str) -> None:
        self._handlers.pop((domain, service), None)


class _RegistryEntry:
    def __init__(self, platform: str, unique_id: str) -> None:
        self.platform = platform
        self.unique_id = unique_id


class _EntityRegistry:
    def async_get(self, entity_id: str) -> _RegistryEntry | None:
        if entity_id == _ENTITY_ID:
            return _RegistryEntry("ha_ipbuilding_gateway", _DEVICE_ID)
        return None


class _Coordinator:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def async_send_command(self, device_id: str, action: str) -> bool:
        self.sent.append((device_id, action))
        return True


async def _extract_entity_ids_legacy(hass, service_call, expand_group: bool = True):
    """Shape of ``async_extract_entity_ids`` before Home Assistant 2025.10.

    The first parameter is named ``hass``. The service call is the second.
    """
    del hass, expand_group
    raw = service_call.data.get("entity_id")
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {raw}
    return set(raw)


async def _extract_entity_ids_current(service_call, expand_group: bool = True):
    """Shape of ``async_extract_entity_ids`` on Home Assistant 2026.10.1.

    Signature is ``(service_call, expand_group=True)``. The implementation
    reads ``service_call.data`` and then ``service_call.hass``.
    """
    data = service_call.data
    _hass = service_call.hass
    del _hass, expand_group
    raw = data.get("entity_id")
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {raw}
    return set(raw)


# Existing stub modules that this file temporarily turns into packages.
_PACKAGES_MARKED: list[types.ModuleType] = []


def _ensure_package(name: str) -> types.ModuleType:
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    if not hasattr(mod, "__path__"):
        mod.__path__ = []  # type: ignore[attr-defined]
        _PACKAGES_MARKED.append(mod)
    return mod


def _ensure_module(name: str) -> types.ModuleType:
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    parent_name, _, child = name.rpartition(".")
    if parent_name:
        setattr(sys.modules[parent_name], child, mod)
    return mod


def _load_services(extract_entity_ids):
    """Import the companion services module against the given helper."""
    _ensure_package("homeassistant")
    _ensure_module("homeassistant.const")
    const_mod = sys.modules["homeassistant.const"]
    if not hasattr(const_mod, "CONF_HOST"):
        const_mod.CONF_HOST = "host"
    if not hasattr(const_mod, "CONF_PORT"):
        const_mod.CONF_PORT = "port"

    core = _ensure_module("homeassistant.core")
    core.HomeAssistant = HomeAssistant
    core.ServiceCall = ServiceCall

    exceptions = _ensure_module("homeassistant.exceptions")
    if not hasattr(exceptions, "HomeAssistantError"):
        exceptions.HomeAssistantError = type("HomeAssistantError", (Exception,), {})

    _ensure_package("homeassistant.helpers")
    cv = _ensure_module("homeassistant.helpers.config_validation")
    cv.make_entity_service_schema = lambda schema: schema

    er = _ensure_module("homeassistant.helpers.entity_registry")
    er.async_get = lambda _hass: _EntityRegistry()

    service = _ensure_module("homeassistant.helpers.service")
    service.async_extract_entity_ids = extract_entity_ids

    pkg = sys.modules.get("ha_ipbuilding_gateway")
    if pkg is None or not hasattr(pkg, "__path__"):
        pkg = types.ModuleType("ha_ipbuilding_gateway")
        pkg.__path__ = [str(_COMP_DIR)]  # type: ignore[attr-defined]
        sys.modules["ha_ipbuilding_gateway"] = pkg

    spec = importlib.util.spec_from_file_location(
        "ha_ipbuilding_gateway.services",
        _COMP_DIR / "services.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _exercise(extract_entity_ids, service_name: str, action: str) -> None:
    """Register one dim service and assert the gateway command is sent."""
    before = {name: sys.modules.get(name) for name in _STUB_NAMES}
    attr_backup: list[tuple[object, str, bool, object]] = []

    def _remember(obj: object, name: str) -> None:
        attr_backup.append((obj, name, hasattr(obj, name), getattr(obj, name, None)))

    try:
        # Remember attributes the loader overwrites on modules that already exist.
        for dotted in (
            "homeassistant.core",
            "homeassistant.helpers.entity_registry",
            "homeassistant.helpers.service",
            "homeassistant.helpers.config_validation",
        ):
            existing = sys.modules.get(dotted)
            if existing is None:
                continue
            if dotted.endswith(".core"):
                _remember(existing, "HomeAssistant")
                _remember(existing, "ServiceCall")
            elif dotted.endswith(".entity_registry"):
                _remember(existing, "async_get")
            elif dotted.endswith(".service"):
                _remember(existing, "async_extract_entity_ids")
            elif dotted.endswith(".config_validation"):
                _remember(existing, "make_entity_service_schema")

        services = _load_services(extract_entity_ids)
        hass = HomeAssistant()
        coordinator = _Coordinator()
        services.async_register_services(hass, coordinator)
        handler = hass.services._handlers[("ha_ipbuilding_gateway", service_name)]
        call = ServiceCall(
            hass,
            "ha_ipbuilding_gateway",
            service_name,
            {"entity_id": _ENTITY_ID},
        )
        assert call.hass is hass
        assert not hasattr(hass, "hass")

        asyncio.run(handler(call))

        assert coordinator.sent == [(_DEVICE_ID, action)]
    finally:
        for obj, name, had, old in reversed(attr_backup):
            if had:
                setattr(obj, name, old)
            elif hasattr(obj, name):
                delattr(obj, name)
        for name, previous in before.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
        while _PACKAGES_MARKED:
            marked = _PACKAGES_MARKED.pop()
            if hasattr(marked, "__path__"):
                del marked.__path__


@pytest.mark.parametrize(
    ("service_name", "action"),
    [("dim_start", "DIM_START"), ("dim_stop", "DIM_STOP")],
)
def test_hold_to_dim_service_sends_gateway_command(service_name: str, action: str) -> None:
    """dim_start / dim_stop send DIM_START / DIM_STOP for a targeted light.

    The service call is a ServiceCall whose ``.hass`` is a HomeAssistant-like
    object. That is the shape that breaks when the helper is still invoked
    with ``(hass, call)`` on Home Assistant 2026.10.
    """
    _exercise(_extract_entity_ids_current, service_name, action)


@pytest.mark.parametrize(
    ("service_name", "action"),
    [("dim_start", "DIM_START"), ("dim_stop", "DIM_STOP")],
)
def test_hold_to_dim_service_still_sends_command_on_older_helper(
    service_name: str, action: str
) -> None:
    """The same services keep working when HA still requires the hass argument.

    Home Assistant 2023.8 through 2025.9 declare ``async_extract_entity_ids``
    as ``(hass, service_call)``. The minimum in ``hacs.json`` is 2023.8.
    """
    _exercise(_extract_entity_ids_legacy, service_name, action)
