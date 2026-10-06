"""Fetch public sportsdataverse files into the private cache."""

from __future__ import annotations

import urllib.request
from pathlib import Path

USER_AGENT = "hash-marks-ingest/0.1 (college football sister site; private cache)"

SCHEDULE_URL = (
    "https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/"
    "main/schedules/csv/cfb_schedules_{season}.csv"
)
LINES_URL = (
    "https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/"
    "main/betting/csv/cfb_line_odds.csv.gz"
)


def fetch(url: str, dest: Path, *, force: bool = False) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        tmp.write_bytes(response.read())
    tmp.replace(dest)
    return dest
