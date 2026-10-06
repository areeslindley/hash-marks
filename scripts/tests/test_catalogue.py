"""Catalogue helpers. No network, no NFL constants."""

from __future__ import annotations

import unittest

from scripts.ingest.parse import is_fbs, median
from scripts.ingest.lines import is_home_row
from scripts.models.constants import LIVE_SEASON, PAGES_GAME_SEASONS
from scripts.models.eras import era_label
from scripts.site.catalogue import annotate_all, pages_games, structure_index


def sample_games():
    return annotate_all(
        [
            {
                "game_id": "1",
                "season": 2025,
                "week": 1,
                "season_type": "regular",
                "gameday": "2025-08-30",
                "completed": 1,
                "home_id": "a",
                "home_team": "Alabama",
                "home_conference": "SEC",
                "home_division": "fbs",
                "home_points": 31,
                "away_id": "w",
                "away_team": "Western Kentucky",
                "away_conference": "CUSA",
                "away_division": "fbs",
                "away_points": 0,
                "spread_line": 31.0,
                "total_line": 60.0,
            },
            {
                "game_id": "2",
                "season": 2026,
                "week": 1,
                "season_type": "regular",
                "gameday": "2026-08-29",
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
            {
                "game_id": "3",
                "season": 2012,
                "week": 1,
                "season_type": "regular",
                "gameday": "2012-09-01",
                "completed": 1,
                "home_id": "a",
                "home_team": "Alabama",
                "home_conference": "SEC",
                "home_division": "fbs",
                "home_points": 41,
                "away_id": "m",
                "away_team": "Michigan",
                "away_conference": "Big Ten",
                "away_division": "fbs",
                "away_points": 14,
            },
        ]
    )


class ParseTests(unittest.TestCase):
    def test_fbs_gate(self):
        self.assertTrue(is_fbs("fbs"))
        self.assertFalse(is_fbs("fcs"))
        self.assertFalse(is_fbs("ii"))

    def test_median(self):
        self.assertEqual(median([3.0, 7.0, 1.0]), 3.0)

    def test_home_row_from_desc(self):
        desc = "Western Kentucky@Alabama"
        self.assertTrue(is_home_row("Alabama", desc))
        self.assertFalse(is_home_row("Western Kentucky", desc))
        self.assertTrue(is_home_row("UTH", "Texas Christian@Utah"))


class EraTests(unittest.TestCase):
    def test_college_eras_not_nfl(self):
        self.assertEqual(era_label(2013), "pre-playoff")
        self.assertEqual(era_label(2014), "2014-cfp4")
        self.assertEqual(era_label(2020), "2020-pandemic")
        self.assertEqual(era_label(2024), "2024-cfp12")
        self.assertEqual(era_label(2026), "2024-cfp12")


class CatalogueTests(unittest.TestCase):
    def test_pages_window_excludes_history(self):
        live = pages_games(sample_games())
        self.assertEqual({row["season"] for row in live}, set(PAGES_GAME_SEASONS))
        self.assertTrue(all(row["season"] != 2012 for row in live))

    def test_structure_is_conferences(self):
        tree = structure_index(sample_games(), 2025)
        names = [row["conference"] for row in tree["conferences"]]
        self.assertIn("SEC", names)
        self.assertNotIn("AFC", names)
        self.assertNotIn("NFC", names)

    def test_live_season_is_college_year(self):
        self.assertEqual(LIVE_SEASON, 2026)


if __name__ == "__main__":
    unittest.main()
