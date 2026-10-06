"""Pages export must not become a CFBD mirror."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.site.catalogue import annotate_all, pages_games
from scripts.site import export as export_mod


class HostingTests(unittest.TestCase):
    def test_export_writes_live_window_only(self):
        games = annotate_all(
            [
                {
                    "game_id": "old",
                    "season": 2010,
                    "week": 1,
                    "season_type": "regular",
                    "gameday": "2010-09-04",
                    "completed": 1,
                    "home_id": "a",
                    "home_team": "Alabama",
                    "home_conference": "SEC",
                    "home_division": "fbs",
                    "home_points": 24,
                    "away_id": "p",
                    "away_team": "Penn State",
                    "away_conference": "Big Ten",
                    "away_division": "fbs",
                    "away_points": 3,
                },
                {
                    "game_id": "new",
                    "season": 2026,
                    "week": 1,
                    "season_type": "regular",
                    "gameday": "2026-09-05",
                    "completed": 0,
                    "home_id": "a",
                    "home_team": "Alabama",
                    "home_conference": "SEC",
                    "home_division": "fbs",
                    "home_points": None,
                    "away_id": "g",
                    "away_team": "Georgia",
                    "away_conference": "SEC",
                    "away_division": "fbs",
                    "away_points": None,
                },
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir()
            (docs / "data").mkdir()
            (docs / "data" / "games.json").write_text("[]\n", encoding="utf-8")
            with mock.patch.object(export_mod, "DOCS", docs), mock.patch.object(
                export_mod, "load_report", return_value={}
            ):
                export_mod.export_json(games)
            self.assertFalse((docs / "data" / "games.json").exists())
            live = json.loads((docs / "data" / "live_games.json").read_text())
            self.assertEqual([row["game_id"] for row in live], ["new"])
            self.assertEqual(pages_games(games)[0]["game_id"], "new")


if __name__ == "__main__":
    unittest.main()
