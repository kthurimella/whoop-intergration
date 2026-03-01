"""
Natural language food lookup via the API Ninjas Nutrition API.

Usage:
    result = lookup("chipotle bowl with chicken and rice")
    # Returns: {"calories": 735, "protein_g": 52, "items": [...]}

Requires API_NINJAS_KEY env var.
Free tier (non-commercial): https://api-ninjas.com/api/nutrition
"""

import os

import requests

API_NINJAS_KEY = os.getenv("API_NINJAS_KEY", "")
API_NINJAS_URL = "https://api.api-ninjas.com/v1/nutrition"


def is_configured() -> bool:
    return bool(API_NINJAS_KEY)


def lookup(query: str) -> dict | None:
    """Parse a natural-language food description into calories and protein.

    Returns dict with total calories, protein_g, and individual items,
    or None if the lookup fails.
    """
    if not API_NINJAS_KEY:
        return None

    try:
        resp = requests.get(
            API_NINJAS_URL,
            headers={"X-Api-Key": API_NINJAS_KEY},
            params={"query": query},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return None

    # API returns a list directly (not wrapped in "items" key)
    items_raw = data if isinstance(data, list) else data.get("items", [])
    if not items_raw:
        return None

    total_cal = 0
    total_protein = 0
    items = []

    for f in items_raw:
        cal = round(float(f.get("calories", 0)))
        pro = round(float(f.get("protein_g", 0)))
        total_cal += cal
        total_protein += pro
        items.append({
            "name": f.get("name", "unknown"),
            "qty": round(float(f.get("serving_size_g", 100))),
            "unit": "g",
            "calories": cal,
            "protein_g": pro,
        })

    return {
        "calories": total_cal,
        "protein_g": total_protein,
        "items": items,
    }
