"""XinChao API client with auto-login and token caching (async)."""

import json
import time
import logging
import httpx
from config import API_URL, ADMIN_EMAIL, ADMIN_PASSWORD

logger = logging.getLogger("xinchao-mcp.api")

# Must complete before tose.sh proxy 30s timeout
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0)

_token_cache = {"token": None, "expires_at": 0}

_client = httpx.AsyncClient(
    timeout=DEFAULT_TIMEOUT,
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=120),
)


def _parse_json(resp: httpx.Response) -> dict:
    """Safely parse JSON response."""
    content_type = resp.headers.get("content-type", "")
    if "application/json" not in content_type:
        raise ValueError(f"API returned non-JSON (status={resp.status_code}): {resp.text[:200]}")
    return resp.json()


async def _login() -> str:
    """Login to XinChao admin API, cache token for 23h."""
    t0 = time.monotonic()
    logger.info(">>> Login starting")
    try:
        resp = await _client.post(f"{API_URL}/admin/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        logger.info("<<< Login done in %.1fs (status=%s)", time.monotonic() - t0, resp.status_code)
        if resp.status_code >= 400:
            raise ValueError(f"Login failed (status={resp.status_code}): {resp.text[:200]}")
        data = _parse_json(resp)
        meta = data.get("metadata", {})
        token = (meta.get("accessToken") or meta.get("token")
                 or data.get("accessToken") or data.get("token"))
        if not token:
            raise ValueError(f"Cannot extract token from: {json.dumps(data)[:200]}")
        _token_cache["token"] = token
        _token_cache["expires_at"] = time.time() + 82800  # 23h
        return token
    except httpx.TimeoutException as e:
        logger.error("Login timeout: %s", e)
        raise
    except httpx.HTTPError as e:
        logger.error("Login HTTP error: %s", e)
        raise


async def _get_token() -> str:
    """Get valid token, auto-login if expired."""
    if _token_cache["token"] and _token_cache["expires_at"] > time.time():
        return _token_cache["token"]
    return await _login()


async def api(method: str, path: str, data=None, params=None) -> dict:
    """Authenticated API request with auto-retry on 401."""
    t0 = time.monotonic()
    logger.info(">>> %s %s starting", method, path)
    try:
        token = await _get_token()
        resp = await _client.request(
            method, f"{API_URL}{path}",
            json=data, params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        logger.info("<<< %s %s done in %.1fs (status=%s)", method, path, time.monotonic() - t0, resp.status_code)

        # Auto re-login on 401
        if resp.status_code == 401:
            _token_cache["token"] = None
            token = await _login()
            resp = await _client.request(
                method, f"{API_URL}{path}",
                json=data, params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            logger.info("<<< %s %s retry done in %.1fs (status=%s)", method, path, time.monotonic() - t0, resp.status_code)

        if resp.status_code >= 400:
            return {"error": resp.status_code, "message": resp.text[:500]}
        return _parse_json(resp)

    except httpx.TimeoutException as e:
        logger.warning("Timeout %s %s after %.1fs: %s", method, path, time.monotonic() - t0, e)
        return {"error": "timeout", "message": f"Request timed out after {time.monotonic() - t0:.1f}s: {e}"}
    except httpx.HTTPError as e:
        logger.error("HTTP error %s %s: %s", method, path, e)
        return {"error": "http_error", "message": str(e)}
    except Exception as e:
        logger.exception("Unexpected error %s %s", method, path)
        return {"error": "unexpected", "message": str(e)}
