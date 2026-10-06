"""Shape FBS rows for the catalogue. No NFL team map, no ledger."""

from __future__ import annotations

from scripts.ingest.parse import is_fbs
from scripts.models.constants import HOLDOUT_SEASON, LIVE_SEASON, PAGES_GAME_SEASONS
from scripts.models.eras import era_flags, era_label

PUBLIC_FIELDS = (
    "game_id",
    "season",
    "week",
    "season_type",
    "gameday",
    "venue",
    "neutral_site",
    "conference_game",
    "home_id",
    "home_team",
    "home_conference",
    "home_division",
    "home_points",
    "away_id",
    "away_team",
    "away_conference",
    "away_division",
    "away_points",
    "spread_line",
    "total_line",
    "notes",
)


def status_of(row: dict) -> str:
    if row.get("completed") and row.get("home_points") is not None and row.get("away_points") is not None:
        return "Finished"
    return "Scheduled"


def public_game(row: dict) -> dict:
    out = {key: row.get(key) for key in PUBLIC_FIELDS}
    out["status"] = status_of(row)
    out["game_type"] = "POST" if (row.get("season_type") or "") == "postseason" else "REG"
    out["game_type_label"] = "Postseason" if out["game_type"] == "POST" else "Regular"
    out["result"] = None
    if row.get("home_points") is not None and row.get("away_points") is not None:
        out["result"] = float(row["home_points"]) - float(row["away_points"])
        out["total"] = float(row["home_points"]) + float(row["away_points"])
    else:
        out["total"] = None
    season = row.get("season")
    out["era"] = era_label(int(season)) if season is not None else ""
    out["both_fbs"] = is_fbs(row.get("home_division")) and is_fbs(row.get("away_division"))
    return out


def annotate_all(rows: list[dict]) -> list[dict]:
    games = [public_game(row) for row in rows]
    games.sort(key=lambda item: (item.get("gameday") or "", item.get("game_id") or ""))
    return games


def filter_games(
    games: list[dict],
    *,
    season: int | None = None,
    week: int | None = None,
    status: str | None = None,
    team: str | None = None,
    conference: str | None = None,
    game_type: str | None = None,
    query: str | None = None,
) -> list[dict]:
    team_key = (team or "").strip().lower()
    conf_key = (conference or "").strip().lower()
    needle = (query or "").strip().lower()
    status_key = (status or "").strip()
    out = []
    for row in games:
        if season is not None and int(row["season"]) != int(season):
            continue
        if week is not None and int(row["week"]) != int(week):
            continue
        if status_key and row["status"] != status_key:
            continue
        if game_type and row.get("game_type") != game_type:
            continue
        if team_key:
            names = {(row.get("home_team") or "").lower(), (row.get("away_team") or "").lower()}
            ids = {str(row.get("home_id") or ""), str(row.get("away_id") or "")}
            if team_key not in names and team not in ids:
                continue
        if conf_key:
            conferences = {
                (row.get("home_conference") or "").lower(),
                (row.get("away_conference") or "").lower(),
            }
            if conf_key not in conferences:
                continue
        if needle:
            blob = " ".join(
                str(row.get(key) or "")
                for key in (
                    "away_team",
                    "home_team",
                    "venue",
                    "home_conference",
                    "away_conference",
                    "game_type_label",
                )
            ).lower()
            if needle not in blob:
                continue
        out.append(row)
    return out


def paginate(rows: list[dict], page: int = 1, per_page: int = 25) -> dict:
    total = len(rows)
    per_page = max(1, min(int(per_page), 100))
    pages = max(1, (total + per_page - 1) // per_page) if total else 1
    page = max(1, min(int(page), pages))
    start = (page - 1) * per_page
    return {
        "data": rows[start : start + per_page],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
        },
    }


def _cover_residual(row: dict, is_home: bool) -> float | None:
    spread = row.get("spread_line")
    margin = row.get("result")
    if spread is None or margin is None:
        return None
    market = float(margin) - float(spread)
    return market if is_home else -market


