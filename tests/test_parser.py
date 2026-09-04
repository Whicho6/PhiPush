import json
from pathlib import Path

from app.services.chart_data import ChartDataError, load_charts
from app.services.record_parser import normalize_player


ROOT = Path(__file__).parents[1]


def test_mock_parser_and_unknown():
    charts = load_charts(ROOT / "data/demo_charts.json")
    player = normalize_player(json.loads((ROOT / "data/mock_player.json").read_text(encoding="utf-8")), charts)
    assert 30 <= len(player.records) <= 50
    unknown = next(x for x in player.records if x.song_id.startswith("Unknown"))
    assert not unknown.known and unknown.chart_rks == 0


def test_chart_validation(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('[{"id":"x"}]', encoding="utf-8")
    try:
        load_charts(bad)
        assert False
    except ChartDataError:
        pass
