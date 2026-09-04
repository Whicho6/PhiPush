import math

from app.models.schemas import Record
from app.services.rks import accuracy_for_rks, build_best, chart_rks, projected_gain


def rec(rks, ap=False):
    return Record("x", "x", "IN", 16, 990000, 99, ap=ap, chart_rks=rks)


def test_chart_formula_and_boundaries():
    assert chart_rks(15, 69.999) == 0
    assert math.isclose(chart_rks(15, 70), 15 / 9)
    assert chart_rks(15, 100) == 15
    assert chart_rks(15, 101) == 15
    assert chart_rks(None, 100) == 0


def test_b30_sort_cutoff_and_phi():
    rows = [rec(float(i), ap=i in (28, 29, 30, 31)) for i in range(1, 32)]
    result = build_best(rows)
    assert [x.chart_rks for x in result.phi] == [31, 30, 29]
    assert len(result.best) == 27
    assert result.cutoff == 5
    assert result.total == (31 + 30 + 29 + sum(range(5, 32))) / 30


def test_inverse_formula():
    assert math.isclose(accuracy_for_rks(15, chart_rks(15, 98.4)), 98.4)
    assert accuracy_for_rks(15, 0.01) == 70.0
    assert accuracy_for_rks(15, 16) is None


def test_replacement_projection():
    rows = [rec(float(i)) for i in range(1, 32)]
    low = rows[0]
    gain, replaced, entered = projected_gain(rows, low, 32)
    assert entered and replaced is rows[4]
    assert math.isclose(gain, 27 / 30)


def test_phi_is_also_allowed_in_best_and_empty_phi_slots_are_not_backfilled():
    rows = [rec(float(i), ap=i >= 28) for i in range(1, 31)]
    result = build_best(rows)
    assert [x.chart_rks for x in result.phi] == [30, 29, 28]
    assert [x.chart_rks for x in result.best[:3]] == [30, 29, 28]
    no_phi = build_best([rec(1.0) for _ in range(27)])
    assert math.isclose(no_phi.total, 27 / 30)


def test_empty_records():
    result = build_best([])
    assert result.total == result.cutoff == 0
