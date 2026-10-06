"""Load FBS schedules from cfbfastR-data and write a coverage report.

Full vendor CSVs stay in data/cache (gitignored). The SQLite file is private.
Coverage JSON is derived and may be committed.
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

from scripts.ingest.download import SCHEDULE_URL, fetch
from scripts.ingest.parse import as_bool, as_float, as_int, as_str, is_fbs
from scripts.models.constants import CATALOGUE_FROM, HOLDOUT_SEASON, LIVE_SEASON
from scripts.models.eras import era_flags, era_label
from scripts.models.store import CACHE_DIR, DB_PATH, REPORTS_DIR, ensure_data_dirs, write_report

SEASONS = tuple(range(CATALOGUE_FROM, LIVE_SEASON + 1))

CREATE_GAMES = """
CREATE TABLE IF NOT EXISTS games (
    game_id TEXT PRIMARY KEY,
    season INTEGER,
    week INTEGER,
    season_type TEXT,
    start_date TEXT,
    gameday TEXT,
    completed INTEGER,
    neutral_site INTEGER,
    conference_game INTEGER,
    venue TEXT,
    home_id TEXT,
    home_team TEXT,
    home_conference TEXT,
    home_division TEXT,
    home_points INTEGER,
    away_id TEXT,
    away_team TEXT,
    away_conference TEXT,
    away_division TEXT,
    away_points INTEGER,
    notes TEXT,
    spread_line REAL,
    total_line REAL,
    home_moneyline REAL,
    away_moneyline REAL,
    spread_open REAL,
    total_open REAL,
    n_spread_books INTEGER,
    n_total_books INTEGER
)
"""


def schedule_path(season: int) -> "Path":
    from pathlib import Path

    return CACHE_DIR / "schedules" / f"cfb_schedules_{season}.csv"


def download_schedules(*, force: bool = False) -> list:
    ensure_data_dirs()
    paths = []
    for season in SEASONS:
        dest = schedule_path(season)
        print(f"schedule {season} -> {dest.name}")
        paths.append(fetch(SCHEDULE_URL.format(season=season), dest, force=force))
    return paths


def gameday_of(start_date: str | None) -> str | None:
    if not start_date:
        return None
    text = start_date.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return start_date[:10] if len(start_date) >= 10 else start_date
    return parsed.date().isoformat()


def parse_schedule_row(raw: dict) -> dict | None:
    home_div = as_str(raw.get("home_division"))
    away_div = as_str(raw.get("away_division"))
    if not (is_fbs(home_div) or is_fbs(away_div)):
        return None
    start = as_str(raw.get("start_date"))
    home_points = as_int(raw.get("home_points"))
    away_points = as_int(raw.get("away_points"))
    completed = as_bool(raw.get("completed"))
    if completed is None:
        completed = home_points is not None and away_points is not None
    return {
        "game_id": as_str(raw.get("game_id")),
        "season": as_int(raw.get("season")),
        "week": as_int(raw.get("week")),
        "season_type": (as_str(raw.get("season_type")) or "regular").lower(),
        "start_date": start,
        "gameday": gameday_of(start),
        "completed": 1 if completed else 0,
        "neutral_site": 1 if as_bool(raw.get("neutral_site")) else 0,
        "conference_game": 1 if as_bool(raw.get("conference_game")) else 0,
        "venue": as_str(raw.get("venue")),
        "home_id": as_str(raw.get("home_id")),
        "home_team": as_str(raw.get("home_team")),
        "home_conference": as_str(raw.get("home_conference")),
        "home_division": (home_div or "").lower(),
        "home_points": home_points,
        "away_id": as_str(raw.get("away_id")),
        "away_team": as_str(raw.get("away_team")),
        "away_conference": as_str(raw.get("away_conference")),
        "away_division": (away_div or "").lower(),
        "away_points": away_points,
        "notes": as_str(raw.get("notes")),
    }


def load_season_csv(path) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row = parse_schedule_row(raw)
            if row and row["game_id"] and row["season"] is not None:
                rows.append(row)
    return rows


def ensure_games_table(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_GAMES)
    conn.commit()


def replace_games(conn: sqlite3.Connection, rows: list[dict]) -> None:
    conn.execute("DROP TABLE IF EXISTS games")
    ensure_games_table(conn)
    conn.executemany(
        """
        INSERT INTO games (
            game_id, season, week, season_type, start_date, gameday,
            completed, neutral_site, conference_game, venue,
            home_id, home_team, home_conference, home_division, home_points,
            away_id, away_team, away_conference, away_division, away_points,
            notes
        ) VALUES (
            :game_id, :season, :week, :season_type, :start_date, :gameday,
            :completed, :neutral_site, :conference_game, :venue,
            :home_id, :home_team, :home_conference, :home_division, :home_points,
            :away_id, :away_team, :away_conference, :away_division, :away_points,
            :notes
        )
        """,
        rows,
    )
    conn.commit()


def coverage_payload(rows: list[dict]) -> dict:
    by_season: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        by_season[int(row["season"])].append(row)
    season_rows = []
    for season in sorted(by_season):
        games = by_season[season]
        finished = [g for g in games if g["completed"]]
        fbs_teams = {
            (g["home_id"], g["home_team"])
            for g in games
            if is_fbs(g["home_division"])
        } | {
            (g["away_id"], g["away_team"])
            for g in games
            if is_fbs(g["away_division"])
        }
        conferences = {
            g["home_conference"]
            for g in games
            if is_fbs(g["home_division"]) and g["home_conference"]
        } | {
            g["away_conference"]
            for g in games
            if is_fbs(g["away_division"]) and g["away_conference"]
        }
        season_rows.append(
            {
                "season": season,
                "era": era_label(season),
                "flags": era_flags(season),
                "n": len(games),
                "finished": len(finished),
                "scheduled": len(games) - len(finished),
                "regular": sum(1 for g in games if g["season_type"] == "regular"),
                "postseason": sum(1 for g in games if g["season_type"] == "postseason"),
                "both_fbs": sum(
                    1
                    for g in games
                    if is_fbs(g["home_division"]) and is_fbs(g["away_division"])
                ),
                "vs_fcs_or_lower": sum(
                    1
                    for g in games
                    if is_fbs(g["home_division"]) != is_fbs(g["away_division"])
                ),
                "fbs_teams": len(fbs_teams),
                "conferences": sorted(conferences),
                "n_conferences": len(conferences),
                "weather_fields": 0,
            }
        )
    types = Counter(row["season_type"] for row in rows)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "sportsdataverse/cfbfastR-data schedules/csv (CFBD-sourced)",
        "classification": "fbs — keep a game if home or away division is fbs",
        "seasons": [row["season"] for row in season_rows],
        "n_games": len(rows),
        "n_finished": sum(1 for row in rows if row["completed"]),
        "season_types": dict(types),
        "fields_present": {
            "scores": True,
            "venue": True,
            "conference": True,
            "season_type": True,
            "spread_line": False,
            "total_line": False,
            "weather": False,
            "pbp": False,
        },
        "pbp_note": (
            "cfbfastR EPA/WPA play-by-play exists as sportsdataverse-data "
            "release cfbfastR_cfb_pbp from 2014. Not ingested."
        ),
        "weather_note": "Schedule files have venue, not temp/wind. Not ingested.",
        "hosting": {
            "private_sqlite": "data/databases/cfb.db",
            "pages_may_publish": [
                "coverage aggregates",
                "conference tree",
                "per-season counts",
                f"game rows for seasons {HOLDOUT_SEASON}–{LIVE_SEASON} only",
            ],
            "pages_must_not_publish": [
                "full historical games.json",
                "vendor CSV/gzip",
                "raw CFBD API payloads",
            ],
        },
        "by_season": season_rows,
    }


def load_games(conn: sqlite3.Connection | None = None) -> list[dict]:
    own = conn is None
    if own:
        if not DB_PATH.exists():
            raise FileNotFoundError(f"No schedule database at {DB_PATH}. Run: python -m scripts.ingest.schedules")
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute("SELECT * FROM games ORDER BY gameday, game_id")]
    finally:
        if own:
            conn.close()


def run(*, force: bool = False) -> dict:
    ensure_data_dirs()
    download_schedules(force=force)
    rows: list[dict] = []
    for season in SEASONS:
        path = schedule_path(season)
        if not path.exists():
            raise FileNotFoundError(path)
        season_rows = load_season_csv(path)
        print(f"  {season}: {len(season_rows)} FBS games")
        rows.extend(season_rows)
    seen: set[str] = set()
    unique = []
    for row in rows:
        if row["game_id"] in seen:
            continue
        seen.add(row["game_id"])
        unique.append(row)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        replace_games(conn, unique)
        n = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    finally:
        conn.close()
    report = coverage_payload(unique)
    report["n_stored"] = n
    write_report("schedule_coverage.json", report)
    print(f"stored {n} FBS games -> {DB_PATH}")
    print(f"coverage -> {REPORTS_DIR / 'schedule_coverage.json'}")
    return report


def main() -> int:
    force = "--force" in sys.argv
    run(force=force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
