from __future__ import annotations

import json
from pathlib import Path

from app.services.local_bootstrap import ensure_real_environment


TAP = '''
CLIENT_ID = "same-id"
LC_APP_KEY_CN = "app-key"
LC_ID_CN = "same-id"
'''
ENCRYPT = '''
KEY = base64.b64decode("a2V5")
IV = base64.b64decode("aXY=")
'''
INFO = b"id,song\ntrack.id,Track Name\n"
DIFFICULTY = b"id,EZ,HD,IN,AT\ntrack.id,1.0,6.5,12.5,\n"


def test_bootstrap_generates_ignored_local_shapes(tmp_path: Path, monkeypatch):
    for name in (
        "PHIGROS_CLIENT_ID",
        "PHIGROS_CLIENT_TOKEN",
        "LEANCLOUD_APP_ID",
        "LEANCLOUD_APP_KEY",
        "PHIGROS_AES_KEY_B64",
        "PHIGROS_AES_IV_B64",
    ):
        monkeypatch.delenv(name, raising=False)

    (tmp_path / ".env").write_text("PHIGROS_CLIENT_ID=\n", encoding="utf-8")
    payloads = {
        "tap_auth.py": TAP.encode(),
        "encrypt.py": ENCRYPT.encode(),
        "info.csv": INFO,
        "difficulty.csv": DIFFICULTY,
    }
    wrote_env, count = ensure_real_environment(tmp_path, payloads.__getitem__)

    assert wrote_env is True
    assert count == 3
    env = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "PHIGROS_CLIENT_ID=same-id" in env
    charts = json.loads((tmp_path / "data" / "charts.json").read_text(encoding="utf-8"))
    assert [chart["difficulty"] for chart in charts] == ["EZ", "HD", "IN"]
    assert all(chart["song"] == "Track Name" for chart in charts)
