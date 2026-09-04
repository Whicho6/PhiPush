from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Record:
    song_id: str
    song: str
    difficulty: str
    constant: float | None
    score: int
    accuracy: float
    fc: bool = False
    ap: bool = False
    chart_rks: float = 0.0
    known: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlayerData:
    nickname: str
    records: list[Record] = field(default_factory=list)
    source_rks: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"nickname": self.nickname, "source_rks": self.source_rks,
                "records": [r.to_dict() for r in self.records]}
