"""Phase 1: the EventEntity accepts single_press and tags the HA-standard type.

Runtime tests require the ``homeassistant`` package (see other files in
this directory for the same pattern). When HA is not installed, all tests
in this file are skipped — the matching CI environment installs
``requirements-dev.txt``.

Source-level checks for the event-types / bus-event / standard-mapping
shape of the event module live here; companion-specific helper / handler
tests live in other files.
"""
from __future__ import annotations

import pytest

ha = pytest.importorskip("homeassistant")

from custom_components.ha_ipbuilding_gateway import event as ev  # noqa: E402


def test_single_press_is_a_known_event_type():
    assert "single_press" in ev._BUTTON_EVENT_TYPES


def test_single_press_maps_to_bus_event():
    assert ev._ACTION_TO_BUS_EVENT["single_press"] == "button_single_pressed"


def test_standard_event_type_mapping():
    assert ev._STANDARD_EVENT_TYPE["single_press"] == "press_end"
    assert ev._STANDARD_EVENT_TYPE["long_press"] == "long_press_start"
    assert ev._STANDARD_EVENT_TYPE["press"] == "press_start"


def test_release_has_no_standard_event_type():
    # release is a raw edge that follows both short and long presses, so it
    # has no single standard equivalent and must stay unmapped.
    assert "release" not in ev._STANDARD_EVENT_TYPE
