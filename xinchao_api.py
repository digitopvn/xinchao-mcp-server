"""XinChao API client with auto-login and token caching."""

import json
import time
import requests
from config import API_URL, ADMIN_EMAIL, ADMIN_PASSWORD

_token_cache = {"token": None, "expires_at": 0}


def _parse_json(resp):
    """Safely parse JSON response, raise clear error if not JSON."""
    content_type = resp.headers.get("content-type", "")
    if "application/json" not in content_type:
        raise ValueError(f"API returned non-JSON (status={resp.status_code}): {resp.text[:200]}")
    return resp.json()


def _login():
    """Login to XinChao admin API, cache token for 23h."""
    resp = requests.post(f"{API_URL}/admin/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    }, timeout=15)
    if resp.status_code >= 400:
        raise ValueError(f"Login failed (status={resp.status_code}): {resp.text[:200]}")
    data = _parse_json(resp)
    # Extract token from various response shapes
    meta = data.get("metadata", {})
    token = (meta.get("accessToken") or meta.get("token")
             or data.get("accessToken") or data.get("token"))
    if not token:
        raise ValueError(f"Cannot extract token from: {json.dumps(data)[:200]}")
    _token_cache["token"] = token
    _token_cache["expires_at"] = time.time() + 82800  # 23h
    return token


def _get_token():
    """Get valid token, auto-login if expired."""
    if _token_cache["token"] and _token_cache["expires_at"] > time.time():
        return _token_cache["token"]
    return _login()


def api(method, path, data=None, params=None):
    """Authenticated API request with auto-retry on 401."""
    token = _get_token()
    resp = requests.request(method, f"{API_URL}{path}",
                            json=data, params=params,
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=30)
    # Auto re-login on 401
    if resp.status_code == 401:
        _token_cache["token"] = None
        token = _login()
        resp = requests.request(method, f"{API_URL}{path}",
                                json=data, params=params,
                                headers={"Authorization": f"Bearer {token}"},
                                timeout=30)
    if resp.status_code >= 400:
        return {"error": resp.status_code, "message": resp.text[:500]}
    return _parse_json(resp)
