"""Unit tests for ``entity.py`` module-device naming helpers.

Pure-Python tests that do not require a real Home Assistant install.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

# ---------------------------------------------------------------------------
# Minimal ``homeassistant`` stub so the companion's ``entity`` module
# can be imported without a real HA install. We only need the symbols the
# module itself imports from ``.const``.
# ---------------------------------------------------------------------------
if "homeassistant" not in sys.modules:
    sys.modules["homeassistant"] = types.ModuleType("homeassistant")
    const_mod = types.ModuleType("homeassistant.const")
    const_mod.CONF_HOST = "host"
    const_mod.CONF_PORT = "port"
    sys.modules["homeassistant.const"] = const_mod

_REPO = Path(__file__).resolve().parents[1]
_COMP_DIR = _REPO / "custom_components" / "ipbuilding_gateway_ha"

# Build a synthetic package so ``from .const import`` resolves.
_fake_pkg = types.ModuleType("ipbuilding_gateway_ha")
_fake_pkg.__path__ = [str(_COMP_DIR)]
sys.modules["ipbuilding_gateway_ha"] = _fake_pkg

for _name in ("const", "entity"):
    _spec = importlib.util.spec_from_file_location(
        f"ipbuilding_gateway_ha.{_name}", _COMP_DIR / f"{_name}.py"
    )
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = _module
    _spec.loader.exec_module(_module)  # type: ignore[union-attr]

entity_mod = sys.modules["ipbuilding_gateway_ha.entity"]


def test_module_device_name_ip_placeholder_falls_back_to_role():
    """IP-based name (auto-discovery placeholder) resolves to the role label."""
    module = {
        "name": "10.10.1.50",
        "ip": "10.10.1.50",
        "type": "input",
        "model": "IP1100PoE",
    }
    assert entity_mod.module_device_name(module) == "Input"


def test_module_device_name_sku_default_falls_back_to_role():
    """Module whose name equals the SKU default still shows the role label."""
    module = {
        "name": "IP0200PoE",
        "ip": "10.10.1.30",
        "type": "relay",
        "model": "IP0200PoE",
    }
    assert entity_mod.module_device_name(module) == "Relay"


def test_module_device_name_operator_name_is_preserved():
    """Operator-configured names survive the placeholder filter."""
    module = {
        "name": "Kelder relais",
        "ip": "10.10.1.30",
        "type": "relay",
        "model": "IP0200PoE",
    }
    assert entity_mod.module_device_name(module) == "Kelder relais"


def test_module_device_model_falls_back_to_canonical_sku():
    """Empty model is enriched with the canonical SKU for the type."""
    assert entity_mod.module_device_model({"model": "", "type": "input"}) == "IP1100PoE"
    assert entity_mod.module_device_model({"model": "", "type": "relay"}) == "IP0200PoE"
    assert entity_mod.module_device_model({"model": "", "type": "dimmer"}) == "IP0300PoE"


def test_module_device_model_prefers_factory_label():
    """A real factory product label (e.g. IP200PoE) is kept as-is."""
    assert entity_mod.module_device_model(
        {"model": "IP200PoE", "type": "relay"}
    ) == "IP200PoE"


def test_module_device_model_empty_for_unknown_type():
    assert entity_mod.module_device_model({"model": "", "type": "unknown"}) == ""


def test_build_module_hub_device_info_uses_sku_model():
    """Hub device_info shows the SKU as ``model`` even when devices.json lacks it."""
    info = entity_mod.build_module_hub_device_info(
        {
            "id": "00:24:77:52:ad:aa",
            "ip": "10.10.1.50",
            "name": "10.10.1.50",
            "type": "input",
            "model": "",
        }
    )
    assert info["model"] == "IP1100PoE"
    assert info["name"] == "Input"
