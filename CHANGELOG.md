# Changelog

All notable changes to this custom component are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.9.0] - 2026-08-30

### Added
- Persistent notification **Unknown IPBuilding input type** / **Onbekend IPBuilding inputtype** when the gateway reports `dialect_id: input.unknown.button_event`, with the type byte in the body.

### Changed
- **Canonical 8-hex button ids.** The companion accepts 8-, 10-, 14- and 16-hex button ids from the gateway and registers entities under the 8-hex form, so a `button_event` reaches the entity regardless of which id form the gateway sent. Requires gateway ≥ **1.7.0** for dialect/`type_hex` on `device_added`; older gateways still work for id canonicalisation.
- Config-entry **version 2** migrates existing `event_<10 or 14 hex>` unique_ids and matching device identifiers to 8-hex. `entity_id` is left unchanged so names, areas, automations and blueprints survive the upgrade.

## [1.8.3] - 2026-08-23

### Fixed
- Dimmer lights advertise `ColorMode.BRIGHTNESS` at entity creation, so
  Home Assistant shows a brightness slider even when the gateway has not
  yet (or never) reported a `level`. Relays stay `ONOFF`.

## [1.8.2] - 2026-08-10

### Added
- Power sensor exposes gateway `max_watt` as a state attribute
  (`state_attr('sensor.…_power', 'max_watt')`).

## [1.8.1] - 2026-08-06

### Added
- **New wall button on first press.** When the gateway emits `device_added`
  for a button, the companion creates an `event` entity immediately and
  shows a notification linking to the device page (name + area). Requires
  gateway ≥ **1.6.2** (learn-on-press).

## [1.8.0] - 2026-07-17

### Added
- **Double and triple press** — `double_press` / `triple_press` events,
  device triggers (`double_pressed` / `triple_pressed`), and `count` in
  event_data (mapped to HA standard `multi_press_end`). Requires gateway
  ≥ 1.6.0 with the add-on **Double and triple click** option enabled.
- Blueprint **`button_standard` v11** — Matter-like labels (short press /
  multi-press / long press / release after long press); double and
  triple press in a standard collapsed Multi-press section.
  Input keys `press_action` / `long_press_action` / `release_action`
  unchanged; new `double_action` / `triple_action`.
  `min_version: 2024.6.0` for collapsed sections.
- Diagnostic sensors per field module: **Model**, **Firmware**, and
  **Last seen by gateway** (timestamp + `source` attribute: arp/http).

### Changed
- Multi-press is **global** (gateway add-on option) — no per-button CONFIG
  switch. Device triggers `double_pressed` / `triple_pressed` appear only when
  `coordinator.gateway_status["multi_press"]` is true. Event entities still
  accept `double_press` / `triple_press` when the gateway emits them.

### Fixed
- **Unload crash** `TypeError: a coroutine was expected, got True` — bootstrap
  cancel was registered as `Task.cancel`, which returns `True` on unload; HA
  then tries to schedule that return value. Wrap so the callback returns
  `None`. Prevents the entry getting stuck in `FAILED_UNLOAD`.
- Options flow aborts cleanly with `not_loaded` when the coordinator is gone
  (e.g. after a failed unload) instead of raising `KeyError`.
- **hassfest** — service descriptions no longer use `D<ch>…` (rejected as HTML);
  rewritten as `D{ch}…` in `strings.json`, translations, and `services.yaml`.

## [1.7.2] - 2026-06-23

### Added
- **Gear menu: "Scan field bus for modules"** — sends `POST /api/v1/discover` to the gateway and shows the result (`{added} added, {changed} updated, {removed} removed` + duration) in a follow-up screen. Replaces the need to find the discover button on the gateway device. Up to ~120 s timeout (same budget as the existing button).
- **Gear menu: "Refresh buttons and module info"** — sends `POST /api/v1/modules/refresh` to the gateway and shows the number of updated modules and buttons. Use this after changing a wall button or IP1100PoE setting on the module itself; the gateway then pushes a WS snapshot so the companion picks up new names/thresholds without an integration reload. Does **not** find new modules — use *Scan field bus for modules* for that.

### Changed
- **`button.ipbuilding_gateway_run_discovery_sweep` renamed** from "Run discovery sweep" / "Discovery sweep starten" to "Scan field bus for modules" / "Modules opzoeken op de veldbus" so the name matches the new menu item. No functional change.

### Fixed
- **HA 2026.6 update-listener reload** — config flow uses `reload_on_update=False`; the update listener schedules reload via `async_schedule_reload` instead of `async_reload`. Prevents a double reload and the deprecation warning that becomes an error from HA 2026.12.

## [1.7.1] - 2026-06-23

### Added
- **`button_standard` v9 (universal 3-slot blueprint)** — third action slot `Release` added (fires only on release after a long press). Sections are now named **Press / Hold / Release**, with Hold and Release optional. The blueprint can now fully configure a dimmer (`light.toggle` / `dim_start` / `dim_stop`) without needing a separate `button_dim` blueprint — that remains as a preset. Blueprint name changed to **"IPBuilding wandknop"**. `mode:` changed from `single` to `queued` (two triggers per hold must run in order). Existing instances keep working: `release_action` default is `[]` and the new trigger is scoped with `from: "long_press"`.

### Changed
- **Blueprint copy revised** — `button_standard` v9, `button_dim` v8 and `button_dim_stepwise` v1 are aligned in content. The `Knop` and `Lamp` input descriptions are unified; the "No helper needed" sentence in `button_dim` is gone; the Matter-pattern reference in the Release description is shortened. No behaviour change.
- **Version header at the bottom** — from 1.7.1 the `# ipbuilding_blueprint_version: N` line sits at the bottom of the blueprint file in lowercase, no longer at the top. Sync in `blueprints.py` now scans the whole file. The `**Blueprint-versie: N.**` marker in the description (operator-visible in HA) is unchanged.
- **Dim blueprint descriptions clarified** — `button_dim` is explicitly marked as the recommended native variant; `button_dim_stepwise` as an experimental alternative with an `input_boolean` helper (HA 2026.3 helper-create caveat applies).

### Breaking
- **`dim_button.yaml` has been removed from the companion.** The deprecation stub shipped since 0.5.0 is no longer included. Existing automations that reference this blueprint stop working once the stub is removed from `config/blueprints/automation/ha_ipbuilding_gateway/`. Migrate by creating a new automation from `button_dim` (or `button_dim_stepwise` if you want the HA stepwise variant) and disabling the old one. Before this release the stub existed only as back-compat for installs that started in the 0.5.0 era.

## [1.7.0] - 2026-06-23

