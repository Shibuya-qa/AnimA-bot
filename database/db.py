import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Majburiy obuna kanallari
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sub_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                channel_name TEXT NOT NULL,
                channel_link TEXT NOT NULL
            )
        """)
        # Anime post yuboriladigan kanallar
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                channel_name TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS animes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'Tugallangan',
                total_episodes INTEGER DEFAULT 0,
                current_episode INTEGER DEFAULT 0,
                translation TEXT DEFAULT '',
                genres TEXT DEFAULT '',
                thumbnail_file_id TEXT DEFAULT '',
                description TEXT DEFAULT '',
                source_message_id INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Ensure last_active column exists if database was created earlier
        async with db.execute("PRAGMA table_info(users)") as cursor:
            cols = [row[1] for row in await cursor.fetchall()]
            if "last_active" not in cols:
                await db.execute("ALTER TABLE users ADD COLUMN last_active TIMESTAMP")
                await db.execute("UPDATE users SET last_active = created_at WHERE last_active IS NULL")
            
            # Reset last_active to created_at for legacy users migrated with system timestamp
            await db.execute(
                """UPDATE users SET last_active = created_at 
                   WHERE last_active IS NULL 
                      OR (last_active >= datetime('now', '-30 minutes') AND created_at < datetime('now', '-1 hour'))"""
            )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS anime_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anime_id INTEGER NOT NULL,
                episode_number INTEGER NOT NULL,
                file_id TEXT DEFAULT '',
                source_message_id INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(anime_id, episode_number),
                FOREIGN KEY(anime_id) REFERENCES animes(id) ON DELETE CASCADE
            )
        """)
        # Migrate existing source_message_id to anime_episodes as episode 1
        await db.execute("""
            INSERT OR IGNORE INTO anime_episodes (anime_id, episode_number, source_message_id)
            SELECT id, 1, source_message_id FROM animes WHERE source_message_id > 0
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                anime_id INTEGER NOT NULL,
                watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                anime_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, anime_id)
            )
        """)

        # Ensure new columns exist on animes table
        async with db.execute("PRAGMA table_info(animes)") as cursor:
            anime_cols = [row[1] for row in await cursor.fetchall()]
            if "views" not in anime_cols:
                await db.execute("ALTER TABLE animes ADD COLUMN views INTEGER DEFAULT 0")
            if "downloads" not in anime_cols:
                await db.execute("ALTER TABLE animes ADD COLUMN downloads INTEGER DEFAULT 0")
            if "rating" not in anime_cols:
                await db.execute("ALTER TABLE animes ADD COLUMN rating REAL DEFAULT 5.0")
            if "rating_count" not in anime_cols:
                await db.execute("ALTER TABLE animes ADD COLUMN rating_count INTEGER DEFAULT 0")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS anime_ratings (
                user_id INTEGER NOT NULL,
                anime_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, anime_id)
            )
        """)
        await db.commit()


# ─── ANIME ───────────────────────────────────────────────────────────────────

async def get_anime_by_code(code: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM animes WHERE code = ?", (code.strip(),)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_anime_by_id(anime_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM animes WHERE id = ?", (anime_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def add_anime(data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO animes
            (code, name, status, total_episodes, current_episode, translation, genres, thumbnail_file_id, description, source_message_id)
            VALUES
            (:code, :name, :status, :total_episodes, :current_episode, :translation, :genres, :thumbnail_file_id, :description, :source_message_id)
        """, data)
        await db.commit()
        return cursor.lastrowid


async def update_anime(anime_id: int, data: dict):
    fields = ", ".join(f"{k} = :{k}" for k in data)
    data["id"] = anime_id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE animes SET {fields} WHERE id = :id", data)
        await db.commit()


