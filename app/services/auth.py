from __future__ import annotations
import asyncio, base64, hashlib, hmac, io, json, os, secrets, time, uuid
from dataclasses import dataclass
from typing import Awaitable, Callable
from urllib.parse import urlsplit
import httpx
import qrcode

# Public Phigros client configuration (Client ID/Client Token), not a Master Key.
PHIGROS_CLIENT_ID = os.getenv("PHIGROS_CLIENT_ID", "")
PHIGROS_CLIENT_TOKEN = os.getenv("PHIGROS_CLIENT_TOKEN", "")
TAP_DEVICE_URL = "https://accounts.tapapis.cn/oauth2/v1/device/code"
TAP_TOKEN_URL = "https://accounts.tapapis.cn/oauth2/v1/token"
TAP_PROFILE_URL = "https://open.tapapis.cn/account/profile/v1"
LC_USERS_URL = "https://rak3ffdi.cloud.tds1.tapapis.cn/1.1/users"

class TapTapAuthError(RuntimeError): pass
class TapTapQrExpired(TapTapAuthError): pass

@dataclass(slots=True)
class LoginAttempt:
    login_id: str; device_code: str; device_id: str; qr_url: str; qr_image: str
    verification_url: str; expires_at: float; interval: int; status: str = "pending"
    phipush_session: str | None = None; error: str | None = None

