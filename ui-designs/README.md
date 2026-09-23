# Golden Stock — two UI designs

Two separate, working interfaces for design review, published alongside the production site:

- **[Compare both designs](https://kartikeyaav.github.io/Golden-Stock/ui-designs/)**
- **[Design II — Research Desk](https://kartikeyaav.github.io/Golden-Stock/ui-designs/v2/)**: warm ivory, forest rail, brass accents and editorial spacing.
- **[Design III — Intelligence Terminal](https://kartikeyaav.github.io/Golden-Stock/ui-designs/v3/)**: midnight surfaces, cyan accents, monospace data, price-scale chart, signal-readiness panel, company setup cards and an interactive 1,000-stock map.

The production landing page and dashboard stay at their existing URLs. No trading rules, scores, jobs or brokerage integrations change.

## Structure

```text
ui-designs/
  index.html          Comparison page
  styles.css          Comparison-page styles
  v2/                 Research Desk shell and styles
  v3/                 Intelligence Terminal shell, styles and overview
  shared/app.js       Shared screens and controls
  shared/snapshot.json Sanitized, archived research data
  scripts/            Public-data preparation and boundary test
```

Both interfaces support search, watchlists, screeners, sorting, pagination, news, themes, analyst and committee research, penny research, score breakdowns, historical price views, journal and evidence. Design III changes the composition as well as the palette. It also restores an expandable universe map and adds chart price scales with per-point date/price titles.

## Data and public-preview boundaries

The shared archive was generated on 15 September 2026; main equity prices are dated 7 September and the penny screen has its own date. This is deliberately a frozen comparison dataset, not a second live trading system. The no-new-trigger brief is specific to that archive. Scores are heuristics, not calibrated success probabilities.

Personal holdings, notes from the real position file, personal capital and position sizing are not copied into the public preview. Portfolio shows the omission clearly; paper aggregates are labeled simulation. The original local `ui_v2/original.html` and unsanitized snapshot are **not** included in this folder. The watchlist stays in the viewer's browser, shared between these two designs.

Google Fonts is optional; system fallbacks are defined. No JavaScript frameworks, external scripts, package installation, API keys or build server are required.

## Run locally

From the repository root:

```sh
python -m http.server 8767 --bind 127.0.0.1
```

Open `http://127.0.0.1:8767/ui-designs/`. Opening HTML files directly will not load the JSON snapshot.

To explicitly prepare a new archive from a local exported dashboard JSON object:

```sh
python ui-designs/scripts/prepare_snapshot.py SOURCE_JSON ui-designs/shared/snapshot.json
python -m unittest discover -s ui-designs/scripts -p 'test_*.py'
```

Review the generated snapshot before publication. Never replace it with the full local dashboard or real holdings. A refresh also requires reviewing dated narrative and compatibility; the live pipeline does not overwrite this design archive.

## Publishing

The existing `.github/workflows/pages.yml` includes `ui-designs/**` in its push trigger and copies both versions into the Pages artifact. Subsequent daily and weekly deployments retain these routes. Publishing remains one serialized Pages workflow, so a second deployment does not replace the existing site with only the previews.

## Review notes

Desktop and phone layouts, navigation, stock dossiers, score blocks, chart periods, the universe map, public portfolio omission and shared controls were checked in a browser. JavaScript syntax and the public-data projection were checked separately. These are design previews, not complete production feature parity or an accessibility certification. Integration should retain the production trigger-priority ranking, advanced eligibility filters, operational controls, data freshness rules and complete paper ledger.
