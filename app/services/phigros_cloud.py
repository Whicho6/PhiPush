from __future__ import annotations

import base64
import io
import json
import os
import zipfile

import httpx
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from app.models.schemas import PlayerData
from app.services.record_parser import parse_game_record

# Public protocol identifiers used by the Phigros client. Override if the service changes.
LC_APP_ID = os.getenv("LEANCLOUD_APP_ID", "")
LC_APP_KEY = os.getenv("LEANCLOUD_APP_KEY", "")
LC_BASE = "https://rak3ffdi.cloud.tds1.tapapis.cn/1.1"
AES_KEY_B64 = os.getenv("PHIGROS_AES_KEY_B64", "")
AES_IV_B64 = os.getenv("PHIGROS_AES_IV_B64", "")


class CloudUnavailable(RuntimeError):
    pass


def _decrypt(blob: bytes) -> bytes:
    if not AES_KEY_B64 or not AES_IV_B64:
        raise CloudUnavailable("缺少本地 PHIGROS_AES_KEY_B64 / PHIGROS_AES_IV_B64 配置。")
    decryptor = Cipher(algorithms.AES(base64.b64decode(AES_KEY_B64)), modes.CBC(base64.b64decode(AES_IV_B64))).decryptor()
    padded = decryptor.update(blob) + decryptor.finalize()
    unpadder = PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


async def load_player(session_token: str, charts: dict) -> PlayerData:
    """Read only the newest cloud save. Never uploads or mutates cloud state."""
    if not LC_APP_ID or not LC_APP_KEY:
        raise CloudUnavailable("缺少本地 LEANCLOUD_APP_ID / LEANCLOUD_APP_KEY 配置。")
    headers = {"X-LC-Id": LC_APP_ID, "X-LC-Key": LC_APP_KEY, "X-LC-Session": session_token,
               "User-Agent": "LeanCloud-CSharp-SDK/1.0.3"}
    try:
        # LeanCloud/CDN occasionally drops a fresh connection. Retrying only
        # connection establishment is safe because every request here is GET.
        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, transport=transport) as client:
            user_response = await client.get(f"{LC_BASE}/users/me", headers=headers)
            user_response.raise_for_status()
            user_info = user_response.json()
            response = await client.get(f"{LC_BASE}/classes/_GameSave", params={"order": "-updatedAt", "limit": 1}, headers=headers)
            response.raise_for_status()
            results = response.json().get("results", [])
            if not results:
                raise CloudUnavailable("账号中没有可用的 Phigros 云存档。")
            save = results[0]
            nickname = user_info.get("nickname") or user_info.get("username") or "Phigros Player"
            file_obj = save.get("gameFile") or save.get("file") or {}
            url = file_obj.get("url")
            if not url:
                raise CloudUnavailable("云存档记录缺少下载地址。")
            archive_response = await client.get(url)
            archive_response.raise_for_status()
            archive = zipfile.ZipFile(io.BytesIO(archive_response.content))
            raw = archive.read("gameRecord")
            if not raw or raw[0] != 1:
                raise CloudUnavailable("暂不支持此 gameRecord 版本。")
            player = parse_game_record(bytes([raw[0]]) + _decrypt(raw[1:]), charts, nickname)
            summary = save.get("summary")
            if summary:
                try:
                    raw_summary = base64.b64decode(summary)
                    if len(raw_summary) >= 7:
                        import struct
                        player.source_rks = float(struct.unpack_from("<f", raw_summary, 3)[0])
                except Exception:
                    pass
            return player
    except CloudUnavailable:
        raise
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403):
            raise CloudUnavailable("SessionToken 无效或已过期。") from None
        raise CloudUnavailable(f"云存档服务返回 HTTP {exc.response.status_code}。") from None
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise CloudUnavailable("连接 Phigros 云存档服务超时，请检查网络后重新扫码。") from None
    except httpx.RequestError:
        raise CloudUnavailable("读取 Phigros 云存档时网络中断，请重新扫码后再试。") from None
    except Exception as exc:
        raise CloudUnavailable(f"无法读取云存档：{type(exc).__name__}") from None
