# Changelog

Alle notable wijzigingen aan deze custom component worden hier gedocumenteerd.

Het format is gebaseerd op [Keep a Changelog](https://keepachangelog.com/nl/1.1.0/),
en dit project volgt [Semantic Versioning](https://semver.org/lang/nl/).

## [Unreleased]

## [0.1.1] — 2026-06-12

### Fixed
- Dimmer lights no longer declare both `BRIGHTNESS` and `ONOFF` in
  `supported_color_modes` — Home Assistant 2026.3 rejects that combination.
- Light entity names are derived from the device registry (`name=None` +
  `has_entity_name=True`) instead of duplicating the device name on the entity.

### Changed
- Consolidated `LightEntityDescription` / `SwitchEntityDescription` imports
  to match Home Assistant 2026.3 module layout.

## [0.1.0] — 2026-06-05

### Added
- Eerste publicatie als zelfstandige HACS Integration
- Light entities (relay ON/OFF + dimmer BRIGHTNESS)
- Switch entities (relay/dimmer met semantic_type switch/plug/fan)
- Button event entities (IP1100PoE fysieke knop → `ipbuilding_gateway_ha.button_pressed` event)
- Sensor entities (per-kanaal current_watt)
- Supervisor auto-detectie (geen handmatige host/poort nodig wanneer add-on actief is)
- Handmatige config flow met validatie via `GET /api/v1/devices`
- WebSocket-coordinator met automatische reconnect
- Nederlandse en Engelse vertalingen

[Unreleased]: https://github.com/markminnoye/ipbuilding-gateway-ha/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/markminnoye/ipbuilding-gateway-ha/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/markminnoye/ipbuilding-gateway-ha/releases/tag/v0.1.0
