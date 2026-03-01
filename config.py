"""
Personal targets and settings for the 15-week cut plan.
Adjust these to match your goals.
"""

import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# --- WHOOP OAuth2 ---
WHOOP_CLIENT_ID = os.getenv("WHOOP_CLIENT_ID", "")
WHOOP_CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET", "")
WHOOP_REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI", "http://localhost:5000/callback")
WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_API_BASE = "https://api.prod.whoop.com/developer/v1"
WHOOP_SCOPES = "read:recovery read:cycles read:sleep read:workout read:profile"

# --- Plan targets ---
START_WEIGHT = 183.0
GOAL_WEIGHT = 160.0
START_DATE = date(2025, 3, 1)
END_DATE = date(2025, 6, 15)
TOTAL_WEEKS = 15

# --- Daily targets ---
CALORIE_TARGET = 1800
PROTEIN_TARGET_G = 140

# --- App settings ---
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")
DATABASE_PATH = os.getenv("DATABASE_PATH", "tracker.db")
TOKEN_PATH = os.getenv("TOKEN_PATH", "whoop_tokens.json")
