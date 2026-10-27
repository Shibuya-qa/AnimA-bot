"""
ShoDa Anime — Telegram Mini App Backend API Server
Built with aiohttp.web & aiosqlite, connecting directly to anime_bot.db
"""

import os
import json
import asyncio
import aiosqlite
from aiohttp import web
from config import DB_PATH

WEBAPP_DIR = os.path.join(os.path.dirname(__file__), "webapp")

# Ensure required extra tables exist for the mini app
async def init_extra_tables():
    async with aiosqlite.connect(DB_PATH) as db:
        # Chat messages table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mini_app_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                message TEXT NOT NULL,
                reply_to TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # User extra data (points, balance, is_vip)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mini_app_user_meta (
                user_id INTEGER PRIMARY KEY,
                points INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

# --- CORS MIDDLEWARE ---
@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

# --- API ENDPOINTS ---

async def get_animes(request):
    """Return animes list with optional search and filters"""
    query = request.query.get("q", "").strip()
    genre = request.query.get("genre", "").strip()
    limit = int(request.query.get("limit", 100))

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = "SELECT * FROM animes WHERE 1=1"
        params = []

        if query:
            sql += " AND (name LIKE ? OR code LIKE ? OR genres LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
        if genre and genre != "all":
            sql += " AND genres LIKE ?"
            params.append(f"%{genre}%")

        sql += " ORDER BY COALESCE(views, 0) DESC, id DESC LIMIT ?"
        params.append(limit)

        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            animes = []
            for r in rows:
                d = dict(r)
                # Map fields to match mini app expectations
                d["episodes"] = d.get("total_episodes") or d.get("current_episode") or 12
                d["rating"] = round(float(d.get("rating") or 5.0), 1)
                d["views"] = int(d.get("views") or 0)
                d["type"] = "film" if (d.get("total_episodes") == 1 or "film" in (d.get("genres") or "").lower()) else "serial"
                d["is_vip"] = False
                d["poster"] = "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&auto=format&fit=crop&q=80"
                animes.append(d)

            return web.json_response(animes)

async def get_anime_by_id(request):
    """Return single anime with episodes"""
    anime_id = int(request.match_info["id"])
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM animes WHERE id = ?", (anime_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return web.json_response({"error": "Anime not found"}, status=404)
            data = dict(row)

        async with db.execute("SELECT episode_number FROM anime_episodes WHERE anime_id = ? ORDER BY episode_number ASC", (anime_id,)) as ep_cur:
            episodes = [r[0] for r in await ep_cur.fetchall()]
            data["episodes_list"] = episodes or list(range(1, (data.get("total_episodes") or 12) + 1))

        return web.json_response(data)

