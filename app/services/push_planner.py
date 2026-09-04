from __future__ import annotations

from dataclasses import asdict, dataclass

from app.models.schemas import Record
from app.services.rks import accuracy_for_rks, build_best, chart_rks, project_change

STEPS = (0.1, 0.25, 0.5, 1.0, 1.5, 2.0)
ACC_MILESTONES = (98.0, 98.5, 99.0, 99.5, 99.7, 99.85, 100.0)


@dataclass(slots=True)
class Opportunity:
    record: Record
    target_accuracy: float
    target_chart_rks: float
    total_gain: float
    acc_gain: float
    score: float
    enters_best: bool
    best_gain: float
    phi_gain: float
    effort: float
    crosses_display_boundary: bool
    route_type: str
    reason: str

    def to_dict(self) -> dict:
        return {**self.record.to_dict(), "target_accuracy": round(self.target_accuracy, 4),
                "target_chart_rks": round(self.target_chart_rks, 6), "estimated_total_rks_gain": round(self.total_gain, 6),
                "required_acc_improvement": round(self.acc_gain, 4), "recommendation_score": round(self.score, 6),
                "enters_best": self.enters_best, "best_gain": round(self.best_gain, 6),
                "phi_gain": round(self.phi_gain, 6), "estimated_effort": round(self.effort, 6),
                "crosses_display_boundary": self.crosses_display_boundary,
                "route_type": self.route_type, "reason": self.reason}


def _next_display_gain(total: float) -> float:
    """Gain required to cross the game's next two-decimal rounding boundary."""
    gain = int(total * 100) / 100 + 0.005 - total
    return gain + 0.01 if gain <= 1e-12 else gain


def _effort(current: float, target: float) -> float:
    """Transparent, deliberately conservative proxy for practice effort.

    It is not a claim about chart difficulty.  The convex precision terms stop
    99.9 -> 100 from looking as cheap as an ordinary 0.1 percentage-point gain.
    """
    delta = max(0.0001, target - current)
    precision = (1.0 + max(0.0, target - 97.0) * 0.7
                 + max(0.0, target - 99.0) * 2.2
                 + max(0.0, target - 99.8) * 12.0)
    ap_tax = 0.35 if target >= 100.0 - 1e-8 else 0.0
    return delta * precision + ap_tax


def _accuracy_for_total_gain(records: list[Record], rec: Record, desired_gain: float) -> float | None:
    """Binary-search the ACC needed for a real P3+B27 total gain."""
    maximum = project_change(records, rec, chart_rks(rec.constant, 100.0), True).total_gain
    if maximum + 1e-10 < desired_gain:
        return None
    low, high = rec.accuracy, 100.0
    for _ in range(45):
        mid = (low + high) / 2
        projection = project_change(records, rec, chart_rks(rec.constant, mid), rec.ap or mid >= 100.0 - 1e-9)
        if projection.total_gain >= desired_gain:
            high = mid
        else:
            low = mid
    return high


def opportunities(records: list[Record], limit: int = 10) -> list[Opportunity]:
    base = build_best(records)
    display_gain = _next_display_gain(base.total)
    out = []
    for rec in records:
        if rec.constant is None or rec.accuracy >= 100:
            continue
        candidates = set(min(100.0, rec.accuracy + x) for x in STEPS)
        candidates.update(x for x in ACC_MILESTONES if rec.accuracy < x <= 100.0)
        needed = accuracy_for_rks(rec.constant, base.cutoff + 1e-6)
        if needed is not None and rec.accuracy < needed <= min(100.0, rec.accuracy + 3.0):
            candidates.add(needed)
        visible_target = _accuracy_for_total_gain(records, rec, display_gain)
        if visible_target is not None and visible_target > rec.accuracy + 1e-7:
            candidates.add(visible_target)
        best = None
        for target in sorted(candidates):
            new_rks = chart_rks(rec.constant, target)
            projection = project_change(records, rec, new_rks, rec.ap or target >= 100.0 - 1e-8)
            gain, entered = projection.total_gain, projection.entered_best
            if gain <= 1e-8:
                continue
            delta = target - rec.accuracy
            effort = _effort(rec.accuracy, target)
            crosses = gain + 1e-8 >= display_gain
            score = gain / effort * (1.08 if crosses else 1.0)
            if projection.phi_gain > 1e-9:
                route_type = "phi"
                reason = (f"推至 100% 后可进入或抬高 P1–P3，并同时计算 B27 变化；"
                          f"P 槽 +{projection.phi_gain:.3f}，B 槽 +{projection.best_gain:.3f}，"
                          f"总 RKS 预计 +{gain:.3f}。")
            elif entered:
                route_type = "enter_best"
                reason = f"提升约 {delta:.2f}% ACC 可进入 B27，预计总 RKS +{gain:.3f}。"
            else:
                route_type = "improve_best"
                reason = f"提升约 {delta:.2f}% ACC 可抬高现有 B27，预计总 RKS +{gain:.3f}。"
            if crosses:
                reason += " 可跨过下一档游戏内两位小数显示线。"
            cand = Opportunity(rec, target, new_rks, gain, delta, score, entered,
                               projection.best_gain, projection.phi_gain, effort,
                               crosses, route_type, reason)
            if best is None or cand.score > best.score:
                best = cand
        if best:
            out.append(best)
    return sorted(out, key=lambda x: (x.score, x.total_gain), reverse=True)[:limit]


def target_route(records: list[Record], target_rks: float, max_steps: int = 10) -> dict:
    working = [Record(**r.to_dict()) for r in records]
    initial = build_best(working).total
    route = []
    while build_best(working).total + 1e-9 < target_rks and len(route) < max_steps:
        choices = opportunities(working, limit=30)
        if not choices:
            break
        choice = choices[0]
        rec = choice.record
        before_acc = rec.accuracy
        rec.accuracy = choice.target_accuracy
        rec.chart_rks = choice.target_chart_rks
        rec.ap = rec.ap or rec.accuracy >= 100
        route.append({"song": rec.song, "difficulty": rec.difficulty, "from_accuracy": round(before_acc, 4),
                      "to_accuracy": round(rec.accuracy, 4), "estimated_total_rks_gain": round(choice.total_gain, 6),
                      "best_gain": round(choice.best_gain, 6), "phi_gain": round(choice.phi_gain, 6),
                      "route_type": choice.route_type})
    final = build_best(working).total
    return {"current_rks": round(initial, 6), "target_rks": target_rks, "required_gain": round(max(0, target_rks-initial), 6),
            "estimated_final_rks": round(final, 6), "reached": final + 1e-9 >= target_rks, "steps": route,
            "disclaimer": "该路线根据数学收益估算，不代表实际谱面难度，也不保证实际结果。"}