async def set_source_message_id(code: str, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE animes SET source_message_id = ? WHERE code = ?", (message_id, code))
        await db.commit()


async def delete_anime(anime_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM animes WHERE id = ?", (anime_id,))
        await db.commit()


async def list_animes(offset: int = 0, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM animes ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_animes_by_name(name: str) -> list[dict]:
    """Return all anime rows with this exact name (sibling codes like mki1..mki12)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM animes WHERE name = ?", (name,)) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def count_animes() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM animes") as cursor:
            return (await cursor.fetchone())[0]


async def increment_anime_views(anime_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE animes SET views = COALESCE(views, 0) + 1 WHERE id = ?", (anime_id,))
        await db.commit()


async def increment_anime_downloads(anime_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE animes SET downloads = COALESCE(downloads, 0) + 1 WHERE id = ?", (anime_id,))
        await db.commit()


async def search_animes(query: str, limit: int = 20) -> list[dict]:
    query_clean = query.strip()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM animes 
            WHERE code LIKE ? OR name LIKE ? OR genres LIKE ?
            ORDER BY 
                CASE WHEN code = ? THEN 1
                     WHEN code LIKE ? THEN 2
                     WHEN name LIKE ? THEN 3
                     ELSE 4 END,
                COALESCE(views, 0) DESC
            LIMIT ?
        """, (f"{query_clean}%", f"%{query_clean}%", f"%{query_clean}%",
              query_clean, f"{query_clean}%", f"{query_clean}%", limit)) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_top_animes(limit: int = 10) -> list[dict]:
    """
    Return top animes grouped by name so that sibling parts
    (e.g. mki1, mki2 … all named 'Mening kichik iblisim') appear
    as a single entry.  Views and downloads are summed across all parts;
    rating is averaged.  The representative row is the part with the
    smallest id (i.e. part-1 / the original entry).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT
                a.id,
                a.code,
                a.name,
                a.status,
                a.total_episodes,
                a.current_episode,
                a.translation,
                a.genres,
                a.thumbnail_file_id,
                a.description,
                a.source_message_id,
                a.created_at,
                SUM(COALESCE(g.views, 0))     AS views,
                SUM(COALESCE(g.downloads, 0)) AS downloads,
                AVG(COALESCE(g.rating, 5.0))  AS rating,
                SUM(COALESCE(g.rating_count, 0)) AS rating_count
            FROM animes a
            JOIN (
                -- for every name-group pick the row with the minimum id
                SELECT name, MIN(id) AS min_id FROM animes GROUP BY name
            ) rep ON a.id = rep.min_id
            JOIN animes g ON g.name = a.name   -- aggregate siblings
            GROUP BY a.name
            ORDER BY (SUM(COALESCE(g.views, 0)) * 2 + SUM(COALESCE(g.downloads, 0)) * 3) DESC,
                     a.id DESC
            LIMIT ?
        """, (limit,)) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_random_anime() -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM animes ORDER BY RANDOM() LIMIT 1") as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def rate_anime(user_id: int, anime_id: int, score: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO anime_ratings (user_id, anime_id, score) VALUES (?, ?, ?)
            ON CONFLICT(user_id, anime_id) DO UPDATE SET score = excluded.score
        """, (user_id, anime_id, score))
        async with db.execute("SELECT AVG(score) as avg_score, COUNT(score) as cnt FROM anime_ratings WHERE anime_id = ?", (anime_id,)) as cursor:
            r = await cursor.fetchone()
            avg_score = round(r[0], 1) if r and r[0] is not None else float(score)
            cnt = r[1] if r else 1
        await db.execute("UPDATE animes SET rating = ?, rating_count = ? WHERE id = ?", (avg_score, cnt, anime_id))
        await db.commit()
        return {"rating": avg_score, "rating_count": cnt}


async def get_user_rating(user_id: int, anime_id: int) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT score FROM anime_ratings WHERE user_id = ? AND anime_id = ?", (user_id, anime_id)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_all_genres() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT DISTINCT genres FROM animes WHERE genres != ''") as cursor:
            rows = await cursor.fetchall()
            genres_set = set()
            for r in rows:
                for g in r[0].replace("/", ",").split(","):
                    g_clean = g.strip().title()
                    if g_clean:
                        genres_set.add(g_clean)
            return sorted(list(genres_set))


async def get_animes_by_genre(genre: str, offset: int = 0, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM animes 
            WHERE genres LIKE ? 
            ORDER BY COALESCE(views, 0) DESC, id DESC 
            LIMIT ? OFFSET ?
        """, (f"%{genre.strip()}%", limit, offset)) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def count_animes_by_genre(genre: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM animes WHERE genres LIKE ?", (f"%{genre.strip()}%",)) as cursor:
            return (await cursor.fetchone())[0]


# ─── USERS ───────────────────────────────────────────────────────────────────

async def register_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (id, username, full_name, last_active)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(id) DO UPDATE SET
               username=excluded.username,
               full_name=excluded.full_name,
               last_active=CURRENT_TIMESTAMP""",
            (user_id, username, full_name)
        )
        await db.commit()


async def touch_user_activity(user_id: int, username: str = "", full_name: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (id, username, full_name, last_active)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(id) DO UPDATE SET
               last_active=CURRENT_TIMESTAMP,
               username=CASE WHEN excluded.username != '' THEN excluded.username ELSE users.username END,
               full_name=CASE WHEN excluded.full_name != '' THEN excluded.full_name ELSE users.full_name END""",
            (user_id, username, full_name)
        )
        await db.commit()


