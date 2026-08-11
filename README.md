# 🎬 Anime Telegram Bot

A Telegram bot for browsing and watching anime by short numeric codes. Users send a
code (or pick from a paginated catalog), and the bot delivers an info card together
with the video, copied straight from a private storage channel. Built with **aiogram 3**
and an async **SQLite** database.

<img width="331" height="392" alt="image" src="https://github.com/user-attachments/assets/b1b934df-1943-4d57-b7c2-96617b9019f2" />


<img width="256" height="237" alt="image" src="https://github.com/user-attachments/assets/c34cd809-3f07-4f0f-bdd7-faa3fffc30da" />


> The bot interface is in **Uzbek**.

---

## ✨ Features

### For users
- **Watch by code** — send an anime's code (e.g. `81`) and get its card + video instantly.
- **Deep links** — `/start <code>` opens straight into an anime (shareable links).
- **Catalog** — browse all anime with pagination (8 per page), completed/ongoing markers.
- **Favorites** — add/remove anime to a personal favorites list.
- **Watch history** — the bot keeps track of what each user has opened.
- **Personal cabinet** — favorites and history in one place.
- **Forced subscription** — users must join the required channel(s) before using the bot
  (enforced by middleware).

### For admins (`/panel`)
- **Password-protected access** — non-admins unlock the panel with a password, then get
  saved as admins in the database.
- **Anime management** — add / edit / delete anime through a step-by-step FSM form
  (code, name, status, episodes, translation, genres, thumbnail, description).
- **Statistics** — total users, anime, admins and broadcast channels.
- **Subscription channels** — manage which channels users must be subscribed to.
- **Broadcast channels** — manage channels and broadcast new anime to them.

---

## 🛠 Tech Stack

| Layer        | Technology |
|--------------|-----------|
| Language     | Python 3.10+ |
| Framework    | [aiogram 3.13](https://docs.aiogram.dev/) (async, router-based) |
| Database     | SQLite via [aiosqlite](https://github.com/omnilib/aiosqlite) (async) |
| State (FSM)  | aiogram `MemoryStorage` |
| Config       | `python-dotenv` |

---

## 🧠 How it works

Videos are **not** stored in the database — only their location. Each anime record keeps
a `source_message_id` pointing at a message in a private **storage channel**
(`SOURCE_CHANNEL_ID`). When a user requests an anime:

1. The bot sends a formatted **info card** (status, episodes, genres, description).
2. It then uses `copy_message` to deliver the video from the storage channel into the
   user's chat — so the original file never has to be re-uploaded.

This keeps the database light and lets a single uploaded video serve unlimited users.

---

## 📁 Project Structure

```
.
├── bot.py                  # Entry point: sets up Dispatcher, middlewares, routers
├── config.py               # Loads env vars (token, admin ids, source channel)
├── database/
│   └── db.py               # Async SQLite: users, anime, favorites, history, channels
├── handlers/
│   ├── start.py            # /start, deep links, welcome
│   ├── anime.py            # Code lookup, catalog, delivery, favorites
│   ├── cabinet.py          # User cabinet (favorites, history)
│   ├── admin.py            # Admin panel: CRUD, stats, channels (FSM)
│   ├── subscription.py     # Forced-subscription flow
│   └── channel.py          # Auto-detect uploads in the storage channel
├── keyboards/
│   └── main.py             # Inline & reply keyboards
├── middlewares/
│   ├── subscription.py     # Blocks users who aren't subscribed
│   └── chat_type.py        # Restricts the bot to private chats
└── utils/
    └── broadcaster.py      # Broadcasting anime to channels
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A private channel to store videos (the bot must be an admin there)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/bek-vap/animebot.git
cd animebot

# 2. (recommended) create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env            # then fill in the values

# 5. Run the bot
python bot.py
```

### Environment variables (`.env`)

| Variable            | Description |
|---------------------|-------------|
| `BOT_TOKEN`         | Bot token from @BotFather |
| `ADMIN_IDS`         | Comma-separated Telegram user IDs with admin access |
| `ADMIN_PASSWORD`    | Password to unlock the admin panel |
| `SOURCE_CHANNEL_ID` | ID of the private channel where videos are stored (e.g. `-1001234567890`) |

The SQLite database (`anime_bot.db`) is created automatically on first run.

---

## 📝 Notes

- Built as a hands-on project to practice async Python, the aiogram 3 router/middleware
  model, FSM-based forms and relational data modelling.
- Secrets are kept out of version control via `.gitignore`; see `.env.example` for the
  expected format.
