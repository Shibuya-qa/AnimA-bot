"""
Helper script: syncs all animes from anime_bot.db to webapp/data/animes.json
"""

import os
import json
import sqlite3
from config import DB_PATH

def sync_animes():
    data_dir = os.path.join(os.path.dirname(__file__), "webapp", "data")
    os.makedirs(data_dir, exist_ok=True)
    out_file = os.path.join(data_dir, "animes.json")

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM animes ORDER BY id DESC")
    rows = cur.fetchall()

    animes = []
    for r in rows:
        d = dict(r)
        d["episodes"] = d.get("total_episodes") or d.get("current_episode") or 12
        d["rating"] = round(float(d.get("rating") or 5.0), 1)
        d["views"] = int(d.get("views") or 0)
        d["type"] = "film" if (d.get("total_episodes") == 1 or "film" in (d.get("genres") or "").lower()) else "serial"
        d["is_vip"] = False
        d["poster"] = "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=700&auto=format&fit=crop&q=85"
        animes.append(d)

    con.close()

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(animes, f, ensure_ascii=False, indent=2)

    print(f"[OK] Exported {len(animes)} animes to {out_file}")

if __name__ == "__main__":
    sync_animes()