def season_summary(games: list[dict], season: int) -> dict:
    rows = filter_games(games, season=season)
    finished = [row for row in rows if row["status"] == "Finished"]
    scheduled = [row for row in rows if row["status"] == "Scheduled"]
    weeks: dict[int, dict] = {}
    for row in rows:
        week = int(row["week"] or 0)
        bucket = weeks.setdefault(week, {"week": week, "n": 0, "finished": 0, "points": 0.0})
        bucket["n"] += 1
        if row["status"] == "Finished":
            bucket["finished"] += 1
            bucket["points"] += float(row["total"] or 0)
    week_rows = []
    for week in sorted(weeks):
        bucket = weeks[week]
        n_fin = bucket["finished"]
        week_rows.append(
            {
                "week": week,
                "n": bucket["n"],
                "finished": n_fin,
                "points_per_game": round(bucket["points"] / n_fin, 2) if n_fin else None,
            }
        )
    dates = [row["gameday"] for row in rows if row.get("gameday")]
    fbs_names = {
        row["home_team"]
        for row in rows
        if is_fbs(row.get("home_division"))
    } | {
        row["away_team"]
        for row in rows
        if is_fbs(row.get("away_division"))
    }
    return {
        "season": int(season),
        "era": era_label(int(season)),
        "flags": era_flags(int(season)),
        "n": len(rows),
        "finished": len(finished),
        "scheduled": len(scheduled),
        "reg": sum(1 for row in rows if row.get("game_type") == "REG"),
        "post": sum(1 for row in rows if row.get("game_type") == "POST"),
        "min_date": min(dates) if dates else None,
        "max_date": max(dates) if dates else None,
        "teams": len(fbs_names),
        "mean_total": round(sum(float(row["total"]) for row in finished) / len(finished), 2)
        if finished
        else None,
        "weeks": week_rows,
        "latest": sorted(finished, key=lambda item: item["gameday"] or "", reverse=True)[:8],
        "upcoming": sorted(scheduled, key=lambda item: item["gameday"] or "")[:8],
        "holdout_season": HOLDOUT_SEASON,
        "live_season": LIVE_SEASON,
    }


def _team_game_view(row: dict, team: str) -> dict:
    is_home = (row.get("home_team") or "") == team or str(row.get("home_id") or "") == team
    scored = row["home_points"] if is_home else row["away_points"]
    allowed = row["away_points"] if is_home else row["home_points"]
    opponent = row["away_team"] if is_home else row["home_team"]
    result = None
    if scored is not None and allowed is not None:
        if scored > allowed:
            result = "W"
        elif scored < allowed:
            result = "L"
        else:
            result = "T"
    cover_residual = _cover_residual(row, is_home)
    cover = None
    if result is not None and cover_residual is not None:
        if cover_residual == 0:
            cover = "push"
        else:
            cover = "cover" if cover_residual > 0 else "loss"
    return {
        **row,
        "is_home": is_home,
        "scored": scored,
        "allowed": allowed,
        "opponent": opponent,
        "team_result": result,
        "cover": cover,
        "cover_residual": None if cover_residual is None else round(cover_residual, 2),
    }


def team_key(row: dict, home: bool) -> tuple[str, str, str, str]:
    if home:
        return (
            str(row.get("home_id") or row.get("home_team") or ""),
            row.get("home_team") or "",
            row.get("home_conference") or "Independent",
            (row.get("home_division") or "").lower(),
        )
    return (
        str(row.get("away_id") or row.get("away_team") or ""),
        row.get("away_team") or "",
        row.get("away_conference") or "Independent",
        (row.get("away_division") or "").lower(),
    )


def fbs_teams_in_season(games: list[dict], season: int) -> list[dict]:
    rows = filter_games(games, season=season)
    seen: dict[str, dict] = {}
    for row in rows:
        for home in (True, False):
            ident, name, conference, division = team_key(row, home)
            if not is_fbs(division) or not ident:
                continue
            seen[ident] = {
                "id": ident,
                "name": name,
                "conference": conference,
                "division": division,
            }
    return sorted(seen.values(), key=lambda item: (item["conference"], item["name"]))