async def count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            return (await cursor.fetchone())[0]


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


async def get_active_users_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE last_active >= datetime('now', '-1 day')"
        ) as c1:
            u_24h = (await c1.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE last_active >= datetime('now', '-7 days')"
        ) as c2:
            u_7d = (await c2.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE last_active >= datetime('now', '-30 days')"
        ) as c3:
            u_30d = (await c3.fetchone())[0]

        return {"24h": u_24h, "7d": u_7d, "30d": u_30d}


# ─── ANIME EPISODES ──────────────────────────────────────────────────────────

async def add_episode(anime_id: int, episode_number: int, file_id: str = "", source_message_id: int = 0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO anime_episodes (anime_id, episode_number, file_id, source_message_id)
               VALUES (?, ?, ?, ?)""",
            (anime_id, episode_number, file_id, source_message_id)
        )
        # Update current_episode in animes table if needed
        await db.execute(
            """UPDATE animes SET current_episode = MAX(current_episode, ?)
               WHERE id = ?""",
            (episode_number, anime_id)
        )
        await db.commit()


async def get_episodes(anime_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM anime_episodes WHERE anime_id = ? ORDER BY episode_number ASC",
            (anime_id,)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_episode(anime_id: int, episode_number: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM anime_episodes WHERE anime_id = ? AND episode_number = ?",
            (anime_id, episode_number)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def delete_episode(anime_id: int, episode_number: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM anime_episodes WHERE anime_id = ? AND episode_number = ?",
            (anime_id, episode_number)
        )
        await db.commit()


async def add_history(user_id: int, anime_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO user_history (user_id, anime_id) VALUES (?, ?)", (user_id, anime_id))
        await db.commit()


async def get_user_history(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT a.id as anime_id, a.name, a.code, h.watched_at
            FROM user_history h JOIN animes a ON h.anime_id = a.id
            WHERE h.user_id = ? ORDER BY h.watched_at DESC LIMIT 10
        """, (user_id,)) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def add_favorite(user_id: int, anime_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO favorites (user_id, anime_id) VALUES (?, ?)", (user_id, anime_id))
        await db.commit()


async def remove_favorite(user_id: int, anime_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
        await db.commit()


async def get_favorites(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT a.id as anime_id, a.name, a.code FROM favorites f
            JOIN animes a ON f.anime_id = a.id
            WHERE f.user_id = ? ORDER BY f.added_at DESC
        """, (user_id,)) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def is_favorite(user_id: int, anime_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM favorites WHERE user_id=? AND anime_id=?", (user_id, anime_id)) as c:
            return await c.fetchone() is not None


# ─── ADMINS ──────────────────────────────────────────────────────────────────

async def is_admin_in_db(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as c:
            return await c.fetchone() is not None


async def add_admin(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id, username, full_name) VALUES (?,?,?)",
                         (user_id, username, full_name))
        await db.commit()


async def list_admins() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins ORDER BY added_at") as c:
            return [dict(r) for r in await c.fetchall()]


# ─── SUBSCRIPTION CHANNELS ───────────────────────────────────────────────────

async def get_sub_channels() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sub_channels") as c:
            return [dict(r) for r in await c.fetchall()]


async def add_sub_channel(channel_id: str, channel_name: str, channel_link: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO sub_channels (channel_id, channel_name, channel_link) VALUES (?,?,?)",
                         (channel_id, channel_name, channel_link))
        await db.commit()


async def delete_sub_channel(row_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sub_channels WHERE id = ?", (row_id,))
        await db.commit()


# ─── BROADCAST CHANNELS ──────────────────────────────────────────────────────

async def get_broadcast_channels() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM broadcast_channels") as c:
            return [dict(r) for r in await c.fetchall()]


async def add_broadcast_channel(channel_id: str, channel_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO broadcast_channels (channel_id, channel_name) VALUES (?,?)",
                         (channel_id, channel_name))
        await db.commit()


async def delete_broadcast_channel(row_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM broadcast_channels WHERE id = ?", (row_id,))
        await db.commit()
