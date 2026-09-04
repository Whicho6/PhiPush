from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Protocol


class RksRecord(Protocol):
    chart_rks: float
    ap: bool


@dataclass(frozen=True, slots=True)
class BestSet:
    phi: tuple[RksRecord, ...]
    best: tuple[RksRecord, ...]
    total: float
    cutoff: float


@dataclass(frozen=True, slots=True)
class Projection:
    total_gain: float
    best_gain: float
    phi_gain: float
    replaced: RksRecord | None
    entered_best: bool


def chart_rks(constant: float | None, accuracy: float) -> float:
    """Current Phigros chart RKS: C*((ACC-55)/45)^2, zero below 70%."""
    if constant is None or constant < 0 or accuracy < 70:
        return 0.0
    acc = min(100.0, accuracy)
    return constant * ((acc - 55.0) / 45.0) ** 2


def accuracy_for_rks(constant: float, target_rks: float) -> float | None:
    if constant <= 0 or target_rks < 0 or target_rks > constant + 1e-12:
        return None
    if target_rks == 0:
        return 70.0
    # Positive chart RKS is discontinuous at 70%; values between 0 and the
    # 70%-RKS are unattainable, so 70% is the minimum useful answer.
    return min(100.0, max(70.0, 55.0 + 45.0 * math.sqrt(target_rks / constant)))


def build_best(records: Iterable[RksRecord], slots: int = 30, phi_slots: int = 3) -> BestSet:
    eligible = sorted((r for r in records if r.chart_rks > 0), key=lambda r: r.chart_rks, reverse=True)
    phi = tuple(sorted((r for r in eligible if r.ap), key=lambda r: r.chart_rks, reverse=True)[:phi_slots])
    # Current Phigros uses three bonus Phi slots plus B1-B27. A Phi chart may
    # therefore contribute twice: once in P1-P3 and again in B1-B27.
    best_count = max(0, slots - phi_slots)
    best = tuple(eligible[:best_count])
    total = (sum(r.chart_rks for r in phi) + sum(r.chart_rks for r in best)) / slots if slots else 0.0
    cutoff = best[-1].chart_rks if len(best) == best_count and best else 0.0
    return BestSet(phi=phi, best=best, total=total, cutoff=cutoff)


def project_change(records: list[RksRecord], record: RksRecord, new_rks: float,
                   new_ap: bool | None = None) -> Projection:
    """Simulate one score change and split its B27 and P1-P3 contributions."""
    before = build_best(records)
    old = record.chart_rks
    old_ap = record.ap
    record.chart_rks = new_rks
    if new_ap is not None:
        record.ap = new_ap
    try:
        after = build_best(records)
        after_best_sum = sum(r.chart_rks for r in after.best)
        after_phi_sum = sum(r.chart_rks for r in after.phi)
        after_ids = {id(r) for r in after.best}
    finally:
        record.chart_rks = old
        record.ap = old_ap
    before_ids = {id(r) for r in before.best}
    replaced = next((r for r in before.best if id(r) not in after_ids), None)
    entered = id(record) in after_ids and id(record) not in before_ids
    best_gain = (after_best_sum - sum(r.chart_rks for r in before.best)) / 30
    phi_gain = (after_phi_sum - sum(r.chart_rks for r in before.phi)) / 30
    return Projection(max(0.0, best_gain + phi_gain), max(0.0, best_gain),
                      max(0.0, phi_gain), replaced, entered)


def projected_gain(records: list[RksRecord], record: RksRecord, new_rks: float,
                   new_ap: bool | None = None) -> tuple[float, RksRecord | None, bool]:
    projection = project_change(records, record, new_rks, new_ap)
    return projection.total_gain, projection.replaced, projection.entered_best
