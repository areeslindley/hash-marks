"""Join a median close onto FBS games from cfbfastR-data line odds.

The gzip is a private cache. Only aggregated coverage is committed.
spread_line uses a home-relative convention: positive favours home
(home margin minus this number is the ATS residual). The vendor posts
a Vegas home line (negative if favoured); we store both.
"""

from __future__ import annotations

import csv
import gzip
import sqlite3
import sys
from collections import defaultdict

from scripts.ingest.download import LINES_URL, fetch
from scripts.ingest.parse import as_float, as_str, median
from scripts.models.store import CACHE_DIR, DB_PATH, ensure_data_dirs, write_report

LINES_PATH = CACHE_DIR / "betting" / "cfb_line_odds.csv.gz"


def download_lines(*, force: bool = False):
    ensure_data_dirs()
    print(f"lines -> {LINES_PATH.name}")
    return fetch(LINES_URL, LINES_PATH, force=force)


def _side_score(code: str, name: str) -> int:
    code = (code or "").strip().lower()
    name = (name or "").strip().lower()
    if not code or not name:
        return 0
    if code == name:
        return 8
    if code in name or name in code:
        return 6
    words = [part for part in name.replace("(", " ").replace(")", " ").split() if part]
    initials = "".join(word[0] for word in words if word[0].isalpha())
    if code == initials or (len(initials) >= 2 and code.startswith(initials)):
        return 5
    if any(code[:3] == word[:3] for word in words if len(code) >= 3 and len(word) >= 3):
        return 3
    if len(code) >= 3 and len(name) >= 3 and code[0] == name[0] and code[1] in name:
        return 2
    return 0


def parse_sides(game_desc: str | None) -> tuple[str, str]:
    text = game_desc or ""
    if "@" not in text:
        return "", ""
    away, home = text.split("@", 1)
    return away.strip(), home.strip()


def is_home_row(abbr: str, game_desc: str | None) -> bool | None:
    away, home = parse_sides(game_desc)
    if not home:
        return None
    home_score = _side_score(abbr, home)
    away_score = _side_score(abbr, away)
    if home_score == 0 and away_score == 0:
        return None
    if home_score == away_score:
        return None
    return home_score > away_score


def reduce_lines(path=LINES_PATH) -> dict[str, dict]:
    """One close per game_id from the long book/market file."""
    home_spreads: dict[str, list[float]] = defaultdict(list)
    home_opens: dict[str, list[float]] = defaultdict(list)
    totals: dict[str, list[float]] = defaultdict(list)
    total_opens: dict[str, list[float]] = defaultdict(list)
    home_ml: dict[str, list[float]] = defaultdict(list)
    away_ml: dict[str, list[float]] = defaultdict(list)

    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            game_id = as_str(raw.get("game_id"))
            if not game_id:
                continue
            market = (as_str(raw.get("market_type")) or "").lower()
            abbr = as_str(raw.get("abbr")) or ""
            desc = as_str(raw.get("game_desc"))
            line = as_float(raw.get("lines"))
            opening = as_float(raw.get("opening_lines"))
            odds = as_float(raw.get("odds"))
            home_row = is_home_row(abbr, desc)

            if market == "spread" and line is not None and home_row is True:
                home_spreads[game_id].append(line)
                if opening is not None:
                    home_opens[game_id].append(opening)
            elif market == "total" and line is not None:
                totals[game_id].append(line)
                if opening is not None:
                    total_opens[game_id].append(opening)
            elif market == "money_line" and odds is not None:
                if home_row is True:
                    home_ml[game_id].append(odds)
                elif home_row is False:
                    away_ml[game_id].append(odds)

    out = {}
    game_ids = set(home_spreads) | set(totals) | set(home_ml)
    for game_id in game_ids:
        vegas_home = median(home_spreads.get(game_id, []))
        spread_line = None if vegas_home is None else -vegas_home
        out[game_id] = {
            "home_spread": vegas_home,
            "spread_line": spread_line,
            "spread_open": None
            if not home_opens.get(game_id)
            else -median(home_opens[game_id]),
            "total_line": median(totals.get(game_id, [])),
            "total_open": median(total_opens.get(game_id, [])),
            "home_moneyline": median(home_ml.get(game_id, [])),
            "away_moneyline": median(away_ml.get(game_id, [])),
            "n_spread_books": len(home_spreads.get(game_id, [])),
            "n_total_books": len(totals.get(game_id, [])),
        }
    return out


