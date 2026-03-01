"""
OAuth2 authentication for the WHOOP API.

Handles the full browser-based OAuth2 flow:
  1. Redirects user to WHOOP login
  2. Captures the callback with auth code
  3. Exchanges code for access + refresh tokens
  4. Auto-refreshes tokens when they expire

Tokens are saved to the SQLite database so they persist across restarts.
"""

import json
import time
from urllib.parse import urlencode

import requests

import config
import tracker

_TOKEN_KEY = "whoop_tokens"


def get_auth_url(state: str = "") -> str:
    """Build the WHOOP authorization URL."""
    params = {
        "client_id": config.WHOOP_CLIENT_ID,
        "redirect_uri": config.WHOOP_REDIRECT_URI,
        "response_type": "code",
        "scope": config.WHOOP_SCOPES,
        "state": state,
    }
    return f"{config.WHOOP_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    """Exchange an authorization code for access + refresh tokens."""
    resp = requests.post(
        config.WHOOP_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.WHOOP_REDIRECT_URI,
            "client_id": config.WHOOP_CLIENT_ID,
            "client_secret": config.WHOOP_CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    tokens = resp.json()
    tokens["obtained_at"] = time.time()
    _save_tokens(tokens)
    return tokens


def refresh_tokens(refresh_token: str) -> dict:
    """Use a refresh token to get a new access token."""
    resp = requests.post(
        config.WHOOP_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config.WHOOP_CLIENT_ID,
            "client_secret": config.WHOOP_CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    tokens = resp.json()
    tokens["obtained_at"] = time.time()
    _save_tokens(tokens)
    return tokens


def get_valid_token() -> str | None:
    """Return a valid access token, refreshing if needed. Returns None if not authenticated."""
    tokens = _load_tokens()
    if not tokens:
        return None

    # Refresh if token is older than 50 minutes (tokens last 60 min)
    age = time.time() - tokens.get("obtained_at", 0)
    if age > 3000:
        try:
            tokens = refresh_tokens(tokens["refresh_token"])
        except requests.RequestException:
            return None

    return tokens.get("access_token")


def is_authenticated() -> bool:
    """Check if we have saved tokens."""
    return _load_tokens() is not None


def clear_tokens():
    """Delete saved tokens (logout)."""
    tracker.kv_delete(_TOKEN_KEY)


def _save_tokens(tokens: dict):
    tracker.kv_set(_TOKEN_KEY, json.dumps(tokens))


def _load_tokens() -> dict | None:
    raw = tracker.kv_get(_TOKEN_KEY)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
