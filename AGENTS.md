## Linear-tickets aanmaken

- Gebruik bij het aanmaken van issues voor nieuwe features altijd het template 'Nieuwe feature'. Behoud alle secties en vul ze op basis van de beschikbare context. Verzin geen ontbrekende informatie; vermeld onzekerheden onder 'Open vragen en beslissingen'.
- Maak nooit een Linear-ticket aan zonder dat Mark eerst gebriefd is over hoe het ticket eruitziet, wat erin staat en waarom het nodig is. Bestaat er al een passend ticket, werk dat dan bij in plaats van een nieuw aan te maken.
- Noem tickets altijd met hun beschrijvende titel, met het nummer tussen haakjes, bijvoorbeeld "Adresveld: 50-tekensgrens (SR-82)".
- Nieuwe tickets komen in Backlog met het label "Agent". Triage is niet mogelijk.

## Releasen (HACS / Home Assistant)

HACS detecteert nieuwe versies via **GitHub Releases** (niet via losse Git-tags):

1. Bump `"version"` in `custom_components/ha_ipbuilding_gateway/manifest.json`.
2. Voeg een sectie `## [<versie>] - YYYY-MM-DD` toe aan `CHANGELOG.md`.
3. Update de versie-checks in `tests/test_options_flow.py` (`test_manifest_version_bumped`, changelog-check) en draai de volledige testsuite (`.venv/bin/python -m pytest tests/test_light_transition.py tests/test_startup_state_runtime.py -q` en `pytest -q`).
4. Commit op `main`, maak een tag `v<versie>` en push beide (`git push origin main v<versie>`).
5. Maak een **GitHub Release** aan met `gh release create v<versie> --title "v<versie>" --notes "..."` zodat HACS de update ziet.
