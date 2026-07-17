# button_standard → unified Matter-labelled wandknop (v11)

Date: 2026-07-17
Status: approved
Repo: `ha-ipbuilding-gateway` · Base branch: `main`

## Achtergrond

`button_standard` (v10) had drie actie-slots (korte druk / vasthouden /
loslaten) en verwees naar een apart `button_multi` blueprint voor
dubbel-/driedubbelklik. Doel: één universeel blueprint, Matter-achtige
labels, multi-press achter een collapsed sectie.

## Beslissingen

- Uitbreiden `button_standard.yaml`; `button_multi.yaml` verwijderen
  (nooit in productie gebruikt; geen migratie; niet in CHANGELOG).
- Matter: labels/hints in de UI; triggers blijven op
  `attribute: event_type` (niet `standard_event_type`).
- Input-keys stabiel: `press_action`, `long_press_action`,
  `release_action`; nieuw `double_action`, `triple_action` (default `[]`).
- `mode: queued` behouden.
- Blueprint-versie 10 → 11; `homeassistant.min_version: "2024.6.0"`
  (voor `collapsed:` input sections).
- `button_dim` / `button_dim_stepwise` ongewijzigd.

## UI-secties

| Sectie | collapsed | Inputs |
|--------|-----------|--------|
| Algemeen | false | `button_entity` |
| Korte druk (`press_end`) | false | `press_action` |
| Multi-press (`multi_press_end`) | **true** | `double_action`, `triple_action` |
| Lange druk (`long_press_start`) | false | `long_press_action` |
| Loslaten na lange druk (`long_release`) | false | `release_action` |

Multi-press sectie-description: add-on *Dubbel- en driedubbelklik*
vereist; herstart; ~350 ms vertraging op korte druk.

## Triggers

Bestaande: `single_press`, `long_press`, `long_press`→`release`.
Nieuw: `double_press`, `triple_press`. Release-guard blijft
`from: "long_press"`.

## Non-goals

- Geen gateway-wijziging.
- Geen conditionele UI op gateway-status.
- Geen auto-migratie van `button_multi`-instanties.