async def get_chat_messages(request):
    """Get recent chat messages"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mini_app_chat ORDER BY id DESC LIMIT 50") as cursor:
            rows = await cursor.fetchall()
            messages = [dict(r) for r in reversed(rows)]
            return web.json_response(messages)

async def post_chat_message(request):
    """Save new chat message"""
    try:
        body = await request.json()
        user_id = body.get("user_id", 0)
        user_name = body.get("user_name", "Anonim")
        message = body.get("message", "").strip()
        reply_to = body.get("reply_to", "")

        if not message:
            return web.json_response({"error": "Message cannot be empty"}, status=400)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO mini_app_chat (user_id, user_name, message, reply_to)
                VALUES (?, ?, ?, ?)
            """, (user_id, user_name, message, reply_to))
            await db.commit()

        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def get_stats(request):
    """Return statistics for the app"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM animes") as c1:
            total_animes = (await c1.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users") as c2:
            total_users = (await c2.fetchone())[0]

        return web.json_response({
            "total_animes": total_animes,
            "total_users": total_users,
            "online_users": 1
        })

# --- USER PROFILE & BOT DATA SYNCHRONIZATION ---

async def get_user_profile(request):
    """Fetch user profile, favorites and history synced with bot database"""
    user_id = int(request.match_info["user_id"])
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # User basic info
        async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as u_cur:
            user_row = await u_cur.fetchone()
            user_data = dict(user_row) if user_row else {"id": user_id, "full_name": "Foydalanuvchi"}

        # Check admin
        from config import ADMIN_IDS
        is_admin = (user_id in ADMIN_IDS)
        if not is_admin:
            async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as a_cur:
                is_admin = bool(await a_cur.fetchone())
        user_data["is_admin"] = is_admin

        # User points & VIP status
        async with db.execute("SELECT points, is_vip FROM mini_app_user_meta WHERE user_id = ?", (user_id,)) as m_cur:
            meta = await m_cur.fetchone()
            user_data["points"] = meta[0] if meta else (999 if is_admin else 0)
            user_data["is_vip"] = bool(meta[1]) if meta else is_admin

        # Favorites (synced with Bot's favorites table)
        async with db.execute("SELECT anime_id FROM favorites WHERE user_id = ?", (user_id,)) as f_cur:
            user_data["favorites"] = [row[0] for row in await f_cur.fetchall()]

        # Watch history (synced with Bot's user_history table)
        async with db.execute("""
            SELECT a.id, a.name, a.code, a.genres, a.views, a.rating, h.watched_at
            FROM user_history h
            JOIN animes a ON a.id = h.anime_id
            WHERE h.user_id = ?
            ORDER BY h.id DESC LIMIT 10
        """, (user_id,)) as h_cur:
            user_data["history"] = [dict(r) for r in await h_cur.fetchall()]

        return web.json_response(user_data)

async def toggle_favorite(request):
    """Sync favorites between Web App and Telegram Bot database"""
    user_id = int(request.match_info["user_id"])
    body = await request.json()
    anime_id = int(body.get("anime_id", 0))

    if not anime_id:
        return web.json_response({"error": "anime_id required"}, status=400)

    async with aiosqlite.connect(DB_PATH) as db:
        # Check if exists
        async with db.execute("SELECT 1 FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id)) as cur:
            exists = bool(await cur.fetchone())

        if exists:
            await db.execute("DELETE FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
            is_fav = False
        else:
            await db.execute("INSERT OR IGNORE INTO favorites (user_id, anime_id) VALUES (?, ?)", (user_id, anime_id))
            is_fav = True
        await db.commit()

        # Return updated list
        async with db.execute("SELECT anime_id FROM favorites WHERE user_id = ?", (user_id,)) as f_cur:
            favs = [row[0] for row in await f_cur.fetchall()]

        return web.json_response({"is_favorite": is_fav, "favorites": favs})

async def add_history(request):
    """Sync watch history and view counts between Web App and Bot"""
    user_id = int(request.match_info["user_id"])
    body = await request.json()
    anime_id = int(body.get("anime_id", 0))

    if not anime_id:
        return web.json_response({"error": "anime_id required"}, status=400)

    async with aiosqlite.connect(DB_PATH) as db:
        # Insert watch history
        await db.execute("INSERT INTO user_history (user_id, anime_id) VALUES (?, ?)", (user_id, anime_id))
        # Increment anime view counter in bot database
        await db.execute("UPDATE animes SET views = COALESCE(views, 0) + 1 WHERE id = ?", (anime_id,))
        await db.commit()

        return web.json_response({"status": "ok"})

# --- APPLICATION FACTORY ---
def create_app():
    app = web.Application(middlewares=[cors_middleware])
    
    # API Routes
    app.router.add_get("/api/animes", get_animes)
    app.router.add_get("/api/animes/{id}", get_anime_by_id)
    app.router.add_get("/api/chat", get_chat_messages)
    app.router.add_post("/api/chat", post_chat_message)
    app.router.add_get("/api/stats", get_stats)

    # Synced User API
    app.router.add_get("/api/user/{user_id}", get_user_profile)
    app.router.add_post("/api/user/{user_id}/favorites", toggle_favorite)
    app.router.add_post("/api/user/{user_id}/history", add_history)

    # Static WebApp UI
    if os.path.exists(WEBAPP_DIR):
        app.router.add_static("/", WEBAPP_DIR, show_index=True)

    return app

async def run_server(host="0.0.0.0", port=8080):
    await init_extra_tables()
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"[OK] ShoDa Mini App Server ishga tushdi: http://localhost:{port}")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_server())
