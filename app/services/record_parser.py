from __future__ import annotations

import io
import struct
from dataclasses import replace

from app.models.schemas import PlayerData, Record
from app.services.rks import chart_rks

DIFFICULTIES = ("EZ", "HD", "IN", "AT")


class ParseError(ValueError):
    pass


def normalize_player(payload: dict, charts: dict[tuple[str, str], dict]) -> PlayerData:
    records = []
    for row in payload.get("records", []):
        song_id = str(row.get("song_id", "unknown"))
        diff = str(row.get("difficulty", "unknown")).upper()
        meta = charts.get((song_id, diff)) or charts.get((song_id.removesuffix(".0"), diff))
        constant = float(row["constant"]) if row.get("constant") is not None else (meta["constant"] if meta else None)
        acc = max(0.0, min(100.0, float(row.get("accuracy", 0))))
        score = max(0, min(1_000_000, int(row.get("score", 0))))
        rec = Record(song_id=song_id, song=str(row.get("song") or (meta["song"] if meta else "Unknown chart")),
                     difficulty=diff, constant=constant, score=score, accuracy=acc,
                     fc=bool(row.get("fc", False)), ap=bool(row.get("ap", score >= 1_000_000)), known=meta is not None or constant is not None)
        records.append(replace(rec, chart_rks=chart_rks(constant, acc)))
    return PlayerData(nickname=str(payload.get("nickname") or "Phigros Player"), records=records,
                      source_rks=float(payload["source_rks"]) if payload.get("source_rks") is not None else None)


class Reader:
    def __init__(self, data: bytes):
        self.fp = io.BytesIO(data)

    def read(self, n: int) -> bytes:
        out = self.fp.read(n)
        if len(out) != n:
            raise ParseError("unexpected end of gameRecord")
        return out

    def byte(self) -> int:
        return self.read(1)[0]

    def varshort(self) -> int:
        first = self.byte()
        return first if first < 128 else (first & 0x7F) | (self.byte() << 7)

    def string(self) -> str:
        size = self.varshort()
        if size < 0 or size > 4096:
            raise ParseError("invalid string size")
        return self.read(size).decode("utf-8")


def parse_game_record(data: bytes, charts: dict[tuple[str, str], dict], nickname: str = "Phigros Player") -> PlayerData:
    """Parse decrypted gameRecord v1 payload (version byte may be included)."""
    if not data:
        raise ParseError("empty gameRecord")
    if data[0] == 1:
        data = data[1:]
    rd = Reader(data)
    rows = []
    for _ in range(rd.varshort()):
        song_id = rd.string()
        block_len = rd.byte()
        block = Reader(rd.read(block_len))
        exists, fc_mask = block.byte(), block.byte()
        for i, diff in enumerate(DIFFICULTIES):
            if exists & (1 << i):
                score = struct.unpack("<I", block.read(4))[0]
                acc = struct.unpack("<f", block.read(4))[0]
                meta = charts.get((song_id, diff)) or charts.get((song_id.removesuffix(".0"), diff))
                rows.append({"song_id": song_id, "song": meta["song"] if meta else "Unknown chart", "difficulty": diff,
                             "constant": meta["constant"] if meta else None, "score": score, "accuracy": acc,
                             "fc": bool(fc_mask & (1 << i)), "ap": score >= 1_000_000})
    return normalize_player({"nickname": nickname, "records": rows}, charts)