class TapTapAuth:
    """TapTap device authorization followed by Phigros LeanCloud login."""
    def __init__(self):
        self.attempts: dict[str, LoginAttempt] = {}
        self._tasks: set[asyncio.Task] = set()

    @property
    def available(self) -> bool: return bool(PHIGROS_CLIENT_ID and PHIGROS_CLIENT_TOKEN)

    @staticmethod
    def _qr_data_uri(url: str) -> str:
        image = qrcode.make(url); buf = io.BytesIO(); image.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    async def start(self, on_token: Callable[[str], Awaitable[str]]) -> LoginAttempt:
        if not self.available: raise TapTapAuthError("Phigros client configuration is unavailable")
        device_id = uuid.uuid4().hex
        form = {"client_id": PHIGROS_CLIENT_ID, "response_type": "device_code", "scope": "public_profile",
                "version": "2.1", "platform": "unity", "info": json.dumps({"device_id": device_id}, separators=(",", ":"))}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                data = self._response_data(await client.post(TAP_DEVICE_URL, data=form), "request device code")
        except TapTapQrExpired as exc:
            item.status = "expired"
            item.error = str(exc)
        except httpx.RequestError as exc:
            raise TapTapAuthError(
                "无法连接 TapTap 授权服务。请检查本机网络、代理或防火墙后重试。"
            ) from exc
        qr_url, device_code = data.get("qrcode_url") or data.get("verification_uri_complete"), data.get("device_code")
        if not qr_url or not device_code: raise TapTapAuthError("TapTap did not return a QR URL and device code")
        item = LoginAttempt(secrets.token_urlsafe(18), device_code, device_id, qr_url, self._qr_data_uri(qr_url), qr_url,
                            time.time() + min(int(data.get("expires_in", 600)), 600), max(2, int(data.get("interval", 2))))
        self.attempts[item.login_id] = item
        task = asyncio.create_task(self._complete(item, on_token)); self._tasks.add(task); task.add_done_callback(self._tasks.discard)
        return item

    @staticmethod
    def _response_data(response: httpx.Response, action: str) -> dict:
        try: payload = response.json()
        except ValueError: raise TapTapAuthError(f"TapTap returned invalid data while trying to {action}") from None
        if response.status_code >= 400:
            message = payload.get("data", {}).get("error") or payload.get("error") or response.status_code
            raise TapTapAuthError(f"TapTap {action} failed: {message}")
        return payload.get("data", payload)

    async def _complete(self, item: LoginAttempt, on_token: Callable[[str], Awaitable[str]]) -> None:
        try:
            access = await self._poll(item); item.status = "authorizing"
            profile = await self._profile(access); session_token = await self._leancloud_login(profile, access)
            try: item.phipush_session = await on_token(session_token)
            finally: session_token = ""
            item.status = "success"
        except httpx.RequestError as exc:
            item.status = "expired" if time.time() >= item.expires_at else "error"
            item.error = "登录过程中无法连接 TapTap 或 Phigros 云服务，请检查网络后重新扫码。"
        except Exception as exc:
            item.status = "expired" if time.time() >= item.expires_at else "error"; item.error = str(exc)

    async def _poll(self, item: LoginAttempt) -> dict:
        form = {"grant_type": "device_token", "client_id": PHIGROS_CLIENT_ID, "secret_type": "hmac-sha-1",
                "code": item.device_code, "version": "1.0", "platform": "unity",
                "info": json.dumps({"device_id": item.device_id}, separators=(",", ":"))}
        async with httpx.AsyncClient(timeout=15) as client:
            while time.time() < item.expires_at:
                response = await client.post(TAP_TOKEN_URL, data=form)
                try: payload = response.json()
                except ValueError: raise TapTapAuthError("TapTap token endpoint returned invalid data") from None
                if payload.get("success") and isinstance(payload.get("data"), dict): return payload["data"]
                error = payload.get("data", {}).get("error") or payload.get("error")
                if error == "authorization_waiting": item.status = "scanned"
                elif error in ("expired_token", "invalid_device_code", "invalid_grant"):
                    raise TapTapQrExpired("二维码已过期，请点击 TapTap 扫码登录生成新的二维码。")
                elif error not in (None, "authorization_pending", "authorization_waiting"):
                    raise TapTapAuthError(f"TapTap authorization failed: {error}")
                await asyncio.sleep(item.interval)
        raise TapTapQrExpired("二维码已过期，请点击 TapTap 扫码登录生成新的二维码。")

    async def _profile(self, access: dict) -> dict:
        if not access.get("kid") or not access.get("mac_key"): raise TapTapAuthError("TapTap token is missing MAC credentials")
        query = f"client_id={PHIGROS_CLIENT_ID}"; url = f"{TAP_PROFILE_URL}?{query}"; parts = urlsplit(url)
        ts, nonce = str(int(time.time())), base64.b64encode(os.urandom(16)).decode("ascii")
        normalized = f"{ts}\n{nonce}\nGET\n{parts.path}?{query}\n{parts.hostname}\n443\n\n"
        mac = base64.b64encode(hmac.new(access["mac_key"].encode(), normalized.encode(), hashlib.sha1).digest()).decode()
        authorization = f'MAC id="{access["kid"]}",ts="{ts}",nonce="{nonce}",mac="{mac}"'
        async with httpx.AsyncClient(timeout=15) as client:
            return self._response_data(await client.get(url, headers={"Authorization": authorization}), "get profile")

    async def _leancloud_login(self, profile: dict, access: dict) -> str:
        timestamp = str(int(time.time())); signature = hashlib.md5(f"{timestamp}{PHIGROS_CLIENT_TOKEN}".encode()).hexdigest()
        headers = {"X-LC-Id": PHIGROS_CLIENT_ID, "X-LC-Sign": f"{signature},{timestamp}"}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(LC_USERS_URL, headers=headers, json={"authData": {"taptap": {**profile, **access}}})
            try: data = response.json()
            except ValueError: raise TapTapAuthError("LeanCloud returned invalid login data") from None
        if response.status_code not in (200, 201) or not data.get("sessionToken"):
            raise TapTapAuthError(f"Phigros LeanCloud login failed: {data.get('error', response.status_code)}")
        return data["sessionToken"]

    def get(self, login_id: str) -> LoginAttempt | None:
        item = self.attempts.get(login_id)
        if item and item.expires_at < time.time() and item.status not in ("success", "error", "expired"):
            item.status = "expired"
            item.error = "二维码已过期，请点击 TapTap 扫码登录生成新的二维码。"
        return item
