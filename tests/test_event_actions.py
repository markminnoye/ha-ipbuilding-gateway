"""Source-level checks for button event taxonomy mappings in event.py.

These tests inspect ``event.py`` directly so they run without a Home
Assistant install. Runtime EventEntity behaviour is covered in CI where
``requirements-dev.txt`` is installed.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_EVENT_SOURCE = (
    _REPO / "custom_components" / "ha_ipbuilding_gateway" / "event.py"
).read_text(encoding="utf-8")
_TREE = ast.parse(_EVENT_SOURCE)


def _assign_list(name: str) -> list[str]:
    for node in _TREE.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    assert isinstance(node.value, ast.List)
                    return [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant)]
    raise AssertionError(f"{name} not found")


def _assign_dict(name: str) -> dict[str, str]:
    for node in _TREE.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name and isinstance(node.value, ast.Dict):
                out: dict[str, str] = {}
                for k, v in zip(node.value.keys, node.value.values):
                    if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                        out[k.value] = v.value
                return out
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    assert isinstance(node.value, ast.Dict)
                    out = {}
                    for k, v in zip(node.value.keys, node.value.values):
                        if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                            out[k.value] = v.value
                    return out
    raise AssertionError(f"{name} not found")


def test_single_press_is_a_known_event_type():
    assert "single_press" in _assign_list("_BUTTON_EVENT_TYPES")


def test_single_press_maps_to_bus_event():
    assert _assign_dict("_ACTION_TO_BUS_EVENT")["single_press"] == "button_single_pressed"


def test_standard_event_type_mapping():
    mapping = _assign_dict("_STANDARD_EVENT_TYPE")
    assert mapping["single_press"] == "press_end"
    assert mapping["long_press"] == "long_press_start"
    assert mapping["press"] == "press_start"


def test_release_has_no_standard_event_type():
    assert "release" not in _assign_dict("_STANDARD_EVENT_TYPE")


def test_multi_press_event_types_known():
    types = _assign_list("_BUTTON_EVENT_TYPES")
    assert "double_press" in types
    assert "triple_press" in types


def test_multi_press_bus_events():
    bus = _assign_dict("_ACTION_TO_BUS_EVENT")
    assert bus["double_press"] == "button_double_pressed"
    assert bus["triple_press"] == "button_triple_pressed"


def test_multi_press_standard_mapping():
    mapping = _assign_dict("_STANDARD_EVENT_TYPE")
    assert mapping["double_press"] == "multi_press_end"
    assert mapping["triple_press"] == "multi_press_end"


def test_count_is_passed_through_to_event_data():
    assert re.search(
        r'count\s*=\s*data\.get\(\s*["\']count["\']\s*\)',
        _EVENT_SOURCE,
    ), "event.py must pass gateway count into event_data"
    assert 'event_data["count"] = count' in _EVENT_SOURCE