### Added
- **`ha_ipbuilding_gateway.dim_start` and `ha_ipbuilding_gateway.dim_stop` services** (entity-targeted, `light.` only). Start/stop the native hold-to-dim ramp on an IP0300PoE channel via the gateway actions `DIM_START` / `DIM_STOP`. The IP0300PoE dims itself and automatically reverses direction on each subsequent hold — no `repeat` loop, no helper, no step configuration in HA. Requires a gateway add-on with `DIM_START`/`DIM_STOP` support (branch `feature/dimmer-downstream-td`, gateway ≥ **1.1.0**).
- **`button_dim` v8** uses the new services instead of the old `repeat` + `brightness_step_pct` + `direction_helper` + endpoint-trigger logic. Short press → `light.toggle`, hold → `dim_start`, release after hold → `dim_stop`. The `direction_helper` / `dim_step_pct` / `dim_interval_ms` / `dim_boundary_pct` inputs are removed.
- **`button_dim_stepwise` blueprint (alternative)** — the old HA-driven, stepwise dim loop (with `input_boolean` direction helper) remains available as a separate alternative for anyone who does not want the native ramp. Native `button_dim` remains the recommended choice.

### Changed
- **Dimmer `light.toggle` now uses the native `TOGGLE` command** (`T<ch>991000`) instead of `DIM <last>` / `DIM 0`. The light entity overrides `async_toggle`: a short press (and every `light.toggle`) switches via the IP0300PoE’s own last-level memory — robust even when HA’s cached brightness is stale (e.g. after a peer button press the gateway did not see). Relays and parameterised toggles fall back to default behaviour.

## [1.6.0] - 2026-06-22

### Removed
- **`button_cover` blueprint** — unvalidated example without cover hardware in the test setup. Hold-to-move / release-to-stop belongs in a dedicated automation (device triggers on `long_press` + `release`) or via `button_standard` for simple open/close on press.

### Breaking
- **`button_cover` is no longer shipped.** Existing instances on a local copy in `config/blueprints/…/button_cover.yaml` keep working until you delete that file. For curtains: `long_press` → `cover.open_cover` / `cover.close_cover`, `release` → `cover.stop_cover` on the button event entity.

## [1.5.0] - 2026-06-22

### Removed
- **`button_scene` blueprint** — redundant with `button_standard`, which already supports `scene.turn_on` (and mixed actions) via the action-editor. New installs no longer receive this file from the companion package.

### Breaking
- **`button_scene` is no longer shipped.** Existing automation instances that still run on a previously synced copy in `config/blueprints/…/button_scene.yaml` keep working until you delete that file. For new button→scene mappings: use `button_standard` and choose the **Scene: Activate** action for short/long press.

## [1.4.1] - 2026-06-22

### Fixed
- **Race between `single_press` and the trailing `release` in `button_dim` (v6 → v7) and `button_cover` (v6 → v7).** On a short tap the gateway sends `single_press` and `release` in quick succession. The top-level `release` trigger also reacted to that short-press release: in `button_dim` (`mode: restart`) that could cancel the just-started `single_press` toggle (short press then did nothing); in `button_cover` (`mode: single`) the trailing release could undo a configured short-press action via `cover.stop_cover`. The `release` trigger is now scoped with `from: "long_press"`, so it only fires on a release that ends a hold (stop the loop + flip direction / stop the cover). `button_scene` did not have this problem (no release trigger).

### Added
- **`button_scene` v4 / `button_dim` v7 / `button_cover` v7** now trigger directly on `single_press` and `long_press` — no more `wait_for_trigger` or raw `press` subscription. Counterpart of the `button_standard` v7 change from v1.3.0. The gateway classifies the press itself, so the race between raw `press` and `long_press` is gone.
- **`single_press` as entity-state translation** in `entity.event.button.state` for both EN and NL. After v1.3.0 the EventEntity already fired the `single_press` event, but the UI showed "Unknown" as state because the translation was missing. Short presses now correctly show "Single pressed" / "Kort ingedrukt".

### Changed
- **`button_dim` v5 → v7**: `wait_for_trigger` with 600 ms timeout on the press branch is gone; the toggle now hangs directly off the `single_press` event. The `release` trigger is scoped with `from: "long_press"` (see Fixed). The release flip guard (`trigger.from_state.attributes.event_type == 'long_press'`) remains — a short-press release must not flip the dim direction.
- **`button_scene` v3 → v4**: top-level `single_press` trigger replaces the raw `press` trigger. `long_press` unchanged.
- **`button_cover` v5 → v7**: top-level `single_press` trigger replaces the raw `press` trigger for the optional short-press action; the `release` trigger is scoped with `from: "long_press"` (see Fixed).

### Tests
- `test_dim_blueprint_waits_on_press_before_toggling`, `test_dim_blueprint_short_press_continues_on_timeout` and `test_scene_blueprint_activates_scenes_on_press_and_long_press` are updated to enforce the v6 contract: no `wait_for_trigger`, direct `single_press` trigger, no raw `press` in the scene blueprint.

### Migration
- Existing automation instances of `button_scene`, `button_dim` and `button_cover` keep working: input names are unchanged (`press_scene`, `long_press_scene`, `target_light`, `direction_helper`, `cover_entity`, `hold_direction`, `release_action`, `press_action`). `blueprints.py` syncs the blueprint files themselves; the input mapping stays 1-to-1.

### Requirements
- Gateway ≥ **1.1.0** for the `single_press` events. Older gateways do not send `single_press`; in that case the new `button_dim` v6 toggle never fires and the operator must fall back to an older blueprint or update the gateway.

## [1.3.0] - 2026-06-21

### Added
- **`single_press` button event + `single_pressed` device trigger.** The gateway now classifies a short press itself: `single_press` on release under the threshold, `long_press` when the threshold is exceeded. The companion adds `single_press` to the EventEntity event types, fires `ha_ipbuilding_gateway.button_single_pressed` on the HA bus, and tags gesture events with their HA/Matter standard name in `event_data` (`press` → `press_start`, `single_press` → `press_end`, `long_press` → `long_press_start`). Raw `release` stays deliberately untagged (follows both short and long press, so no unambiguous standard equivalent). The automation editor shows a new "Single pressed" device trigger. Requires gateway ≥ 1.1.0 to receive the new `single_press` events.

### Changed
- **`button_standard` blueprint (v7)** now triggers directly on `single_press` and `long_press` — no more `wait_for_trigger` with a 600 ms timeout. The gateway does press-vs-long-press disambiguation, so the race between the 600 ms timeout and the 1.5 s default hold threshold is gone. Requires gateway ≥ 1.1.0.

