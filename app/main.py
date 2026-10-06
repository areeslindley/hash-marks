"""Flask app for the Hash Marks FBS catalogue."""

from __future__ import annotations

import socket
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from scripts.ingest.schedules import load_games
from scripts.models.constants import LIVE_SEASON
from scripts.models.store import DB_PATH, REPO_ROOT, load_report
from scripts.site.catalogue import (
    annotate_all,
    filter_games,
    paginate,
    season_summary,
    site_meta,
    structure_index,
    team_season,
    teams_index,
    years_index,
)

_GAMES: list[dict] | None = None
_GAMES_MTIME: float | None = None


def get_games() -> list[dict]:
    global _GAMES, _GAMES_MTIME
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"No schedule database at {DB_PATH}. Run: python -m scripts.ingest.schedules"
        )
    mtime = DB_PATH.stat().st_mtime
    if _GAMES is None or _GAMES_MTIME != mtime:
        _GAMES = annotate_all(load_games())
        _GAMES_MTIME = mtime
    return _GAMES


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(REPO_ROOT / "templates"),
        static_folder=str(REPO_ROOT / "static"),
    )
    app.config["SECRET_KEY"] = "hash-marks"

    @app.route("/")
    def index():
        return render_template("index.html", static_site=False)

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            Path(app.static_folder) / "img",
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )

    @app.route("/api/meta")
    def api_meta():
        return jsonify(
            site_meta(
                get_games(),
                load_report("schedule_coverage.json"),
                load_report("line_coverage.json"),
                load_report("c0_probe.json"),
            )
        )

    @app.route("/api/games")
    def api_games():
        rows = filter_games(
            get_games(),
            season=request.args.get("season", type=int),
            week=request.args.get("week", type=int),
            status=request.args.get("status") or None,
            team=request.args.get("team") or None,
            conference=request.args.get("conference") or None,
            game_type=request.args.get("game_type") or None,
            query=request.args.get("q") or None,
        )
        rows = list(reversed(rows))
        return jsonify(
            paginate(
                rows,
                page=request.args.get("page", 1, type=int) or 1,
                per_page=request.args.get("per_page", 25, type=int) or 25,
            )
        )

    @app.route("/api/games/<game_id>")
    def api_game(game_id: str):
        for row in get_games():
            if row["game_id"] == game_id:
                return jsonify(row)
        return jsonify({"error": "not found"}), 404

    @app.route("/api/season/<int:season>")
    def api_season(season: int):
        return jsonify(season_summary(get_games(), season))

    @app.route("/api/teams")
    def api_teams():
        season = request.args.get("season", LIVE_SEASON, type=int) or LIVE_SEASON
        return jsonify({"season": season, "teams": teams_index(get_games(), season)})

    @app.route("/api/teams/<team>")
    def api_team(team: str):
        season = request.args.get("season", LIVE_SEASON, type=int) or LIVE_SEASON
        payload = team_season(get_games(), team, season)
        if payload is None:
            return jsonify({"error": "unknown team"}), 404
        return jsonify(payload)

    @app.route("/api/structure")
    def api_structure():
        season = request.args.get("season", LIVE_SEASON, type=int) or LIVE_SEASON
        return jsonify(structure_index(get_games(), season))

    @app.route("/api/years")
    def api_years():
        return jsonify(years_index(get_games()))

    @app.route("/api/coverage")
    def api_coverage():
        return jsonify(load_report("schedule_coverage.json") or {})

    return app


def find_available_port(start_port: int = 5000, max_attempts: int = 20) -> int | None:
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("localhost", port))
                return port
            except OSError:
                continue
    return None
