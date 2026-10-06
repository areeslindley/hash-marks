# Hosting audit — what Pages may show

Stamped 2026-09-27, before the catalogue was exported.

## Sources

| File | Host | Origin |
|---|---|---|
| `schedules/csv/cfb_schedules_{season}.csv` | [cfbfastR-data](https://github.com/sportsdataverse/cfbfastR-data) | CFBD `game_info` |
| `betting/csv/cfb_line_odds.csv.gz` | same repo | CFBD line odds |

[CollegeFootballData.com terms](https://collegefootballdata.com/terms) (effective 2026-08-12):

- Allowed: private cache; historical analysis; display of reasonable portions of factual rows as part of a larger product; derived outputs (summaries, models, coverage reports).
- Forbidden: publishing API data as a standalone dataset, bulk download, public database mirror, or substitute API.

nflverse is CC-BY 4.0, which is why Down & Distance can publish a full `docs/data/games.json`. This site cannot copy that pattern for the CFBD-sourced corpus.

## What is stored where

| Surface | Contents |
|---|---|
| `data/cache/` (gitignored) | Vendor CSVs and the line-odds gzip |
| `data/databases/cfb.db` (gitignored) | Full FBS history, 2001–live |
| `data/reports/*.json` (committed) | Aggregated coverage and the C0 probe |
| `docs/data/meta.json` | Site name, seasons, conference list, coverage headline |
| `docs/data/coverage.json` | Same as the coverage report |
| `docs/data/structure.json` | Conference tree for the live season |
| `docs/data/seasons.json` | Per-season counts, not game rows |
| `docs/data/live_games.json` | Holdout + live seasons only (reasonable display) |

There is no `docs/data/games.json`. Flask `/api/games` reads SQLite and can page the full private history.

## Direct CFBD API

A `CFBD_API_KEY` is not required for this ingest. If one is added later, keep it server-side; do not embed it in `docs/`.