def apply_lines(conn: sqlite3.Connection, closes: dict[str, dict]) -> int:
    updated = 0
    for game_id, close in closes.items():
        cur = conn.execute(
            """
            UPDATE games SET
              spread_line = ?, total_line = ?,
              home_moneyline = ?, away_moneyline = ?,
              spread_open = ?, total_open = ?,
              n_spread_books = ?, n_total_books = ?
            WHERE game_id = ?
            """,
            (
                close["spread_line"],
                close["total_line"],
                close["home_moneyline"],
                close["away_moneyline"],
                close["spread_open"],
                close["total_open"],
                close["n_spread_books"],
                close["n_total_books"],
                game_id,
            ),
        )
        updated += cur.rowcount
    conn.commit()
    return updated


def line_coverage(conn: sqlite3.Connection) -> dict:
    rows = list(
        conn.execute(
            """
            SELECT season,
                   COUNT(*) AS n,
                   SUM(completed) AS finished,
                   SUM(CASE WHEN spread_line IS NOT NULL THEN 1 ELSE 0 END) AS n_spread,
                   SUM(CASE WHEN total_line IS NOT NULL THEN 1 ELSE 0 END) AS n_total,
                   SUM(CASE WHEN home_moneyline IS NOT NULL THEN 1 ELSE 0 END) AS n_ml,
                   SUM(CASE WHEN completed = 1 AND spread_line IS NOT NULL THEN 1 ELSE 0 END) AS finished_spread
            FROM games
            GROUP BY season
            ORDER BY season
            """
        )
    )
    by_season = []
    for season, n, finished, n_spread, n_total, n_ml, finished_spread in rows:
        by_season.append(
            {
                "season": season,
                "n": n,
                "finished": finished,
                "n_spread": n_spread,
                "n_total": n_total,
                "n_moneyline": n_ml,
                "finished_spread": finished_spread,
                "spread_rate": None if not n else round(n_spread / n, 4),
                "total_rate": None if not n else round(n_total / n, 4),
            }
        )
    n, n_spread, n_total = conn.execute(
        """
        SELECT COUNT(*),
               SUM(CASE WHEN spread_line IS NOT NULL THEN 1 ELSE 0 END),
               SUM(CASE WHEN total_line IS NOT NULL THEN 1 ELSE 0 END)
        FROM games
        """
    ).fetchone()
    return {
        "n_games": n,
        "n_spread": n_spread,
        "n_total": n_total,
        "spread_rate": None if not n else round(n_spread / n, 4),
        "total_rate": None if not n else round(n_total / n, 4),
        "by_season": by_season,
        "close_convention": (
            "spread_line is home-relative and positive when the home side "
            "is favoured (negate of the posted Vegas home line)."
        ),
    }


def run(*, force: bool = False) -> dict:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"{DB_PATH} missing. Run scripts.ingest.schedules first.")
    download_lines(force=force)
    print("reducing line odds (long file)...")
    closes = reduce_lines()
    print(f"  {len(closes)} games with at least one market")
    conn = sqlite3.connect(str(DB_PATH))
    try:
        updated = apply_lines(conn, closes)
        report = line_coverage(conn)
    finally:
        conn.close()
    report["n_reduced"] = len(closes)
    report["n_updated"] = updated
    write_report("line_coverage.json", report)
    print(f"updated {updated} games with a close")
    return report


def main() -> int:
    force = "--force" in sys.argv
    run(force=force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
