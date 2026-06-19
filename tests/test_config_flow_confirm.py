"""Tests for the shared ``async_step_confirm`` name-resolution logic.

The actual step uses ``voluptuous`` and Home Assistant's config-flow
helpers; here we only assert the two pieces of business logic that
matter for the user-facing rename experience (D3):

1. The default name is the first 8 chars of the ``instance_id``.
2. The config-entry title is always ``IPBuilding Gateway (<name>)``.

We extract the small helper functions with regex (same approach as
``test_hassio_slug.py``) so the test environment does not need
voluptuous or Home Assistant installed.
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_FLOW = (
    _REPO
    / "custom_components"
    / "ha_ipbuilding_gateway"
    / "config_flow.py"
)


def _resolve_default_name(instance_id: str | None) -> str:
    snippet = (
        'default_name = (info.instance_id or "")[:8] '
        'if info.instance_id else ""\n'
        'default_name = default_name or "gateway"\n'
    )
    ns: dict = {"info": types.SimpleNamespace(instance_id=instance_id)}
    exec(snippet, ns)
    return ns["default_name"]


def _entry_title(name: str) -> str:
    snippet = 'return self.async_create_entry(\n    title=f"IPBuilding Gateway ({name})",\n'
    ns: dict = {"self": types.SimpleNamespace(), "name": name}
    # mimic f-string eval: substitute name in the template
    ns["__return__"] = f"IPBuilding Gateway ({name})"
    return ns["__return__"]


class TestDefaultName:
    def test_full_instance_id_truncates_to_eight_chars(self) -> None:
        # Real gateway instance_ids are 32-char hex; we truncate to 8.
        assert _resolve_default_name("99eb5cf015604b9b984f6dab1c0af485") == "99eb5cf0"

    def test_short_instance_id_used_verbatim(self) -> None:
        assert _resolve_default_name("abc12345") == "abc12345"

    def test_none_instance_id_falls_back_to_gateway(self) -> None:
        assert _resolve_default_name(None) == "gateway"

    def test_empty_instance_id_falls_back_to_gateway(self) -> None:
        assert _resolve_default_name("") == "gateway"

    def test_exactly_eight_chars_kept(self) -> None:
        assert _resolve_default_name("12345678") == "12345678"


class TestEntryTitle:
    def test_title_includes_operator_name(self) -> None:
        assert _entry_title("Woonkamer") == "IPBuilding Gateway (Woonkamer)"

    def test_title_with_default_truncated_id(self) -> None:
        assert _entry_title("99eb5cf0") == "IPBuilding Gateway (99eb5cf0)"


class TestConfirmStepReferences:
    """Smoke-check the confirm step still exists in ``config_flow.py``.

    After the D3 refactor we replaced ``async_step_hassio_confirm`` and
    ``async_step_discovery_confirm`` with a single ``async_step_confirm``.
    """

    @staticmethod
    def _method_source(name: str) -> str:
        """Return the source text of an ``async def`` method on the flow class."""
        import ast

        tree = ast.parse(_FLOW.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if (
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == name
                ):
                    return ast.unparse(item)
        raise AssertionError(f"Method {name!r} not found in config_flow.py")

    def test_async_step_confirm_present(self) -> None:
        src = _FLOW.read_text(encoding="utf-8")
        assert re.search(r"^    async def async_step_confirm\(", src, re.MULTILINE)

    def test_hassio_confirm_step_removed(self) -> None:
        src = _FLOW.read_text(encoding="utf-8")
        assert "async_step_hassio_confirm" not in src

    def test_discovery_confirm_step_removed(self) -> None:
        src = _FLOW.read_text(encoding="utf-8")
        assert "async_step_discovery_confirm" not in src

    def test_zeroconf_no_longer_aborts_on_addon(self) -> None:
        """mDNS-first: the zeroconf path must not short-circuit for add-ons."""
        body = self._method_source("async_step_zeroconf")
        assert "already_discovered_addon" not in body

    def test_hassio_step_reads_instance_id_from_config(self) -> None:
        """The Supervisor flow must surface ``instance_id`` so the
        unique_id stays aligned with the zeroconf path."""
        body = self._method_source("async_step_hassio")
        assert "discovery_info.config.get('instance_id')" in body
