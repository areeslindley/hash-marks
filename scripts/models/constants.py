"""College-only harness constants. Do not import from down-and-distance."""

from __future__ import annotations

# sportsdataverse schedule files start here.
CATALOGUE_FROM = 2001

# Line-odds file begins in 2006. C0 probe uses this, not an NFL window.
LINE_ERA_FROM = 2006

# Published product window.
HOLDOUT_SEASON = 2025
LIVE_SEASON = 2026

# Pages may show this inclusive window as reasonable display. Everything
# earlier stays in private SQLite.
PAGES_GAME_SEASONS = (HOLDOUT_SEASON, LIVE_SEASON)

# College discontinuities. Do not pool across these without a flag.
PLAYOFF_4_FROM = 2014
PANDEMIC_SEASON = 2020
PLAYOFF_12_FROM = 2024
