"""
Natural language food lookup via the Nutritionix API.

Usage:
    result = lookup("chipotle bowl with chicken and rice")
    # Returns: {"calories": 735, "protein_g": 52, "items": [...]}

Requires NUTRITIONIX_APP_ID and NUTRITIONIX_API_KEY env vars.
Free tier: https://developer.nutritionix.com/
"""

import os

import requests

NUTRITIONIX_APP_ID = os.getenv("NUTRITIONIX_APP_ID", "")
NUTRITIONIX_API_KEY = os.getenv("NUTRITIONIX_API_KEY", "")
NUTRITIONIX_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"


def lookup(query: str) -> dict | None:
    """Parse a natural-language food description into calories and protein.

    Returns dict with total calories, protein_g, and individual items,
    or None if the lookup fails.
    """
    if not NUTRITIONIX_APP_ID or not NUTRITIONIX_API_KEY:
        return None

    try:
        resp = requests.post(
            NUTRITIONIX_URL,
            headers={
                "x-app-id": NUTRITIONIX_APP_ID,
                "x-app-key": NUTRITIONIX_API_KEY,
                "Content-Type": "application/json",
            },
            json={"query": query},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return None

    foods = data.get("foods", [])
    if not foods:
        return None

    total_cal = 0
    total_protein = 0
    items = []

    for f in foods:
        cal = round(f.get("nf_calories", 0))
        pro = round(f.get("nf_protein", 0))
        total_cal += cal
        total_protein += pro
        items.append({
            "name": f.get("food_name", "unknown"),
            "qty": f.get("serving_qty", 1),
            "unit": f.get("serving_unit", "serving"),
            "calories": cal,
            "protein_g": pro,
        })

    return {
        "calories": total_cal,
        "protein_g": total_protein,
        "items": items,
    }
