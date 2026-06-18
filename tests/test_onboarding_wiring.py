"""Source-level tests for onboarding wiring."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_COMP = _REPO / "custom_components" / "ha_ipbuilding_gateway"


def test_options_flow_routes_to_onboarding_intro() -> None:
    text = (_COMP / "options_flow.py").read_text(encoding="utf-8")
    assert "OnboardingFlowMixin" in text
    assert "async_step_onboarding_intro" in text
    assert "_auto_onboard" in text


def test_init_triggers_options_flow_with_auto_flag() -> None:
    text = (_COMP / "__init__.py").read_text(encoding="utf-8")
    assert "_maybe_launch_onboarding" in text
    assert "_auto_onboard" in text
    assert "async_init" in text
    # The old "context={'source': 'onboarding'}" pattern was a HA-illegal
    # config flow source and has been removed.
    assert 'context={"source": "onboarding"' not in text


def test_config_flow_no_longer_exposes_onboarding_step() -> None:
    text = (_COMP / "config_flow.py").read_text(encoding="utf-8")
    assert "async_step_onboarding" not in text
    assert "OnboardingFlowMixin" not in text


def test_coordinator_exposes_discover_with_result() -> None:
    text = (_COMP / "coordinator.py").read_text(encoding="utf-8")
    assert "async def async_run_discover_with_result" in text
    assert "async_trigger_discover" in text
