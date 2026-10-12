"""Unit tests for the duplicated ``canonical_button_id`` helper."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

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

canonical_button_id = _module.canonical_button_id
canonicalise_button_device = _module.canonicalise_button_device


def test_length_dispatch_and_confirmed_pairs() -> None:
    # 16 getButtons (type prefix + wire) → 8
    assert canonical_button_id("2ddac46c100000c3") == "dac46cc3"
    assert canonical_button_id("2d2f8185190000df") == "2f8185df"
    # 14 wire
    assert canonical_button_id("dac46c100000c3") == "dac46cc3"
    assert canonical_button_id("2f8185190000df") == "2f8185df"
    # 10 legacy IPA-derived
    assert canonical_button_id("dac46cc330") == "dac46cc3"
    # 8 already canonical
    assert canonical_button_id("dac46cc3") == "dac46cc3"
    assert canonical_button_id("2f8185df") == "2f8185df"


def test_uppercase_and_whitespace() -> None:
    assert canonical_button_id("  DAC46C100000C3  ") == "dac46cc3"
    assert canonical_button_id("DAC46CC330") == "dac46cc3"


def test_non_hex_and_other_lengths_return_none() -> None:
    assert canonical_button_id("not-hex!!") is None
    assert canonical_button_id("zzzzzzzz") is None
    assert canonical_button_id("abc") is None
    assert canonical_button_id("dac46cc330ff") is None  # 12 hex
    assert canonical_button_id("") is None
    assert canonical_button_id("10.10.1.30-0") is None


def test_canonicalise_button_device_rewrites_input_not_channel() -> None:
    button = canonicalise_button_device(
        {"id": "2f8185190000df", "device_type": "input", "name": "Hal"}
    )
    assert button["id"] == "2f8185df"
    assert button["name"] == "Hal"

    channel = {"id": "10.10.1.30-0", "device_type": "relay", "name": "Keuken"}
    assert canonicalise_button_device(channel) is channel
    assert channel["id"] == "10.10.1.30-0"


def test_canonicalise_button_device_keeps_id_when_helper_returns_none() -> None:
    device = {"id": "not-a-button-id", "device_type": "input"}
    result = canonicalise_button_device(device)
    assert result is device
    assert result["id"] == "not-a-button-id"
