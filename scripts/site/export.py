"""Export derived catalogue views to docs/. Never write a full games.json."""

from __future__ import annotations

import json
import shutil
import sys

from scripts.ingest.schedules import load_games
from scripts.models.constants import LIVE_SEASON
from scripts.models.store import REPO_ROOT, load_report
from scripts.site.catalogue import (
    annotate_all,
    pages_games,
    season_summary,
    site_meta,
    structure_index,
    years_index,
)

DOCS = REPO_ROOT / "docs"


def write_json(path, payload, *, indent: int | None = None) -> None:
    text = json.dumps(payload, indent=indent, separators=None if indent else (",", ":"))
    path.write_text(text + "\n", encoding="utf-8")


def export_json(games: list[dict]) -> dict:
    data_dir = DOCS / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    # Hard rule: do not emit a historical games.json.
    if (data_dir / "games.json").exists():
        (data_dir / "games.json").unlink()
    coverage = load_report("schedule_coverage.json")
    lines = load_report("line_coverage.json")
    c0 = load_report("c0_probe.json")
    live = pages_games(games)
    write_json(
        data_dir / "meta.json",
        site_meta(games, coverage, lines, c0),
        indent=2,
    )
    write_json(data_dir / "coverage.json", coverage or {}, indent=2)
    write_json(data_dir / "structure.json", structure_index(games, LIVE_SEASON), indent=2)
    write_json(data_dir / "seasons.json", years_index(games), indent=2)
    write_json(
        data_dir / "season_live.json",
        season_summary(games, LIVE_SEASON),
        indent=2,
    )
    write_json(data_dir / "live_games.json", live)
    return {"n_games": len(games), "n_live": len(live)}


def export_static() -> None:
    static_src = REPO_ROOT / "static"
    for folder in ("css", "js", "img"):
        dest = DOCS / folder
        dest.mkdir(parents=True, exist_ok=True)
        src = static_src / folder
        if not src.exists():
            continue
        for path in src.glob("*"):
            shutil.copy2(path, dest / path.name)
    for name in ("favicon.svg", "favicon.ico", "favicon.png"):
        src = static_src / "img" / name
        if src.exists():
            shutil.copy2(src, DOCS / name)


def export_html() -> None:
    from app.main import create_app

    app = create_app()
    with app.app_context():
        html = app.jinja_env.get_template("index.html").render(static_site=True)
    (DOCS / "index.html").write_text(html, encoding="utf-8")


def run() -> dict:
    games = annotate_all(load_games())
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    counts = export_json(games)
    export_static()
    export_html()
    return {"docs": str(DOCS), **counts}


def main() -> int:
    payload = run()
    print(
        f"exported {payload['n_games']} private games, "
        f"{payload['n_live']} holdout+live rows to {payload['docs']} "
        "(no games.json)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
