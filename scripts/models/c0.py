"""C0 probe: the posted close as a scoreline, not a registered walk.

This is not Down & Distance slot 0 imported. No alpha is spent. The
report exists so we know whether a close-wins thesis is even possible
on FBS before a Predictions page is built.
"""

from __future__ import annotations

from scripts.ingest.parse import is_fbs
from scripts.ingest.schedules import load_games
from scripts.models.constants import LINE_ERA_FROM
from scripts.models.store import write_report


def probe_rows(games: list[dict] | None = None) -> list[dict]:
    rows = []
    for game in games or load_games():
        if int(game.get("season") or 0) < LINE_ERA_FROM:
            continue
        if not game.get("completed"):
            continue
        if not (is_fbs(game.get("home_division")) and is_fbs(game.get("away_division"))):
            continue
        if game.get("home_points") is None or game.get("away_points") is None:
            continue
        spread = game.get("spread_line")
        if spread is None:
            continue
        margin = float(game["home_points"]) - float(game["away_points"])
        residual = margin - float(spread)
        rows.append(
            {
                "game_id": game["game_id"],
                "season": int(game["season"]),
                "margin": margin,
                "spread_line": float(spread),
                "residual": residual,
                "home_cover": residual > 0,
                "push": residual == 0,
                "total": float(game["home_points"]) + float(game["away_points"]),
                "total_line": game.get("total_line"),
            }
        )
    return rows


def summarize(rows: list[dict]) -> dict:
    decided = [row for row in rows if not row["push"]]
    by_season: dict[int, list[dict]] = {}
    for row in rows:
        by_season.setdefault(row["season"], []).append(row)
    seasons = []
    for season in sorted(by_season):
        chunk = by_season[season]
        decided_s = [row for row in chunk if not row["push"]]
        seasons.append(
            {
                "season": season,
                "n": len(chunk),
                "n_decided": len(decided_s),
                "home_cover_rate": None
                if not decided_s
                else round(sum(row["home_cover"] for row in decided_s) / len(decided_s), 4),
                "mae": None
                if not chunk
                else round(sum(abs(row["residual"]) for row in chunk) / len(chunk), 3),
            }
        )
    totals = [row for row in rows if row.get("total_line") is not None]
    over = [
        row
        for row in totals
        if row["total"] != row["total_line"]
    ]
    return {
        "kind": "c0_probe",
        "registered": False,
        "note": (
            "Median book close on both-FBS finished games from LINE_ERA_FROM. "
            "Not a walk-forward, not a ledger slot, not imported from the NFL site."
        ),
        "n": len(rows),
        "n_decided": len(decided),
        "home_cover_rate": None
        if not decided
        else round(sum(row["home_cover"] for row in decided) / len(decided), 4),
        "mae": None
        if not rows
        else round(sum(abs(row["residual"]) for row in rows) / len(rows), 3),
        "over_rate": None
        if not over
        else round(sum(1 for row in over if row["total"] > row["total_line"]) / len(over), 4),
        "n_totals": len(over),
        "by_season": seasons,
    }


def run() -> dict:
    payload = summarize(probe_rows())
    write_report("c0_probe.json", payload)
    return payload


def main() -> int:
    payload = run()
    print(
        f"C0 probe n={payload['n']} home ATS={payload['home_cover_rate']} "
        f"MAE={payload['mae']} (not registered)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
