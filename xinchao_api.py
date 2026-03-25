"""XinChao API client with auto-login and token caching."""

import json
import time
import requests
from config import API_URL, ADMIN_EMAIL, ADMIN_PASSWORD

_token_cache = {"token": None, "expires_at": 0}


def _login():
    """Login to XinChao admin API, cache token for 23h."""
    resp = requests.post(f"{API_URL}/admin/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # Extract token from various response shapes
    meta = data.get("metadata", {})
    token = (meta.get("accessToken") or meta.get("token")
             or data.get("accessToken") or data.get("token"))
    if not token:
        raise ValueError(f"Cannot extract token: {json.dumps(data)}")
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
    resp.raise_for_status()
    return resp.json()
