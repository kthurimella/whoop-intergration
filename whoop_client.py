"""
WHOOP API v2 client.

Wraps the endpoints for cycles, recovery, sleep, and workouts.
All methods return parsed JSON dicts or None on failure.
"""

from datetime import date, timedelta

import requests

import auth
import config


class WhoopClient:
    """Thin wrapper around the WHOOP Developer API."""

    def __init__(self):
        self.base = config.WHOOP_API_BASE

    def _headers(self) -> dict | None:
        token = auth.get_valid_token()
        if not token:
            return None
        return {"Authorization": f"Bearer {token}"}

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        headers = self._headers()
        if not headers:
            return None
        try:
            resp = requests.get(
                f"{self.base}{path}", headers=headers, params=params, timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return None

    # --- Cycles (daily strain + calories) ---

    def get_cycles(self, start: date | None = None, end: date | None = None) -> list:
        """Get physiological cycles (strain, calories burned)."""
        if not start:
            start = date.today() - timedelta(days=1)
        if not end:
            end = date.today()
        params = {
            "start": f"{start}T00:00:00.000Z",
            "end": f"{end}T23:59:59.999Z",
        }
        data = self._get("/cycle", params)
        return data.get("records", []) if data else []

    def get_latest_cycle(self) -> dict | None:
        cycles = self.get_cycles()
        return cycles[0] if cycles else None

    # --- Recovery ---

    def get_recovery(self, start: date | None = None, end: date | None = None) -> list:
        """Get recovery scores (HRV, resting HR, recovery %)."""
        if not start:
            start = date.today() - timedelta(days=1)
        if not end:
            end = date.today()
        params = {
            "start": f"{start}T00:00:00.000Z",
            "end": f"{end}T23:59:59.999Z",
        }
        data = self._get("/recovery", params)
        return data.get("records", []) if data else []

    def get_latest_recovery(self) -> dict | None:
        recs = self.get_recovery()
        return recs[0] if recs else None

    # --- Sleep ---

    def get_sleep(self, start: date | None = None, end: date | None = None) -> list:
        """Get sleep data (duration, stages, performance %)."""
        if not start:
            start = date.today() - timedelta(days=1)
        if not end:
            end = date.today()
        params = {
            "start": f"{start}T00:00:00.000Z",
            "end": f"{end}T23:59:59.999Z",
        }
        data = self._get("/activity/sleep", params)
        return data.get("records", []) if data else []

    def get_latest_sleep(self) -> dict | None:
        sleeps = self.get_sleep()
        return sleeps[0] if sleeps else None

    # --- Workouts ---

    def get_workouts(self, start: date | None = None, end: date | None = None) -> list:
        """Get workout data."""
        if not start:
            start = date.today() - timedelta(days=1)
        if not end:
            end = date.today()
        params = {
            "start": f"{start}T00:00:00.000Z",
            "end": f"{end}T23:59:59.999Z",
        }
        data = self._get("/activity/workout", params)
        return data.get("records", []) if data else []

    # --- Profile ---

    def get_profile(self) -> dict | None:
        return self._get("/user/profile/basic")

    # --- Morning snapshot (all-in-one) ---

    def get_morning_snapshot(self) -> dict:
        """Pull recovery, sleep, latest cycle, and workouts in one call."""
        return {
            "recovery": self.get_latest_recovery(),
            "sleep": self.get_latest_sleep(),
            "cycle": self.get_latest_cycle(),
            "workouts": self.get_workouts(),
        }
