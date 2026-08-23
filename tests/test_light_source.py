"""Source-level checks for the light platform.

Mirrors the source-only style of ``test_services_source.py`` so it runs
without a Home Assistant install. Runtime entity tests (instantiating the
entity against a mock coordinator) live in the HA-dependent modules.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_LIGHT = _REPO / "custom_components" / "ha_ipbuilding_gateway" / "light.py"


def test_dimmer_plain_toggle_uses_native_toggle_action() -> None:
    """A dimmer's plain toggle must use the native gateway ``TOGGLE`` action.

    ``TOGGLE`` becomes the ``T<ch>991000`` wire frame, which flips between off
    and the module's own last-level memory (matching the physical IPBuilding
    button). It must NOT fall back to HA's turn_off/turn_on → DIM path, which
    relies on HA's cached brightness and can be stale after a peer button
    press the gateway never saw.
    """
    src = _LIGHT.read_text(encoding="utf-8")
    assert "async def async_toggle" in src, (
        "light entity must override async_toggle so a dimmer toggle is native"
    )
    assert '"TOGGLE"' in src, (
        "the dimmer toggle path must dispatch the gateway TOGGLE action"
    )
    # Non-dimmer / parametrised toggles must still defer to the base impl.
    assert "super().async_toggle" in src, (
        "relay / parametrised toggles must fall back to LightEntity.async_toggle"
    )


def test_dimmer_advertises_brightness_in_init() -> None:
    """Dimmer lights must declare BRIGHTNESS before the first level arrives.

    HA caches supported_color_modes at entity registration. Setting it only
    inside ``_update_from_state`` when ``level`` is present hid the slider
    on modules that never answer a status poll.
    """
    src = _LIGHT.read_text(encoding="utf-8")
    init = src.split("async def async_added_to_hass", 1)[0]
    assert "ColorMode.BRIGHTNESS" in init, (
        "light.py __init__ must set ColorMode.BRIGHTNESS for dimmers"
    )
    assert "_is_dimmer" in init and "ColorMode.BRIGHTNESS" in init
