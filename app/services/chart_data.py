from __future__ import annotations

import json
from pathlib import Path


class ChartDataError(ValueError):
    pass


def load_charts(path: Path) -> dict[tuple[str, str], dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ChartDataError("chart data must be a JSON array")
    result = {}
    for row in raw:
        if not isinstance(row, dict) or not all(k in row for k in ("id", "song", "difficulty", "constant")):
            raise ChartDataError("each chart needs id, song, difficulty and constant")
        if row["difficulty"] not in {"EZ", "HD", "IN", "AT", "SP"}:
            raise ChartDataError(f"invalid difficulty: {row['difficulty']}")
        constant = float(row["constant"])
        if not 0 <= constant <= 20:
            raise ChartDataError(f"invalid constant: {constant}")
        result[(str(row["id"]), row["difficulty"])] = {**row, "constant": constant}
    return result