### Breaking
- **`button_standard` v7 removes old inputs** (`automation_name`, `automation_area`, `press_target`, `long_press_target` and the select actions) in favour of full action selectors. Existing automation **instances** on an earlier `button_standard` version still point at non-existent inputs and must be **recreated** after the update.

### Fixed
- **Blueprint triggers did not fire on event entities.** All
  state triggers in the packaged blueprints (`button_toggle`,
  `button_standard`, `button_dim`, `button_cover`, `button_scene`,
  `dim_button`) filtered on `to: "press"` / `"long_press"` /
  `"release"` against `state`, while for event entities that
  contains a timestamp. The event type lives on `attributes.event_type`.
  As a result e.g. "Hal R → bureau toggle" never fired, while native
  HA automations (device trigger) did work. Triggers now have
  `attribute: event_type` + `not_from: [unavailable, unknown]`.
  In `button_dim`, templates that compared `trigger.state`
  to event names were also updated.
- **Version bumps** of all blueprints (4 → 5 for `button_toggle`,
  2 → 3 for `button_standard`, 3 → 4 for `button_cover` and
  `button_dim`, 1 → 2 for `button_scene` and `dim_button` stub) so
  [`blueprints.py`](custom_components/ha_ipbuilding_gateway/blueprints.py)
  triggers upgrade sync on existing HA installs.
- **`button_standard.yaml` press/long_press distinction.** On a
  long press both the press and long_press actions fired: the
  gateway broadcasts `press` immediately and (after the hold threshold)
  `long_press` again, so two top-level triggers fired in sequence.
  The action block now uses the `wait_for_trigger` pattern from
  [`button_dim.yaml`](custom_components/ha_ipbuilding_gateway/blueprints/automation/ha_ipbuilding_gateway/button_dim.yaml):
  one trigger on `press`, wait 600 ms for `release` or `long_press`,
  then choose the correct action. Short presses behave
  identically; long presses only run the long_press action.
  Version bump 3 → 4.
- **`button_standard.yaml` timeout `UndefinedError`** (v4 had a
  typo in the guard). Home Assistant sets `wait.trigger` to `none`
  on timeout — **not** the whole `wait` variable. The v4 guard
  `wait is none` therefore never matched the timeout path, and the
  subsequent `wait.trigger.to_state.attributes.event_type` access
  on `none` threw `UndefinedError: 'None' has no attribute 'to_state'`
  in the log on every short press. v5 follows the community convention
  (HA forum + Awesome HA Blueprints): `wait.trigger is none` for
  the timeout path (→ press action as soft fallback) and
  `wait.trigger is not none` for the event path. Pattern is
  identical to what `button_dim.yaml` already did. Version bump 4 → 5.
- **`button_dim.yaml` short press did nothing when follow-up was missing.**
  The short-press `wait_for_trigger` had no `continue_on_timeout: true`,
  and the guard was `wait.trigger is not none and ... == 'release'`. When
  the gateway for any reason did not send `release` or `long_press`
  within 600 ms (slow bus, race, firmware bug), HA stopped the
  automation on timeout and never ran the toggle — the operator
  pressed the button and nothing happened. v5 adds
  `continue_on_timeout: true` plus a `wait.trigger is none`
  fallback branch that still runs the toggle (Hue-style: the operator
  expects feedback). Version bump 4 → 5 (`button_dim.yaml`).
- **`button_standard.yaml` v6 — action selector for full freedom.**
  The v5-fixed `select:` (None / On / Off / Toggle / Activate scene)
  + `target:` selector per phase are replaced by one `selector:
  action:` input per phase. The operator now gets the full HA
  action editor (as with a normal automation) and can choose any service,
  any target and all data (brightness, transition, helpers, scripts,
  notifications, …). The blueprint only still disambiguates
  press vs long press; the scene guard (`press_has_scene` /
  `long_press_has_scene`) and fixed service choices are gone.
  Pattern follows the HA community convention: `sequence: !input
  press_action` in a `choose:` branch. Version bump 5 → 6. Existing
  "Hal R → Bureau" instances lose their `press_target` reference;
  recreating the automation from this blueprint is required
  (`blueprints.py` syncs the file itself, but the input
  names have changed).

