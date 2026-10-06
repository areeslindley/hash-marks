"""College football discontinuities. Not the NFL 2020 / 17-game / kickoff flags."""

from __future__ import annotations

from scripts.models.constants import PANDEMIC_SEASON, PLAYOFF_12_FROM, PLAYOFF_4_FROM


def era_flags(season: int) -> dict[str, bool]:
    year = int(season)
    return {
        "playoff_4": PLAYOFF_4_FROM <= year < PLAYOFF_12_FROM,
        "playoff_12": year >= PLAYOFF_12_FROM,
        "pandemic_2020": year == PANDEMIC_SEASON,
        "pre_playoff": year < PLAYOFF_4_FROM,
    }


def era_label(season: int) -> str:
    flags = era_flags(season)
    if flags["pandemic_2020"]:
        return "2020-pandemic"
    if flags["playoff_12"]:
        return "2024-cfp12"
    if flags["playoff_4"]:
        return "2014-cfp4"
    return "pre-playoff"
