from app.models.schemas import Record
from app.services.push_planner import _effort, opportunities, target_route
from app.services.rks import chart_rks


def make(i, acc=98.0, constant=15.0):
    return Record(str(i), f"Song {i}", "IN", constant, 980000, acc, chart_rks=chart_rks(constant, acc))


def test_push_score_sorting_and_fields():
    rows = [make(i, 97 + i * .07, 14 + i * .08) for i in range(35)]
    found = opportunities(rows)
    assert found
    assert found == sorted(found, key=lambda x: (x.score, x.total_gain), reverse=True)
    assert all(x.total_gain > 0 and x.acc_gain > 0 and x.reason for x in found)


def test_target_route_moves_toward_goal():
    rows = [make(i, 97.5 + i * .04, 14.5 + i * .05) for i in range(40)]
    route = target_route(rows, 15.2)
    assert route["estimated_final_rks"] >= route["current_rks"]
    assert len(route["steps"]) <= 10
    assert "不保证" in route["disclaimer"]


def test_unknown_chart_is_skipped():
    unknown = Record("?", "Unknown", "AT", None, 990000, 99)
    assert opportunities([unknown]) == []


def test_ap_projection_counts_phi_and_best_separately():
    rows = [make(i, 99.9, 15.0 - i * .01) for i in range(30)]
    found = opportunities(rows, limit=30)
    ap = next(x for x in found if x.record is rows[0] and x.target_accuracy == 100.0)
    assert ap.route_type == "phi"
    assert ap.phi_gain > 0
    assert ap.best_gain > 0
    assert abs(ap.total_gain - ap.phi_gain - ap.best_gain) < 1e-9


def test_next_visible_rks_boundary_is_a_candidate():
    rows = [make(i, 98.2 + i * .02, 14.8 + i * .02) for i in range(35)]
    found = opportunities(rows, limit=35)
    assert any(x.crosses_display_boundary for x in found)


def test_near_ap_is_not_treated_as_an_ordinary_tenth():
    assert _effort(99.9, 100.0) > (100.0 - 99.9) * 5
