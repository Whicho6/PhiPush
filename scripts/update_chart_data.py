"""在用户本地从 info.tsv 与 difficulty.tsv 生成完整曲库。

输入文件不会被上传。使用者必须自行确认其对输入数据拥有合法访问和使用权限。
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ("EZ", "HD", "IN", "AT")


def main() -> None:
    parser = argparse.ArgumentParser(description="从本地 TSV 文件构建 PhiPush 完整曲库")
    parser.add_argument("source", type=Path, help="本地目录，其中包含 info.tsv 和 difficulty.tsv")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "charts.json")
    args = parser.parse_args()
    source = args.source.resolve()
    for required in ("info.tsv", "difficulty.tsv"):
        if not (source / required).is_file():
            parser.error(f"缺少 {source / required}")
    infos = {}
    with (source / "info.tsv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) >= 2:
                infos[row[0]] = row[1]
    charts = []
    with (source / "difficulty.tsv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if not row:
                continue
            song_id, *constants = row
            for level, value in zip(LEVELS, constants):
                if value and float(value) > 0:
                    charts.append({"id": song_id, "song": infos.get(song_id, song_id),
                                   "difficulty": level, "constant": float(value)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(charts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已在本地生成 {len(charts)} 张谱面：{args.output}")
    print("该文件默认被 Git 忽略；请勿在未确认再分发权利时提交。")


if __name__ == "__main__":
    main()
