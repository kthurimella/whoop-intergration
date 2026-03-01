"""
Flask web app — your WHOOP + weight-cut dashboard.

Run locally:  python app.py
Deploy to Render/Railway and access from your phone.
"""

import secrets
from datetime import date, timedelta

from flask import Flask, redirect, render_template, request, session, url_for

import auth
import config
import tracker
from whoop_client import WhoopClient

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# ── Helpers ──────────────────────────────────────────────────────────────

def _plan_progress() -> dict:
    """Calculate where we are in the 15-week plan."""
    today = date.today()
    total_days = (config.END_DATE - config.START_DATE).days
    elapsed_days = (today - config.START_DATE).days
    elapsed_days = max(0, min(elapsed_days, total_days))
    week_number = elapsed_days // 7 + 1

    total_to_lose = config.START_WEIGHT - config.GOAL_WEIGHT
    latest = tracker.get_latest_weight()
    current_weight = latest["weight"] if latest else config.START_WEIGHT
    lost_so_far = config.START_WEIGHT - current_weight

    expected_rate = total_to_lose / total_days if total_days else 0
    expected_weight = config.START_WEIGHT - (expected_rate * elapsed_days)

    return {
        "week": min(week_number, config.TOTAL_WEEKS),
        "total_weeks": config.TOTAL_WEEKS,
        "pct": round(elapsed_days / total_days * 100) if total_days else 0,
        "current_weight": current_weight,
        "goal_weight": config.GOAL_WEIGHT,
        "start_weight": config.START_WEIGHT,
        "lost": round(lost_so_far, 1),
        "remaining": round(current_weight - config.GOAL_WEIGHT, 1),
        "expected_weight": round(expected_weight, 1),
        "ahead": round(expected_weight - current_weight, 1),
    }


def _format_sleep_duration(ms: int | None) -> str:
    if not ms:
        return "--"
    hours = ms / 3_600_000
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"


# ── Routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Main dashboard page."""
    whoop_data = None
    whoop_connected = auth.is_authenticated()

    if whoop_connected:
        client = WhoopClient()
        whoop_data = client.get_morning_snapshot()

    # Parse WHOOP data for the template
    recovery = None
    sleep = None
    strain = None

    if whoop_data:
        rec = whoop_data.get("recovery")
        if rec and rec.get("score"):
            s = rec["score"]
            recovery = {
                "score": s.get("recovery_score", 0),
                "hrv": round(s.get("hrv_rmssd_milli", 0), 1),
                "resting_hr": s.get("resting_heart_rate", 0),
                "spo2": s.get("spo2_percentage"),
            }

        slp = whoop_data.get("sleep")
        if slp and slp.get("score"):
            s = slp["score"]
            stage = s.get("stage_summary", {})
            sleep = {
                "performance": s.get("sleep_performance_percentage", 0),
                "duration": _format_sleep_duration(
                    stage.get("total_in_bed_time_milli")
                ),
                "deep": _format_sleep_duration(
                    stage.get("total_slow_wave_sleep_time_milli")
                ),
                "rem": _format_sleep_duration(
                    stage.get("total_rem_sleep_time_milli")
                ),
                "efficiency": s.get("sleep_efficiency_percentage", 0),
            }

        cyc = whoop_data.get("cycle")
        if cyc and cyc.get("score"):
            s = cyc["score"]
            strain = {
                "score": round(s.get("strain", 0), 1),
                "calories": round(s.get("kilojoule", 0) / 4.184),
                "avg_hr": s.get("average_heart_rate", 0),
                "max_hr": s.get("max_heart_rate", 0),
            }

    plan = _plan_progress()
    today_food = tracker.get_food()
    weight_history = tracker.get_weight_history(days=14)
    weekly = tracker.get_weekly_averages(weeks=4)

    # Calorie deficit estimate
    deficit = None
    if strain and today_food:
        burned = strain["calories"]
        eaten = today_food["calories"]
        deficit = burned - eaten

    return render_template(
        "dashboard.html",
        whoop_connected=whoop_connected,
        recovery=recovery,
        sleep=sleep,
        strain=strain,
        plan=plan,
        today_food=today_food,
        weight_history=weight_history,
        weekly=weekly,
        deficit=deficit,
        calorie_target=config.CALORIE_TARGET,
        protein_target=config.PROTEIN_TARGET_G,
    )


@app.route("/log", methods=["POST"])
def log_entry():
    """Log weight or food from the web form."""
    entry_type = request.form.get("type")

    if entry_type == "weight":
        weight = request.form.get("weight")
        if weight:
            tracker.log_weight(float(weight))

    elif entry_type == "food":
        calories = request.form.get("calories")
        protein = request.form.get("protein", "0")
        if calories:
            tracker.log_food(int(calories), int(protein or 0))

    return redirect(url_for("index"))


@app.route("/login")
def login():
    """Start WHOOP OAuth2 flow."""
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    return redirect(auth.get_auth_url(state))


@app.route("/callback")
def callback():
    """Handle WHOOP OAuth2 callback."""
    error = request.args.get("error")
    if error:
        return f"Authorization failed: {error}", 400

    code = request.args.get("code")
    if not code:
        return "Missing authorization code", 400

    auth.exchange_code(code)
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    """Clear tokens and disconnect WHOOP."""
    auth.clear_tokens()
    return redirect(url_for("index"))


@app.route("/history")
def history():
    """Full history view."""
    weight_history = tracker.get_weight_history(days=90)
    food_history = tracker.get_food_history(days=90)
    weekly = tracker.get_weekly_averages(weeks=12)
    return render_template(
        "history.html",
        weight_history=weight_history,
        food_history=food_history,
        weekly=weekly,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
