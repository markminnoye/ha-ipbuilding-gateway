"""Tests for the pure discovery-payload parser.

These tests import the parser directly — it has no Home Assistant
dependencies so we can run it in the test environment without
installing the full HA core tree.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_COMP = _REPO / "custom_components" / "ha_ipbuilding_gateway"
_PARSER_PATH = _COMP / "discovery_parser.py"
_CONST_PATH = _COMP / "const.py"


def _load_module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# The parser imports from .const, so we register a parent package first.
import types

_pkg = types.ModuleType("ha_ipbuilding_gateway")
_pkg.__path__ = [str(_COMP)]
sys.modules["ha_ipbuilding_gateway"] = _pkg

_const = _load_module_from_path("ha_ipbuilding_gateway.const", _CONST_PATH)
_parser = _load_module_from_path(
    "ha_ipbuilding_gateway.discovery_parser", _PARSER_PATH
)


class TestParseZeroconfPropertiesSchemaV2:
    """Schema v2: explicit host, port, sw, mac, instance_id."""

    def test_all_v2_fields(self) -> None:
        info = _parser.parse_zeroconf_properties(
            {
                "instance_id": "99eb5cf015604b9b984f6dab1c0af485",
                "sw": "1.0.4",
                "version": "1.0.4",
                "host": "192.168.1.50",
                "port": "8080",
                "base_url": "http://192.168.1.50:8080",
                "mac": "aa:bb:cc:dd:ee:ff",
                "homeassistant_addon": "false",
                "schema_version": "2",
            }
        )
        assert info.host == "192.168.1.50"
        assert info.port == 8080
        assert info.instance_id == "99eb5cf015604b9b984f6dab1c0af485"
        assert info.sw_version == "1.0.4"
        assert info.mac == "aa:bb:cc:dd:ee:ff"
        assert info.is_addon is False
        assert info.schema_version == 2

    def test_sw_fallback_to_version(self) -> None:
        """Older gateways (or v1 payloads) only carry ``version``."""
        info = _parser.parse_zeroconf_properties(
            {
                "instance_id": "abc",
                "version": "1.0.3",
                "homeassistant_addon": "true",
                "schema_version": "1",
            },
            host="127.0.0.1",
            port=8080,
        )
        # sw_version falls back to version
        assert info.sw_version == "1.0.3"
        assert info.mac is None
        assert info.schema_version == 1

    def test_addon_payload_no_mac(self) -> None:
        info = _parser.parse_zeroconf_properties(
            {
                "instance_id": "uuid-1",
                "sw": "1.0.4",
                "host": "127.0.0.1",
                "port": "8080",
                "base_url": "http://127.0.0.1:8080",
                "mac": "",
                "homeassistant_addon": "true",
                "schema_version": "2",
            }
        )
        assert info.is_addon is True
        # Empty mac serialised as None so the companion can skip it.
        assert info.mac is None
        assert info.host == "127.0.0.1"
        assert info.port == 8080

    def test_falls_back_to_srv_record_host(self) -> None:
        """Without TXT ``host``/``port`` we use the SRV record fields."""
        info = _parser.parse_zeroconf_properties(
            {
                "instance_id": "uuid-2",
                "homeassistant_addon": "false",
                "schema_version": "2",
            },
            host="gateway.local",
            port=8123,
        )
        assert info.host == "gateway.local"
        assert info.port == 8123