def team_season(games: list[dict], team: str, season: int) -> dict | None:
    info = next((item for item in fbs_teams_in_season(games, season) if item["id"] == team or item["name"] == team), None)
    if info is None:
        return None
    name = info["name"]
    rows = [_team_game_view(row, name) for row in filter_games(games, season=season, team=name)]
    finished = [row for row in rows if row["team_result"]]
    wins = sum(1 for row in finished if row["team_result"] == "W")
    losses = sum(1 for row in finished if row["team_result"] == "L")
    ties = sum(1 for row in finished if row["team_result"] == "T")
    covers = [row for row in finished if row["cover"] in {"cover", "loss"}]
    return {
        "id": info["id"],
        "name": name,
        "conference": info["conference"],
        "season": int(season),
        "n": len(rows),
        "finished": len(finished),
        "record": f"{wins}-{losses}-{ties}",
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "points_for": round(sum(float(row["scored"]) for row in finished), 1) if finished else 0,
        "points_against": round(sum(float(row["allowed"]) for row in finished), 1) if finished else 0,
        "ats_hit": round(sum(1 for row in covers if row["cover"] == "cover") / len(covers), 3)
        if covers
        else None,
        "ats_n": len(covers),
        "games": rows,
    }


def teams_index(games: list[dict], season: int) -> list[dict]:
    out = []
    for info in fbs_teams_in_season(games, season):
        payload = team_season(games, info["name"], season)
        if payload is None:
            continue
        out.append(
            {
                "id": payload["id"],
                "name": payload["name"],
                "conference": payload["conference"],
                "record": payload["record"],
                "wins": payload["wins"],
                "losses": payload["losses"],
                "ties": payload["ties"],
                "n": payload["n"],
                "finished": payload["finished"],
                "points_for": payload["points_for"],
                "points_against": payload["points_against"],
                "ats_hit": payload["ats_hit"],
            }
        )
    return out


def structure_index(games: list[dict], season: int) -> dict:
    teams = teams_index(games, season)
    conferences: dict[str, list[dict]] = {}
    for team in teams:
        conferences.setdefault(team["conference"], []).append(team)
    tree = [
        {
            "conference": name,
            "n": len(members),
            "teams": members,
        }
        for name, members in sorted(conferences.items(), key=lambda item: (-len(item[1]), item[0]))
    ]
    return {"season": int(season), "n_conferences": len(tree), "n_teams": len(teams), "conferences": tree}


def years_index(games: list[dict]) -> list[dict]:
    by_season: dict[int, dict] = {}
    for row in games:
        season = int(row["season"])
        bucket = by_season.setdefault(
            season,
            {"season": season, "n": 0, "finished": 0, "scheduled": 0, "reg": 0, "post": 0},
        )
        bucket["n"] += 1
        if row["status"] == "Finished":
            bucket["finished"] += 1
        else:
            bucket["scheduled"] += 1
        if row.get("game_type") == "REG":
            bucket["reg"] += 1
        else:
            bucket["post"] += 1
    out = []
    for season in sorted(by_season, reverse=True):
        bucket = by_season[season]
        bucket["era"] = era_label(season)
        bucket["flags"] = era_flags(season)
        out.append(bucket)
    return out


def pages_games(games: list[dict]) -> list[dict]:
    allowed = set(PAGES_GAME_SEASONS)
    return [row for row in games if int(row["season"]) in allowed]


def site_meta(games: list[dict], coverage: dict | None = None, lines: dict | None = None, c0: dict | None = None) -> dict:
    seasons = sorted({int(row["season"]) for row in games})
    live_structure = structure_index(games, LIVE_SEASON)
    return {
        "name": "Hash Marks",
        "sport": "fbs",
        "live_season": LIVE_SEASON,
        "holdout_season": HOLDOUT_SEASON,
        "pages_game_seasons": list(PAGES_GAME_SEASONS),
        "seasons": seasons,
        "season_min": seasons[0] if seasons else None,
        "season_max": seasons[-1] if seasons else None,
        "n_games": len(games),
        "n_pages_games": len(pages_games(games)),
        "conferences": [row["conference"] for row in live_structure["conferences"]],
        "coverage": coverage,
        "lines": lines,
        "c0": c0,
        "hosting": (
            "Full history is private SQLite. Pages publishes derived "
            "summaries plus holdout and live game rows only."
        ),
    }
