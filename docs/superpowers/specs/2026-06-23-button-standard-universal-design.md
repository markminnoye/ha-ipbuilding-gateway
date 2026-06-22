# button_standard → universele wandknop-blueprint (3 slots)

Date: 2026-06-23
Status: approved (design), ready for implementation plan
Repo: `ha-ipbuilding-gateway` · Base branch: `main`

## Achtergrond

`button_standard` (v8) heeft twee actie-slots: **Korte druk** (`single_press`)
en **Lang indrukken** (`long_press`). Door een derde slot **Loslaten**
(`release`) toe te voegen wordt de blueprint universeel: ook een dimmer kan er
volledig in geconfigureerd worden (Indrukken→toggle, Vasthouden→dim_start,
Loslaten→dim_stop), zonder de aparte dim-blueprints nodig te hebben.

De naam "kort en lang" vervalt; de slots heten voortaan **Indrukken /
Vasthouden / Loslaten**.

## Beslissing: release = "long release" (Matter-patroon)

De `release`-actie vuurt **alleen op de release die een lange druk afsluit**,
niet na een korte tik. Dit volgt de cross-ecosysteem-standaard:

- Matter's Switch-cluster (HA `matter/event.py`) onderscheidt expliciet
  `short_release` (loslaten na korte druk) en `long_release` (loslaten na lange
  druk). Dimmer-knoppen binden dim-stop aan **`long_release`**.
- Zigbee/Hue-remotes doen het identiek (hold → release).

Waarom niet "elke release": dan vuurt een korte tik twee slots (Indrukken +
Loslaten). Voor een dimmer betekent dat een losse `dim_stop` (`D…1000`) ná de
toggle — een frame dat we in de captures nooit losstaand zagen en waarvan het
effect onbewezen is. Het long-release-model vermijdt dat volledig.

**Geen gateway-wijziging nodig.** De gateway stuurt al `press → single_press →
release` (tik) en `press → long_press → release` (vasthouden). De blueprint
herkent "release ná long_press" puur met de trigger-conditie `from:
"long_press"` — exact wat `button_dim` nu al doet. Mapping op Matter:

| gateway event | Matter-equivalent |
|---|---|
| `single_press` | short_release (tik klaar) |
| `long_press` | long_press |
| `release` met `from: "long_press"` | long_release |

## Ontwerp

### Inputs (secties)

| Sectie | Input | Label | Selector | Default |
|---|---|---|---|---|
| Algemeen | `button_entity` | Knop | event-entity (deze integratie) | — |
| Indrukken | `press_action` | Actie bij indrukken | `action` | `[]` |
| Vasthouden | `long_press_action` | Actie bij vasthouden | `action` | `[]` |
| Loslaten | `release_action` | Actie bij loslaten (ná vasthouden) | `action` | `[]` |

Alle drie de actie-slots zijn optioneel (`default: []`), zodat de blueprint ook
voor een simpele knop met alleen "Indrukken" bruikbaar blijft.

### Triggers

```yaml
- platform: state            # Indrukken
  entity_id: !input button_entity
  attribute: event_type
  to: "single_press"
  not_from: [unavailable, unknown]
  id: short
- platform: state            # Vasthouden
  entity_id: !input button_entity
  attribute: event_type
  to: "long_press"
  not_from: [unavailable, unknown]
  id: long
- platform: state            # Loslaten — alleen ná een lange druk
  entity_id: !input button_entity
  attribute: event_type
  from: "long_press"
  to: "release"
  id: release
```

### Actie

```yaml
- choose:
    - conditions: [{condition: trigger, id: long}]
      sequence: !input long_press_action
    - conditions: [{condition: trigger, id: release}]
      sequence: !input release_action
  default: !input press_action     # id short
```

### Mode

`mode: queued` (was `single`). Bij vasthouden vuren nu **twee** triggers
(`long_press` daarna `release`); queued voert ze in volgorde uit zodat de
Loslaten-actie nooit gedropt wordt terwijl de Vasthouden-actie nog loopt.

### Overige

- Blueprint-naam: **"IPBuilding wandknop"** (i.p.v. "— kort en lang").
- Versie-header → `# ipbuilding_blueprint_version: 9`; beschrijving bevat
  `**Blueprint-versie: 9.**`.
- Beschrijving verwijst naar de dim-presets als snelkoppeling.

## Dimmer in één blueprint

Volledige dimmer-config zonder helper:

- **Indrukken** → `light.toggle` (gaat via de native `TOGGLE` → `T<ch>991000`).
- **Vasthouden** → `ha_ipbuilding_gateway.dim_start`.
- **Loslaten** → `ha_ipbuilding_gateway.dim_stop`.

## Non-goals

- Geen gateway-wijziging.
- `button_dim` (native) en `button_dim_stepwise` blijven als kant-en-klare
  presets bestaan — `button_standard` is de flexibele universele variant.
- Geen multi-press / dubbelklik in deze iteratie (Matter `multi_press_n` is
  buiten scope).

## Testing

- `tests/test_blueprints_source.py`: `button_standard` houdt zijn
  versie-header + `**Blueprint-versie: 9.**`-marker; blijft geldige YAML.
- Als een bestaande test de slot-structuur of versie van `button_standard`
  pint, die bijwerken naar de drie slots / v9.
- Handmatig: korte tik → alleen Indrukken; vasthouden → Vasthouden gevolgd
  door Loslaten; dimmer end-to-end (toggle / ramp / stop).

## Risico's

- Gedragswijziging `mode: single → queued`: bewust, nodig voor de twee triggers
  per vasthouden. Voor bestaande gebruikers met alleen Indrukken/Vasthouden
  verandert er functioneel niets (er vuurt nog steeds één trigger per tik).
