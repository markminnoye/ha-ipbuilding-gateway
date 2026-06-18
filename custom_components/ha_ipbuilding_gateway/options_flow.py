"""Options flow for ha_ipbuilding_gateway."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlowResult, OptionsFlow

from .onboarding_flow import OnboardingFlowMixin


class IPBuildingOptionsFlowHandler(OnboardingFlowMixin, OptionsFlow):
    """Handle options for IPBuilding Gateway HA.

    In HA 2026.6+ ``OptionsFlow.config_entry`` is a read-only property
    backed by ``self.hass.config_entries.async_get_known_entry`` — the
    flow manager injects the entry id via ``self.handler`` after the
    constructor returns. Do not define ``__init__(self, config_entry)``
    and do not assign ``self.config_entry``: the property has no setter
    and the assignment raises ``AttributeError`` before the first step
    runs.

    Menu options must map to ``async_step_<option>`` methods (the
    frontend sends ``{"next_step_id": "<option>"}`` and the backend
    dispatches via ``getattr(flow, "async_step_<option>")``). The single
    ``run_onboarding`` menu entry therefore needs a dedicated step.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Present the options menu or auto-launch the wizard.

        The post-install bootstrap in ``__init__.async_setup_entry`` sets
        ``hass.data[DOMAIN][f"{entry.entry_id}_auto_onboard"] = True``
        and then opens the flow via ``options.async_init(entry.entry_id)``.
        The first step is therefore ``async_step_init`` with
        ``user_input is None``; we detect the flag and jump straight to
        the onboarding intro. A manual *Configure* click (or a second
        open) sees no flag and falls through to the menu.
        """
        from .const import DOMAIN

        auto_flag = self.hass.data.get(DOMAIN, {}).get(
            f"{self.config_entry.entry_id}_auto_onboard"
        )
        if auto_flag:
            self.hass.data[DOMAIN].pop(
                f"{self.config_entry.entry_id}_auto_onboard", None
            )
            return await self.async_step_run_onboarding()

        return self.async_show_menu(
            step_id="init",
            menu_options=["run_onboarding"],
        )

    async def async_step_run_onboarding(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start the onboarding wizard.

        Dispatched by HA when the operator clicks the ``run_onboarding``
        menu entry, and reused by the post-install bootstrap in
        ``async_step_init``. Resets the per-flow caches so a re-run
        after completion shows a fresh wizard.
        """
        self._onboarding_entry = self.config_entry
        self._discover_task = None
        self._modules_refresh_task = None
        self._discover_result = None
        return await self.async_step_onboarding_intro()