### Changed
- **`button_toggle` v5**: back to the **`target:` selector** (HA
  Motion-activated Light UX). The `entity:` selector from v2/v4 was
  too narrow for the dominant operator flow ("toggle the light(s) in
  this room"). `light_target` now accepts one or more
  entities, a device or a whole area via the Entity /
  Device / Area tabs. The action passes the input straight through
  (`target: !input light_target`) so multiple targets or an
  area toggle are supported.

### Tests
- `test_toggle_blueprint_uses_target_selector` replaces the
  inverted entity-only test.
- `test_button_blueprints_use_event_type_attribute_on_triggers` is
  a new regression test that for every blueprint asserts
  `attribute: event_type` is on the trigger.
- Dim template assertions now refer to
  `attributes.event_type` instead of `state`.

### Migration
- Existing automations created from the old `button_toggle` blueprint
  keep their saved YAML (including the incorrect
  `to: "press"` without `attribute`); those must be **recreated**
  or have the trigger + target fixed manually. Blueprint sync
  only upgrades the blueprint file itself.
- Legacy `ipbuilding_gateway_ha/button_toggle.yaml` on HA can
  be deleted manually; the v5 version lives under
  `ha_ipbuilding_gateway/`.

### Removed
- **`button_toggle.yaml`** — removed. Combining
  `button_standard` with the action selector (choose
  `homeassistant.toggle` as service on a `target:` of lights /
  switches / area) covers the same flow with more freedom. No
  new instances from this blueprint; existing
  automations keep working on their saved YAML until the
  operator deletes them or recreates them from
  `button_standard.yaml`.

## [1.2.2] - 2026-06-19

### Changed
- **Integration is now named "IPBuilding Gateway"** instead of "IPBuilding Gateway Companion". The `manifest.json` `name` is updated; the device tree in the Companion remains gateway → module → channel.

### Added
- **Discovery TXT schema v2**: new TXT fields `sw` (alias of `version`), `host`, `port` and `mac` are now read. `DISCOVERY_SCHEMA_VERSION` is bumped to 2.
- **`mac` and `sw_version` in `GatewayDiscoveryInfo`**. Empty `mac` is passed as `None` (Supervisor add-on has no unique interface MAC).

### Changed
- **mDNS-first discovery** (like Shelly). `async_step_zeroconf` now also works for Supervisor add-ons — the duplicate guard `already_discovered_addon` is removed. Both discovery paths (zeroconf and HassIO) use the same `async_step_confirm` step.
- **Naming on add (D3)**: one new `confirm` step replaces `hassio_confirm` and `discovery_confirm`. Default name = first 8 characters of `instance_id` (or `gateway` as fallback); the operator can change it. The chosen name goes into the config-entry title (`IPBuilding Gateway (<name>)`) and into the `flow_title` of the Discovered card.
- **`async_step_hassio` now reads `instance_id`** from the Supervisor `config` payload, so the unique_id between zeroconf and HassIO discovery is aligned. Fallback is the Supervisor discovery UUID.
- **Translations**: new `flow_title` and `confirm` step in `strings.json`, `translations/nl.json` and `translations/en.json`. Placeholders `{addon}`, `{version}`, `{url}` and `{name}` are now used in one description block.

### Tests
- New tests: `tests/test_discovery_parser.py` (schema v2 + mac + sw fallback) and `tests/test_config_flow_confirm.py` (default name truncation, `flow_title` template, refactor smoke tests).

### Requirements
- Gateway ≥ **1.0.4** to use the new TXT fields. Older gateways keep working thanks to fallback to `version`/`base_url`.

## [1.2.1] - 2026-06-19

### Fixed
- **Supervisor discovery now accepts custom-repo slugs.** `async_step_hassio` in `config_flow.py` uses a suffix match (`*ipbuilding_gateway`) instead of strict equality. This makes the IPBuilding Gateway Companion appear in **Settings → Devices & services → Discovered** even when the add-on is installed via a custom repository (slug such as `3059e002_ipbuilding_gateway`). The fixed store slug `ipbuilding_gateway` of course still works.

## [1.2.0] - 2026-06-19

### Breaking
- **Onboarding wizard removed** from the pairing flow. On a fresh install the gear menu (`Configure`) is where the operator explicitly maps gateway rooms to HA areas. The `_suggest_channel_areas` silent mapping (onto existing areas with the same name) and the `suggested_area` hint on devices keep working.
- **Button import removed.** The wizard imported IP1100PoE button → action mappings from `getButtons` into `automations.yaml`; this must now go through the packaged blueprints (`button_standard`, `button_toggle`, `button_dim`, `button_cover`, `dim_button`) or custom HA automations.
- **Pre-change snapshot:** the last version with the full wizard is tagged as `v1.1.0-with-onboarding-wizard` on `b80346f` — use `git checkout v1.1.0-with-onboarding-wizard -- <paths>` to recover the wizard code.

### Added
- **Room → area mapping as a gear option.** The options flow has one menu item *Map rooms* (`map_rooms`) that shows an `AreaSelector` per gateway room. An empty field falls back to an HA area with the same name (or creates one); the choice is stored in `entry.options[CONF_ROOM_MAPPINGS]` and reapplied by `__init__._apply_stored_room_mappings` on every reload.
- **Map rooms opens automatically** right after adding a gateway. `_maybe_offer_room_mapping` starts the options flow itself (`hass.config_entries.options.async_init`) as soon as gateway rooms are known and no mapping is stored yet; `async_step_init` then skips the menu and shows *Map rooms* immediately. A new `entry.options[CONF_ROOM_MAPPING_OFFERED]` flag ensures this happens only once per gateway, even if the operator closes the screen without saving.

### Changed
- `config_flow.py`: all discovery paths (`async_step_user`, `async_step_hassio_confirm`, `async_step_discovery_confirm`) now call `async_create_entry` directly. No `_ob_*` state, no wizard spinner left in the pairing flow.
- `async_step_hassio_confirm` now takes `host`/`port` from `self._discovery_info` (latent `NameError` in the old code when the form was opened without `user_input`).
- `options_flow.py` rewritten as one `IPBuildingOptionsFlowHandler(OptionsFlow)` with menu `["map_rooms"]` — no more `OnboardingFlowMixin`.
- `_apply_onboarding_results` renamed to `_apply_stored_room_mappings` and only does room mapping; button import is gone.
- Debug agent-log blocks in `config_flow.async_step_hassio` and `_import_button_automations` removed.

### Removed
- Wizard modules: `onboarding_flow.py`, `gateway_rest.py`, `button_automation_builder.py`, `automation_store.py`, `target_resolver.py`, `button_mapping.py`.
- Constants: `CONF_ONBOARDING_COMPLETED`, `CONF_ONBOARDING_SKIPPED`, `CONF_IMPORT_BUTTONS`, `CONF_BUTTON_AUTOMATIONS`.
- i18n: all `ob_*` / `onboarding_*` steps, `preparing` / `discovery` / `modules_refresh` progress keys, `onboarding_complete` abort.
- Tests: `test_onboarding_wiring.py`, `test_button_automation_builder.py`, `test_button_mapping.py`, `test_automation_store.py`.

## [1.1.0] - 2026-06-19

### Added
- **Onboarding wizard in the pairing flow.** After adding the gateway the wizard runs immediately — *rooms → areas* → *overview of new entities* → *import buttons* — before the integration is created. This replaces the bare entity overview as the first screen.
- **Room → HA area mapping.** Gateway room names are shown as field labels and mapped to Home Assistant areas; an existing area with the same name is preselected and missing areas are created. Applies to relays/dimmers and IP1100PoE buttons.
- **Button automations are actually created** in `automations.yaml`: per configured button action a HA device-trigger automation with alias `"<button> → <target>"`, action `on`/`off`/`toggle` per the input module, and a stable `ipb_map_*` id (idempotent — hand-made automations are kept). The integration automatically calls `automation.reload`.
- **Button targets are prefilled** in the "run wizard again" flow from the existing input-module mapping.
- IP1100PoE buttons are **enabled** by default in the entity registry; inactive relay/dimmer channels (`active: false` in `devices.json`) remain disabled+hidden.

### Changed
- The onboarding wizard now runs **in the config flow** instead of an automatically started OptionsFlow. The OptionsFlow remains available for *Configure → run wizard again*.
- **Discovery scan removed** from the wizard. A sweep now only runs silently when the gateway does not yet know any devices (fresh install).
- Button automations are now **enabled by default** and use the modern `triggers`/`conditions`/`actions` schema. `allOn`/`allOff` are skipped for now instead of writing an invalid module-scope group.

### Fixed
- **Coordinator crash on every refresh** and failed onboarding discovery: the per-entity listener dict collided with `DataUpdateCoordinator._listeners` (renamed to `_entity_listeners`).
- **Empty wizard menus/labels:** onboarding translations lived under the wrong flow section; they are now in the right place. Dynamic fields (rooms, buttons) are keyed by name so the label is correct.
- **Wizard stuck after the room step:** invalid `show_progress` transition plus a reload mid-wizard that pulled the coordinator out from under it (`KeyError`).
- **Unload error** `'_asyncio.Task' object is not callable`: the bootstrap sweep registered a Task instead of a callable on `async_on_unload`.
- No more scan screen when pairing an already populated gateway.

## [1.0.0] - 2026-06-18

### Breaking
- **HA domain renamed** from `ipbuilding_gateway_ha` to `ha_ipbuilding_gateway`. This is a **breaking change** for existing HA installs. Remove the old integration from Settings → Devices & Services, reinstall via HACS, and update your Lovelace cards, scripts and automations to use the new entity IDs (`light.ha_ipbuilding_gateway_*`, `switch.ha_ipbuilding_gateway_*`, `event.ha_ipbuilding_gateway_*`, `sensor.ha_ipbuilding_gateway_*`). Rename the folder `config/blueprints/automation/ipbuilding_gateway_ha/` yourself to `config/blueprints/automation/ha_ipbuilding_gateway/` (or recreate the blueprints from the UI). No data loss in `devices.json` (gateway side). See the [README migration section](README.md#upgrading-from-a-pre-10-install) for the full steps.
- **Bus event types** renamed: `ipbuilding_gateway_ha.button_pressed`, `.button_long_pressed`, `.button_released` → `ha_ipbuilding_gateway.button_pressed`, `.button_long_pressed`, `.button_released`. HA Core events follow automatically because they are built via `f"{DOMAIN}.{suffix}"`; any hardcoded references in custom automations must be updated.

### Changed
- **Repository renamed** from `markminnoye/ipbuilding-gateway-ha` to `markminnoye/ha-ipbuilding-gateway`. GitHub sets a 301 redirect so existing clones, issues and HACS custom-repository URLs keep working. (Previous release.)
- **First major release (1.0.0)** — marks the first stable version of the full field-bus hub + companion stack.

## [0.4.3] - 2026-06-18

### Fixed
- **Correct light state immediately after a restart.** Before this version the companion set every channel for which the gateway had not (yet) passed a real on/off state to "off" — including relay channels still waiting for their first UDP command, and dimmer channels that had not yet returned a level reply. A fresh restart of the gateway or companion therefore looked like "everything off", even when lights were on. The companion now maps "unknown" and "inactive" cleanly to an unknown state in Home Assistant, so HA shows "Unknown" instead of "off" until the gateway delivers the first real status. Works together with [IPBuilding Gateway v0.4.3](https://github.com/markminnoye/IPBuilding-Gateway/releases/tag/v0.4.3), which fetches live channel status at startup so the first snapshot is correct immediately.

## [0.4.0-rc.11] - 2026-06-18

### Changed
- **Packaged blueprints no longer in the HA Blueprint picker** — `async_install_packaged_blueprints` is now a no-op. The blueprint files remain in the repo (reference + source-only tests), but are no longer copied to `config/blueprints/automation/ipbuilding_gateway_ha/`. The public API (`async_install_packaged_blueprints`, `invalidate_packaged_blueprints_cache`) remains for backward compatibility. The README section is rewritten: "Button automations" points the operator to community blueprints (Z2M Hue Dimmer Ultimate Controller, IKEA STYRBAR) and the standard HA flow.
- **`manifest.json` dependencies** — `blueprint` is removed (the companion no longer ships anything to HA blueprints).

### Notes
- **Existing installs** — `config/blueprints/automation/ipbuilding_gateway_ha/*.yaml` files remain on HA. The operator can delete them via the HA Blueprint picker or the filesystem. Existing automations that reference `use_blueprint` keep working until the operator removes the blueprint files.
- **New installs** — The Blueprint picker no longer shows IPBuilding blueprints. Operators build actions via community blueprints or the standard HA flow.

## [0.4.0-rc.10] - 2026-06-18

### Changed
- **`button_toggle.yaml` (v4)** — `automation_name` input and `alias: !input automation_name` are removed. The automation name is now filled in directly in the Home Assistant save popup (which always opens when creating a new automation). The popup prefills the blueprint name "IPBuilding wandknop — toggle"; the operator types the desired friendly name and confirms. This avoids the mismatch between the blueprint input and the popup default.

## [0.4.0-rc.9] - 2026-06-18

### Notes
- **`button_cover.yaml` is an example** — the blueprint name now starts with `[Voorbeeld]` and the description explains that the companion developers have no `cover` hardware to validate this. Please report bugs via GitHub Issues with label `cover-blueprint`.
- **`button_toggle.yaml`** — the sentence "The automation area is asked by Home Assistant in the popup that appears after you press 'Opslaan' — it is not a blueprint input" is removed from the description to avoid duplicate explanation.
- **HA frontend rename popup** — Home Assistant always opens a "rename" popup when creating a new automation, including from a blueprint. The popup fills in the **blueprint name** as default (e.g. "IPBuilding wandknop — toggle"), not the `automation_name` from the blueprint. `alias: !input automation_name` is still written correctly into the saved YAML; adjust the name in the popup before confirming if you do not want the blueprint name.

## [0.4.0-rc.8] - 2026-06-18

### Changed
- **`button_toggle.yaml` (v2) — minimal UX** — replaces the `target:` selector (which showed tabs for entity / device / area plus an "Add target" button) with an `entity:` selector with `multiple: false`. The `target_kind` and `target_area` fields are removed; the toggle blueprint is now one entity on one button. The `automation_area` input is removed: HA asks for the area in the popup that appears after "Save", and a second "Area" field in the blueprint was confusing.
- **`button_standard.yaml` (v2) — target selector + scene guard** — replaces 8 separate fields (`*_target_kind`, `*_entity_target`, `*_area` per phase) with one `target:` field per phase. The `target:` selector automatically offers entity, multiple entities, or an area in one widget. A derived `*_has_scene` variable checks whether the target contains a scene; `on`/`off`/`toggle` are defensively skipped when that is the case, and `activate_scene` is skipped when there is no scene in the target.

## [0.4.0-rc.7] - 2026-06-18

### Fixed
- **YAML 1.1 boolean coercion in blueprint `select` options** — `value: on` and `value: off` were read by YAML as booleans (`True`/`False`), so HA’s `select` validator rejected them with `expected str for dictionary value @ data['...']['value']. Got None`. All option fields in `button_standard.yaml` are now explicitly quoted (`"on"`, `"off"`, `"none"`, `"toggle"`, `"activate_scene"`). Regression guard in `tests/test_blueprints_source.py::test_select_option_values_are_strings`.

## [0.4.0-rc.6] - 2026-06-18

### Added
- **Blueprint set for IP1100PoE buttons** — four targeted blueprints in `custom_components/ipbuilding_gateway_ha/blueprints/automation/ipbuilding_gateway_ha/`: `button_toggle` (short press → toggle), `button_standard` (short + optional long, with on / off / toggle / scene for entity or all lights in a room), `button_dim` (toggle + dim during hold, replaces `dim_button.yaml`) and `button_cover` (hold = open or close, release = stop).
- **Versioned blueprint sync** — each packaged blueprint has a `# ipbuilding_blueprint_version: N` header. The companion overwrites existing blueprints on HA when the package version is higher. Files with a `# user_modified: true` marker remain untouched.

### Fixed
- **Dim blueprint `max: 1` error** — `button_dim.yaml` uses only `mode: restart`; the invalid `max: 1` is removed so `Message malformed: value must be at least 2 @ data['max']` no longer occurs on save.
- **Helper UX text** — `button_dim.yaml` now explains the difference between the **Name** (may contain spaces) and the **Entity ID** (only `a-z`, `0-9`, underscores) of the `input_boolean` direction helper.
- **Device trigger no longer leaks across other buttons** — `async_attach_trigger` in `device_trigger.py` fell back to an empty `event_data` filter when the hardware id could not be found. An empty filter matches *every* `ipbuilding_gateway_ha.button_*` event, so an automation on one button could fire on a physical press of another. The handler now fails hard with a `ValueError` when the hardware id is missing; regression guard in `tests/test_device_trigger.py`.

### Deprecated
- **`dim_button.yaml`** is replaced by `button_dim.yaml` and remains only as a stub. The stub fires a `persistent_notification` as soon as an existing automation still uses it. Migrate by creating a new automation from `button_dim.yaml` and disabling the old one.

## [0.4.0-rc.5] - 2026-06-18

### Fixed
- **hassfest:** `automation` and `blueprint` added to `manifest.json` `dependencies` (required for packaged blueprint installation).
- **Manual config flow pre-fills the host with `127.0.0.1`** — the Supervisor add-on contract. Operators adding the integration by hand used to see an empty host field; the loopback hint now matches the HassIO discovery flow, so a fresh add-on install confirms out of the box. Standalone installs (Docker, Pi, remote) can still override the value.
- **discovery_completed + bootstrap one-shot** — more robust handling of discovery events and the first REST bootstrap.

### Removed
- **Debug switch to toggle gateway field-bus polling.** The `Fieldbus polling (debug)` entity and the related coordinator helpers are removed. The gateway-side `POST /api/v1/debug/fieldbus-polling` endpoint is likewise removed (see [`IPBuilding-Gateway` v0.4.3](../../IPBuilding-Gateway/blob/main/ipbuilding_gateway/CHANGELOG.md)).

## [0.4.0] - 2026-06-17

### Added
- **Dim-button blueprint** (`ipbuilding_gateway_ha/dim_button.yaml`): toggle on short press, dim during hold with automatic direction flip on release and at 1% / 100%.
- Packaged automation blueprints are copied automatically to `config/blueprints/automation/` on integration setup when they are still missing there; existing files are not overwritten.
- IP1100PoE buttons: `long_press` and `release` event types on the event entity, plus bus events `ipbuilding_gateway_ha.button_long_pressed` and `ipbuilding_gateway_ha.button_released` (alongside the existing `button_pressed`).
- Three device triggers per button in the automation editor: **Button pressed**, **Long pressed**, **Released**.

### Changed
- Physical buttons and the discovery-sweep button are split across the `event` and `button` platforms; hardware buttons get a stable `event.<hardware_id>` entity_id.
- **Refreshed icon set for the integration.** The companion icon (HACS category, Devices & services) and the brand icons in `brand/` are replaced by a new set. The display in Settings → Devices & services and the brand icon grid now use the new design; entity behaviour is unchanged.

### Fixed
- Dim-button blueprint: entity selector uses the `filter:` format (HA 2026.3+); `direction_helper` variable in the dim-repeat action.

## [0.3.8] - 2026-06-16

### Fixed
- **Channel entities (lights, switches, power sensors, IP1100PoE button events) failed to appear on startup**: the REST fallback left `coordinator.data` as a list while the four platforms (and the area-suggestion helper) read it as a dict, so only the three module devices were ever registered. Platforms now go through `IPBuildingCoordinator.devices_snapshot()`, and the REST fetch also populates the internal device cache so `coordinator.data` matches the WebSocket shape.

## [0.3.7] - 2026-06-16

### Changed
- **Device name for the three field modules now shows `Relay module`, `Dimmer module`, `Input module`** instead of `Relay` / `Dimmer` / `Input`. The suffix makes it explicit that the card in onboarding "Name and assign" represents the physical module, not one of the channels. Channel devices in "Device info" keep their short role label (`Relay` / `Dimmer` / `Input`) so the overview stays compact with 16+ channels. The SKU title (`IP0200PoE` / `IP0300PoE` / `IP1100PoE`) is unchanged.

## [0.3.6] - 2026-06-16

### Fixed
- **IP1100PoE buttons now appear as disabled** instead of unavailable. New buttons from the gateway snapshot are registered hidden and disabled by default; enable them yourself under Settings → Devices & entities.

## [0.3.5] - 2026-06-16

### Notes
- **Lockstep bump** with the add-on. No code changes in the companion. Requires add-on **v0.3.5** for automatic Supervisor updates.

## [0.3.3] - 2026-06-16

### Fixed
- **Button entities failed to load** with `UnboundLocalError: cannot access local variable 'callback'`: the WS listener inside `async_added_to_hass` was named `callback`, which shadowed the imported `@callback` decorator from Home Assistant.
- **Duplicate unique ID errors** for lights, sensors and buttons on startup: the debounced diff triggered by the first WebSocket `snapshot` treated every channel as new because `_known_devices` was still empty after the initial REST/platform setup. The coordinator now seeds known devices once all platforms have finished loading.

### Changed
- **Module names are now consistent across all three field modules.** A new `module_device_model` helper returns the canonical hardware SKU (`IP0200PoE`, `IP0300PoE`, `IP1100PoE`) as the `model` field even when the gateway snapshot lacks a factory product label. The Tier-2 module registration and `build_module_hub_device_info` both use it, so onboarding's "Apparaat-info" always shows the SKU as title.
- `module_device_name` now treats the module's IP address and the bare hardware SKU as auto-discovery placeholders. Operators who set a real name in `devices.json` (e.g. `Kelder relais`) are unaffected; auto-discovery and pre-provisioned installs (e.g. legacy `name: "10.10.1.50"`) now show the role label (`Relay` / `Dimmer` / `Input`) instead of an IP.

### Notes
- Requires add-on **v0.3.3** for the SKU backfill; older add-ons keep working thanks to the defensive fallback in the companion, but do not get automatic `devices.json` correction.

## [0.3.1] — 2026-06-16

### Changed
- Companion version bumped to **0.3.1** to keep lockstep with the gateway add-on. This is a build-only release on the add-on side: the add-on image at tag `v0.3.0` was missing the `zeroconf` package at runtime because the build context picked up a stale copy of `requirements-gateway.txt`. The companion code itself is unchanged from 0.3.0.

## [0.3.0] — 2026-06-16

Bundle release: everything since **0.1.0** (plus changes that only lived under
0.1.1–0.2.2) is in this version. Intermediate tags were not
all published as separate releases — upgrade in one step to
**v0.3.0** together with add-on **v0.3.0**.

### Added
- The integration appears in **Settings → Devices & Services → Discovered** (same UX as Shelly, ESPHome, Music Assistant). On HA OS via Supervisor discovery; with a standalone gateway via mDNS (`_ipbgw._tcp.local.`). Both paths are deduplicated to one entry.
- **Gateway status sensor** (diagnostic): shows `ok` / `degraded` / `unhealthy`, version, uptime and open issues from the gateway. Works via `GET /api/v1/status` and live WebSocket updates.
- **Discovery sweep button** on the gateway device: starts a forced field-bus scan (`POST /api/v1/discover`) from Home Assistant.
- **Physical IP1100PoE buttons as routable event entities** (issue #4): each button from `getButtons` appears as `event.<name>` under the IP1100PoE device; presses trigger the entity state event plus the bus event `ipbuilding_gateway_ha.button_pressed`. Entities are created dynamically after a discovery sweep or `POST /api/v1/modules/refresh` (gateway handles the snapshot broadcast). Use a **state trigger** on `to: "press"` in automations.
- Inactive channels (`active: false`) appear as disabled, hidden entities — enable via **Settings → Devices & entities** when the wiring is ready (since 0.1.2).
- Dashboard example (`dashboard.md`) with Lovelace glance, discover button and issues card.

### Changed
- Config flow rewritten to the Music Assistant pattern: separate `hassio` and `zeroconf` steps with confirmation; manual host/port remains the fallback.
- **Three-tier device tree:** IPBuilding Gateway → module (Relay / Dimmer / Input) → channel entity. Modules are registered explicitly; `sw_version` comes from the gateway status API.
- Channel devices show **Relay** / **Dimmer** / **Input** instead of the hardware SKU in the UI; hardware model stays on the module device.
- Rooms from `devices.json` (`room`) are proposed as **suggested area** during onboarding; existing manual area assignments are not overwritten.
- Matching icons for lights and switches (dimmer, lamp, fan, outlet, …).
- WebSocket connection calmer: server-side keep-alive 60 s, shorter reconnect backoff, less noise in the HA log on normal cycles.
- Add-on and companion are released in lockstep on the same version number.

### Fixed
- **Discovered list works:** zeroconf parser uses SRV host/port (not TXT only); without this fix nothing appeared in Discovered despite a correct broadcast.
- **Dimmers work:** light and switch entities send `DIM` instead of `ON`/`OFF`; brightness from the service call or last known level.
- **Inactive channels:** `active: false` disables entities instead of removing them; registry sync applies disable/hide correctly.
- **Power sensors:** no more duplicated device name in the display name (e.g. `sensor.achterdeur_licht_power` instead of a double).
- Home Assistant **2026.3** compatibility for dimmer `color_modes` and entity naming.
- Translations and manifest meet hassfest/HACS (`strings.json` schema, repo topics).

### Notes
- Install **companion v0.3.0** and **add-on v0.3.0** together. From **0.1.0** this is the only upgrade step you need.
- Requires a gateway that exposes `modules` and status in the API/WebSocket (add-on v0.3.0).

## [0.2.2] — 2026-06-15

> Included in **[0.3.0]** above.

### Changed
- Module and channel devices now show **Relay** / **Dimmer** / **Input** instead of the hardware SKU (`IP0200PoE`, `IP0300PoE`, `IP1100PoE`) in Apparaat-info and the “Verbonden via …” chain. The hardware model remains on the parent module device's `model` field; operator-configured module names in `devices.json` are still respected (issue #2 follow-up).
- Channel `device_info` now forwards the gateway's `room` field as `suggested_area`, so the onboarding “Naam geven en toewijzen” screen preselects the matching HA area. After platform setup, `_suggest_channel_areas` resolves existing HA areas by name and assigns the `area_id` automatically — without overwriting an operator's manual area assignment (issue #2).
- Light entities now pick their icon from the channel's `semantic_type` and `device_type` via `entity_icon()` in `entity.py`: `mdi:brightness-6` for dimmer-driven lights, `mdi:lightbulb` otherwise. Switch entities now set the same icon mapping, picking between `mdi:fan`, `mdi:power-plug`, `mdi:toggle-switch-variant`, etc., instead of the default switch icon.

## [0.2.1] — 2026-06-15

> Included in **[0.3.0]** above.

### Fixed
- The three field modules (`IP0200PoE`, `IP0300PoE`, `IP1100PoE`) now appear as devices in Home Assistant. The previous release relied on the `via_device` link to auto-create the module devices, but Home Assistant does not create a parent device from a `via_device` reference alone — a hub that fronts other devices must register them explicitly. The companion now fetches `GET /api/v1/modules` at setup and registers the gateway plus each module device, so the full gateway → module → channel tree is built even for modules whose channels are all inactive (e.g. the input module).

## [0.2.0] — 2026-06-15

> Included in **[0.3.0]** above.

### Changed
- Companion now builds a 3-tier device tree: `IPBuilding Gateway` → per-module device (e.g. `IP0200PoE`) → per-channel entity. Channels reference their parent module via `via_device` (module devices are registered explicitly in v0.2.1).
- Channel `device_info` now uses the parent module's product model (`IP0200PoE` / `IP0300PoE` / `IP1100PoE`) instead of the channel's `semantic_type` or `device_type`.
- Tier-1 gateway device now shows `model="IPBuilding Gateway Software"` and `sw_version` from the gateway's `/api/v1/status` (issue #14).
- Manifest metadata updated: `iot_class: local_push` (was `local_polling`), and added `quality_scale`, `issue_tracker`, `documentation`.
- The companion coordinator now consumes the `modules` field from the WebSocket `snapshot` payload (previously dropped) and exposes it via a `modules` property plus a `module_for_channel` helper for the entity platforms.

### Notes
- Requires the IPBuilding Gateway add-on (or standalone gateway) to expose `modules` in its `GET /api/v1/modules` and WebSocket `snapshot` response. This is already shipped in the gateway repo.

## [0.1.5] — 2026-06-15

> Included in **[0.3.0]** above.

### Fixed
- Power-sensor entities no longer have the device name embedded in the
  entity's display name. The previous `f"{name} Power"` description combined
  with `has_entity_name=True` produced names like
  `achterdeur_licht achterdeur_licht Power`, which HA slugged to
  `sensor.achterdeur_licht_achterdeur_licht_power`. The description now
  uses `name="Power"`, so a device named "achterdeur_licht" produces a
  clean `sensor.achterdeur_licht_power`.

## [0.1.4] — 2026-06-14

> Included in **[0.3.0]** above.

### Fixed
- Dimmer light and switch entities now send `DIM` commands to the gateway
  instead of `ON`/`OFF`. The northbound API only accepts `DIM` for dimmer
  modules; relay-style commands were rejected with HTTP 400, so dimmers
  appeared broken while relays worked.
- Dimmer turn-on uses the brightness from the service call (`kwargs`) when
  present, otherwise the last known level, otherwise 100%.
- Dimmer detection uses `device_type == "dimmer"` instead of the presence of
  a `level` field in the initial snapshot.

## [0.1.3] — 2026-06-14

> Included in **[0.3.0]** above.

### Fixed
- Channels with `active: false` are now correctly **disabled** in Home
  Assistant instead of being deleted. The runtime diff in `coordinator`
  detected active-flips via `added & removed`, which is always empty (the two
  sets are disjoint by construction), so flipping a channel to `active: false`
  removed its entity and registry entry instead of disabling it. Flips are now
  detected on the device id alone.
- `coordinator` registry sync no longer no-ops: it matched entries with
  `async_get_entity_id(DOMAIN, DOMAIN, …)` (wrong entity domain), so the
  disable/hide flags were never applied. Reconciliation now scans the registry
  by `platform` + `unique_id`.
- Cold start: a channel already set to `active: false` whose entity was
  previously registered *enabled* is now disabled on the next snapshot
  (`apply_active_registry_defaults` only affects brand-new registry entries).
  A user who manually re-enables a disabled entity is no longer fought on every
  steady-state snapshot — only freshly-seen and flipped ids are reconciled.

### Changed
- WebSocket keep-alive: client-side `heartbeat` and `receive_timeout` are
  disabled. The gateway (server-side) drives the PINGs at 60s intervals.
  This avoids a known aiohttp 3.13.5 client-PONG race (aio-libs/aiohttp#12030)
  that caused a reconnect every 30s in simulated mode.
- Reconnect backoff capped at 5s (was 30s) and a ±20% jitter is applied to
  each sleep so simultaneous gateway restarts don't produce a thundering
  herd of reconnects.
- `_receive_loop` now distinguishes graceful server-initiated closes
  (DEBUG log) from real errors (WARNING), so the HA log stays readable
  during normal keep-alive cycles.

### Notes
- Gateway must also be updated: `gateway_api.py` heartbeat raised 30 → 60.

## [0.1.2] — 2026-06-14

> Included in **[0.3.0]** above.

### Added
- Shared `entity.apply_active_registry_defaults` helper. Channels reported by
  the gateway with `active: false` (e.g. relays that are wired-up but not yet
  configured) are now registered in Home Assistant as
  `entity_registry_enabled_default=False` and
  `entity_registry_visible_default=False`, matching the HA-IPBuilding button
  pattern. The operator enables them from Instellingen → Apparaten & entiteiten
  when the wiring is done.

### Changed
- Requires the IPBuilding Gateway add-on to expose inactive channels in its
  `GET /api/v1/devices` and WebSocket `snapshot.devices` response.

## [0.1.1] — 2026-06-12

> Included in **[0.3.0]** above.

### Fixed
- Dimmer lights no longer declare both `BRIGHTNESS` and `ONOFF` in
  `supported_color_modes` — Home Assistant 2026.3 rejects that combination.
- Light entity names are derived from the device registry (`name=None` +
  `has_entity_name=True`) instead of duplicating the device name on the entity.

### Changed
- Consolidated `LightEntityDescription` / `SwitchEntityDescription` imports
  to match Home Assistant 2026.3 module layout.

## [0.1.0] — 2026-06-05

> Replaced by **[0.3.0]** for upgrades; kept for history.

### Added
- First publication as a standalone HACS Integration
- Light entities (relay ON/OFF + dimmer BRIGHTNESS)
- Switch entities (relay/dimmer with semantic_type switch/plug/fan)
- Button event entities (IP1100PoE physical button → `ipbuilding_gateway_ha.button_pressed` event)
- Sensor entities (per-channel current_watt)
- Supervisor auto-detection (no manual host/port needed when the add-on is active)
- Manual config flow with validation via `GET /api/v1/devices`
- WebSocket coordinator with automatic reconnect
- Dutch and English translations

[Unreleased]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.9.0...HEAD
[1.9.0]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.8.3...v1.9.0
[1.8.3]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.8.2...v1.8.3
[1.8.2]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.8.1...v1.8.2
[1.8.1]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.7.2...v1.8.0
[1.7.1]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.7.0...v1.7.1
[1.7.0]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.4.1...v1.5.0
[1.4.1]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.3.0...v1.4.1
[1.3.0]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.2.2...v1.3.0
[1.2.2]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/markminnoye/ha-ipbuilding-gateway/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/markminnoye/ha-ipbuilding-gateway/releases/tag/v1.0.0
[0.4.3]: https://github.com/markminnoye/ha-ipbuilding-gateway/releases/tag/v0.4.3
[0.3.0]: https://github.com/markminnoye/ipbuilding-gateway-ha/compare/v0.1.0...v0.3.0
[0.2.2]: https://github.com/markminnoye/ipbuilding-gateway-ha/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/markminnoye/ipbuilding-gateway-ha/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/markminnoye/ipbuilding-gateway-ha/compare/v0.1.5...v0.2.0
[0.1.5]: https://github.com/markminnoye/ipbuilding-gateway-ha/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/markminnoye/ipbuilding-gateway-ha/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/markminnoye/ipbuilding-gateway-ha/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/markminnoye/ipbuilding-gateway-ha/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/markminnoye/ipbuilding-gateway-ha/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/markminnoye/ipbuilding-gateway-ha/releases/tag/v0.1.0

## Version policy

The `ipbuilding-gateway-ha` companion and the **IPBuilding Gateway** add-on
follow **independent semver**. A bump in one repo does not automatically
mean a bump in the other.

- **Patch (0.3.x)**: cosmetic, no impact on the REST/WS wire.
  Works with all gateway versions that support the current wire.
- **Minor (0.x.0)**: new fields or optional WS events. The older
  gateway keeps working, but the companion does not use the new
  fields unless the gateway provides them.
- **Major (x.0.0)**: breaking change. The CHANGELOG then includes a
  `### Breaking:` entry listing incompatible combinations.

Backward compatibility is the norm — a companion version keeps working
with the current gateway until a `### Breaking:` entry says otherwise.
