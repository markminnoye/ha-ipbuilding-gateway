"""Tests for the IPBuilding Gateway Supervisor add-on slug matcher.

The companion's ``_is_ipbuilding_gateway_addon`` helper must accept both
the bare store slug (``ipbuilding_gateway``) and custom-repo prefixed
slugs (e.g. ``3059e002_ipbuilding_gateway``) so Supervisor discovery
works for users who install the add-on from this repository rather than
the official store.

We extract the helper from ``config_flow.py`` with a regex so the test
runs without ``voluptuous`` / Home Assistant installed.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_FLOW = _REPO / "custom_components" / "ha_ipbuilding_gateway" / "config_flow.py"


def _load_helper() -> callable:
    src = _FLOW.read_text(encoding="utf-8")
    # Include the ADDON_SLUG constant and the helper itself.
    pattern = re.compile(
        r'^ADDON_SLUG = "ipbuilding_gateway"\n'
        r"(?:\n)+"
        r"def _is_ipbuilding_gateway_addon\(slug: str\) -> bool:\s*\n"
        r'    """(?:[^"\\]|\\.)*"""\n'
        r"(?P<body>(?:[ \t]+.*\n)+)",
        re.MULTILINE,
    )
    match = pattern.search(src)
    if not match:
        raise RuntimeError("Could not locate _is_ipbuilding_gateway_addon in config_flow.py")
    snippet = match.group(0)
    namespace: dict = {"__name__": "slug_helper"}
    exec(snippet, namespace)  # noqa: S102 - test loader for a single helper
    return namespace["_is_ipbuilding_gateway_addon"]


_is_ipbuilding_gateway_addon = _load_helper()


class TestIsIpbuildingGatewayAddon:
    def test_bare_store_slug(self) -> None:
        assert _is_ipbuilding_gateway_addon("ipbuilding_gateway") is True

    def test_custom_repo_prefixed_slug(self) -> None:
        assert (
            _is_ipbuilding_gateway_addon("3059e002_ipbuilding_gateway") is True
        )

    def test_arbitrary_repo_prefix(self) -> None:
        assert (
            _is_ipbuilding_gateway_addon("deadbeef_ipbuilding_gateway") is True
        )

    def test_unrelated_slug_rejected(self) -> None:
        assert _is_ipbuilding_gateway_addon("core_mosquitto") is False

    def test_empty_slug_rejected(self) -> None:
        assert _is_ipbuilding_gateway_addon("") is False

    def test_partial_match_rejected(self) -> None:
        # Extra characters after the slug are not the IPBuilding add-on.
        assert _is_ipbuilding_gateway_addon("ipbuilding_gateway_extras") is False
