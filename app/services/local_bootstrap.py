from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
from pathlib import Path
from typing import Callable

import httpx


class BootstrapError(RuntimeError):
    pass


UPSTREAM_COMMIT = "e4bdbeab45feb74c50ef837201d225383acc0ac1"
UPSTREAM_BASE = (
    "https://raw.githubusercontent.com/DeepSeek-V4-Pro/"
    f"phigros-b30-plugin/{UPSTREAM_COMMIT}"
)
FILES = {
    "tap_auth.py": ("tap_auth.py", "e6e5fa0762ca52111ca11eb108af0a7234650ed4f5a38326466d992353bd45d9"),
    "encrypt.py": ("lib_save/encrypt.py", "369bfa1e10b61b2a1bc5ece8eb9909da8d010028e0de2ab684188b24ca9853ce"),
    "info.csv": ("resources/info.csv", "9f7f63d44da3b148b963ddf85d9a9beb7413e14c9f8d2952a5bcd37c3f52bc9f"),
    "difficulty.csv": ("resources/difficulty.csv", "f8a492b129857142288cd6905a4da9a5f70fbbe7234a964de09e11dd6d1f5711"),
}
REQUIRED_CONFIG = (
    "PHIGROS_CLIENT_ID",
    "PHIGROS_CLIENT_TOKEN",
    "LEANCLOUD_APP_ID",
    "LEANCLOUD_APP_KEY",
    "PHIGROS_AES_KEY_B64",
    "PHIGROS_AES_IV_B64",
)


def _download(name: str) -> bytes:
    relative, expected = FILES[name]
    try:
        response = httpx.get(f"{UPSTREAM_BASE}/{relative}", timeout=25, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise BootstrapError(f"无法下载本地初始化资源 {name}：{type(exc).__name__}") from None
    content = response.content
    if hashlib.sha256(content).hexdigest() != expected:
        raise BootstrapError(f"上游资源 {name} 校验失败，已拒绝使用。")
    return content


def _capture(source: str, pattern: str, label: str) -> str:
    match = re.search(pattern, source, re.MULTILINE)
    if not match:
        raise BootstrapError(f"无法从固定上游版本读取 {label}。")
    return match.group(1)


def _extract_config(tap_source: str, encrypt_source: str) -> dict[str, str]:
    quoted = r"[\"']([^\"']+)[\"']"
    client_id = _capture(tap_source, rf"^CLIENT_ID\s*=\s*{quoted}", "TapTap Client ID")
    app_id = _capture(tap_source, rf"^LC_ID_CN\s*=\s*{quoted}", "LeanCloud App ID")
    app_key = _capture(tap_source, rf"^LC_APP_KEY_CN\s*=\s*{quoted}", "LeanCloud App Key")
    aes_key = _capture(
        encrypt_source, rf"^KEY\s*=\s*base64\.b64decode\({quoted}\)", "AES Key"
    )
    aes_iv = _capture(
        encrypt_source, rf"^IV\s*=\s*base64\.b64decode\({quoted}\)", "AES IV"
    )
    if client_id != app_id:
        raise BootstrapError("上游 TapTap Client ID 与 LeanCloud App ID 不一致。")
    return {
        "PHIGROS_CLIENT_ID": client_id,
        "PHIGROS_CLIENT_TOKEN": app_key,
        "LEANCLOUD_APP_ID": app_id,
        "LEANCLOUD_APP_KEY": app_key,
        "PHIGROS_AES_KEY_B64": aes_key,
        "PHIGROS_AES_IV_B64": aes_iv,
    }


def _write_env(path: Path, values: dict[str, str]) -> None:
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    present: set[str] = set()
    output: list[str] = []
    changed = False
    for line in existing:
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, current = line.split("=", 1)
            key = key.strip()
            present.add(key)
            if key in values and not current.strip():
                line = f"{key}={values[key]}"
                changed = True
        output.append(line)
    additions = [f"{key}={value}" for key, value in values.items() if key not in present]
    if not additions and not changed:
        return
    if additions:
        output += ([""] if output else []) + additions
    temporary = path.with_suffix(".tmp")
    temporary.write_text("\n".join(output) + "\n", encoding="utf-8")
    temporary.replace(path)


def _build_charts(info_bytes: bytes, difficulty_bytes: bytes, output: Path) -> int:
    names = {
        row["id"]: row["song"]
        for row in csv.DictReader(io.StringIO(info_bytes.decode("utf-8-sig")))
        if row.get("id") and row.get("song")
    }
    charts: list[dict] = []
    for row in csv.DictReader(io.StringIO(difficulty_bytes.decode("utf-8-sig"))):
        song_id = row.get("id")
        if not song_id:
            continue
        for level in ("EZ", "HD", "IN", "AT"):
            value = (row.get(level) or "").strip()
            if value and float(value) > 0:
                charts.append(
                    {
                        "id": song_id,
                        "song": names.get(song_id, song_id),
                        "difficulty": level,
                        "constant": float(value),
                    }
                )
    if not charts:
        raise BootstrapError("上游曲库为空，已拒绝生成。")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(charts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    return len(charts)


def ensure_real_environment(
    root: Path, fetch: Callable[[str], bytes] = _download
) -> tuple[bool, int | None]:
    """Create ignored local real-mode assets without exposing their contents."""
    env_path = root / ".env"
    configured_charts = os.getenv("PHIPUSH_CHART_DATA")
    charts_path = Path(configured_charts).expanduser() if configured_charts else root / "data" / "charts.json"
    if not charts_path.is_absolute():
        charts_path = root / charts_path
    missing_config = [name for name in REQUIRED_CONFIG if not os.getenv(name)]
    wrote_env = False
    chart_count: int | None = None

    if missing_config:
        values = _extract_config(
            fetch("tap_auth.py").decode("utf-8"),
            fetch("encrypt.py").decode("utf-8"),
        )
        _write_env(env_path, {name: values[name] for name in missing_config})
        wrote_env = True

    if not charts_path.is_file():
        chart_count = _build_charts(fetch("info.csv"), fetch("difficulty.csv"), charts_path)

    return wrote_env, chart_count
