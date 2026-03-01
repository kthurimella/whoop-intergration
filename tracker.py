"""
Local SQLite-backed weight and food logger.

Provides functions for the web app to call, plus a CLI interface:
  python tracker.py weight 181.4
  python tracker.py food 1780 156
  python tracker.py history
  python tracker.py weekly
"""

import sqlite3
import sys
from datetime import date, timedelta

import config


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weight_log (
            date TEXT PRIMARY KEY,
            weight REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS food_log (
            date TEXT PRIMARY KEY,
            calories INTEGER NOT NULL,
            protein_g INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kv_store (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


# --- Weight ---

def log_weight(weight: float, day: date | None = None) -> None:
    day = day or date.today()
    db = _get_db()
    db.execute(
        "INSERT OR REPLACE INTO weight_log (date, weight) VALUES (?, ?)",
        (str(day), weight),
    )
    db.commit()
    db.close()


def get_weight(day: date | None = None) -> float | None:
    day = day or date.today()
    db = _get_db()
    row = db.execute("SELECT weight FROM weight_log WHERE date = ?", (str(day),)).fetchone()
    db.close()
    return row["weight"] if row else None


def get_weight_history(days: int = 30) -> list[dict]:
    db = _get_db()
    cutoff = date.today() - timedelta(days=days)
    rows = db.execute(
        "SELECT date, weight FROM weight_log WHERE date >= ? ORDER BY date DESC",
        (str(cutoff),),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_latest_weight() -> dict | None:
    db = _get_db()
    row = db.execute(
        "SELECT date, weight FROM weight_log ORDER BY date DESC LIMIT 1"
    ).fetchone()
    db.close()
    return dict(row) if row else None


# --- Food ---

def log_food(calories: int, protein_g: int = 0, day: date | None = None) -> None:
    day = day or date.today()
    db = _get_db()
    db.execute(
        "INSERT OR REPLACE INTO food_log (date, calories, protein_g) VALUES (?, ?, ?)",
        (str(day), calories, protein_g),
    )
    db.commit()
    db.close()


def get_food(day: date | None = None) -> dict | None:
    day = day or date.today()
    db = _get_db()
    row = db.execute("SELECT * FROM food_log WHERE date = ?", (str(day),)).fetchone()
    db.close()
    return dict(row) if row else None


def get_food_history(days: int = 30) -> list[dict]:
    db = _get_db()
    cutoff = date.today() - timedelta(days=days)
    rows = db.execute(
        "SELECT * FROM food_log WHERE date >= ? ORDER BY date DESC",
        (str(cutoff),),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# --- Key-value store (for tokens, settings, etc.) ---

def kv_set(key: str, value: str) -> None:
    db = _get_db()
    db.execute(
        "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
        (key, value),
    )
    db.commit()
    db.close()


def kv_get(key: str) -> str | None:
    db = _get_db()
    row = db.execute("SELECT value FROM kv_store WHERE key = ?", (key,)).fetchone()
    db.close()
    return row["value"] if row else None


def kv_delete(key: str) -> None:
    db = _get_db()
    db.execute("DELETE FROM kv_store WHERE key = ?", (key,))
    db.commit()
    db.close()


# --- Weekly summaries ---

def get_weekly_averages(weeks: int = 4) -> list[dict]:
    """Return weekly average weight and calories for the last N weeks."""
    db = _get_db()
    cutoff = date.today() - timedelta(weeks=weeks)
    rows = db.execute("""
        SELECT
            strftime('%Y-W%W', date) as week,
            ROUND(AVG(w.weight), 1) as avg_weight,
            COUNT(w.weight) as weigh_ins
        FROM weight_log w
        WHERE w.date >= ?
        GROUP BY week
        ORDER BY week DESC
    """, (str(cutoff),)).fetchall()

    food_rows = db.execute("""
        SELECT
            strftime('%Y-W%W', date) as week,
            ROUND(AVG(calories)) as avg_calories,
            ROUND(AVG(protein_g)) as avg_protein
        FROM food_log
        WHERE date >= ?
        GROUP BY week
        ORDER BY week DESC
    """, (str(cutoff),)).fetchall()
    db.close()

    food_map = {r["week"]: dict(r) for r in food_rows}
    results = []
    for r in rows:
        w = dict(r)
        f = food_map.get(w["week"], {})
        w["avg_calories"] = f.get("avg_calories")
        w["avg_protein"] = f.get("avg_protein")
        results.append(w)
    return results


# --- CLI ---

def _cli():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tracker.py weight 181.4")
        print("  python tracker.py food 1780 156")
        print("  python tracker.py history")
        print("  python tracker.py weekly")
        return

    cmd = sys.argv[1].lower()

    if cmd == "weight" and len(sys.argv) >= 3:
        w = float(sys.argv[2])
        log_weight(w)
        print(f"Logged weight: {w} lbs")

    elif cmd == "food" and len(sys.argv) >= 3:
        cals = int(sys.argv[2])
        protein = int(sys.argv[3]) if len(sys.argv) >= 4 else 0
        log_food(cals, protein)
        print(f"Logged food: {cals} cal, {protein}g protein")

    elif cmd == "history":
        print("\n--- Weight History (last 30 days) ---")
        for entry in get_weight_history():
            print(f"  {entry['date']}  {entry['weight']} lbs")
        print("\n--- Food History (last 30 days) ---")
        for entry in get_food_history():
            print(f"  {entry['date']}  {entry['calories']} cal  {entry['protein_g']}g protein")

    elif cmd == "weekly":
        print("\n--- Weekly Averages ---")
        for w in get_weekly_averages():
            cals = f"{w['avg_calories']:.0f} cal" if w.get("avg_calories") else "no data"
            prot = f"{w['avg_protein']:.0f}g" if w.get("avg_protein") else ""
            print(f"  {w['week']}  {w['avg_weight']} lbs ({w['weigh_ins']} weigh-ins)  {cals} {prot}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    _cli()
