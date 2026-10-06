# Hash Marks

College football sister site to [Down & Distance](https://areeslindley.github.io/down-and-distance/) and [The Breakdown](https://areeslindley.github.io/rugby-breakdown/). Same statistical standard; FBS schedules from [cfbfastR-data](https://github.com/sportsdataverse/cfbfastR-data) (College Football Data sourced), not nflverse.

This is a **separate sport**. It does not share Down & Distance's database, eval window, or ledger. C1–C3 are not ported. Player preds are not here.

The catalogue is up: Season, Fixtures, Teams, Structure, Years. Flask serves the full private history. The Pages snapshot publishes derived summaries and the current product window only — not a bulk CFBD mirror.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r config/requirements.txt
python -m scripts.ingest.schedules
python -m scripts.ingest.lines
python -m scripts.models.run_c0
```

## Catalogue

```bash
python -m pytest
python run.py
python -m scripts.site.export
```

- Flask app: `python run.py` (http://localhost:5000 or the next free port)
- GitHub Pages snapshot: `docs/` after `python -m scripts.site.export` — see [methodology/hosting.md](methodology/hosting.md)

## Ground rules

1. Investigate and report before building. Coverage is generated from the live sportsdataverse files.
2. FBS first. FCS / NCAA D-II / D-III stay out until they are pulled as their own leagues.
3. The close is the baseline, if the close exists. Always-home is not.
4. Do not import Down & Distance's `EVAL_SEASONS`, slot 4, or NFL era flags.
5. College discontinuities are labelled here: 2014 four-team playoff, 2020 pandemic, 2024 twelve-team CFP. Do not pool across them without a flag.
6. Do not publish a full historical `games.json`. Private SQLite holds the corpus; Pages gets derived views plus the live/holdout window.

## Data and hosting

Schedules and line odds are pulled from public [cfbfastR-data](https://github.com/sportsdataverse/cfbfastR-data) release files. Those files are CFBD-sourced. [CFBD terms](https://collegefootballdata.com/terms) allow a private cache and reasonable display as part of a product; they forbid publishing the API data as a standalone dataset or public database mirror.

`data/cache/` and `data/databases/` are gitignored. Attribution: Data provided by CollegeFootballData.com via sportsdataverse/cfbfastR-data.
