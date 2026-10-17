from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🔍 Qidirish"),
        KeyboardButton(text="🔥 Top Animelar"),
    )
    builder.row(
        KeyboardButton(text="🎲 Random Anime"),
        KeyboardButton(text="🗂 Kabinet"),
    )
    if is_admin:
        builder.row(KeyboardButton(text="👑 Admin Panel"))
    return builder.as_markup(resize_keyboard=True)


def search_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Barcha katalog", callback_data="catalog:0"),
        InlineKeyboardButton(text="🎭 Janrlar", callback_data="genres:list"),
    )
    builder.row(
        InlineKeyboardButton(text="🔥 Top 10 Animelar", callback_data="top_animes"),
        InlineKeyboardButton(text="🎲 Tasodifiy anime", callback_data="random_anime"),
    )
    builder.row(
        InlineKeyboardButton(text="🔎 Tezkor Inline qidiruv", switch_inline_query_current_chat=""),
    )
    return builder.as_markup()


def genres_keyboard(genres: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    row = []
    for g in genres:
        row.append(InlineKeyboardButton(text=f"🎭 {g}", callback_data=f"genre:{g}:0"))
        if len(row) == 2:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="🔙 Qidiruv menyusi", callback_data="search:menu"))
    return builder.as_markup()


def search_results_keyboard(animes: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for anime in animes:
        status_icon = "🟢" if anime.get("status") == "Tugallangan" else "🔄"
        rating = anime.get("rating", 5.0) or 5.0
        views = anime.get("views", 0) or 0
        builder.row(InlineKeyboardButton(
            text=f"{status_icon} {anime['name']} [{anime['code']}] • ⭐{rating:.1f}",
            callback_data=f"catalog:view:{anime['id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Qidiruvga qaytish", callback_data="search:menu"))
    return builder.as_markup()


def top_animes_keyboard(animes: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, anime in enumerate(animes):
        medal = medals[i] if i < len(medals) else "🎬"
        views = anime.get("views", 0) or 0
        rating = anime.get("rating", 5.0) or 5.0
        builder.row(InlineKeyboardButton(
            text=f"{medal} {anime['name']} • 👁 {views:,} • ⭐{rating:.1f}",
            callback_data=f"catalog:view:{anime['id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Qidiruv menyusi", callback_data="search:menu"))
    return builder.as_markup()


def catalog_keyboard(animes: list, offset: int, total: int, genre: str = "") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for anime in animes:
        status_icon = "🟢" if anime.get("status") == "Tugallangan" else "🔄"
        rating = anime.get("rating", 5.0) or 5.0
        builder.row(InlineKeyboardButton(
            text=f"{status_icon} {anime['name']} [{anime['code']}] • ⭐{rating:.1f}",
            callback_data=f"catalog:view:{anime['id']}"
        ))
    nav = []
    page = offset // 8 + 1
    total_pages = (total + 7) // 8
    cb_prefix = f"genre:{genre}" if genre else "catalog"
    if offset > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"{cb_prefix}:{offset - 8}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if offset + 8 < total:
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"{cb_prefix}:{offset + 8}"))
    if nav:
        builder.row(*nav)
    if genre:
        builder.row(InlineKeyboardButton(text="🎭 Barcha janrlar", callback_data="genres:list"))
    else:
        builder.row(InlineKeyboardButton(text="🔙 Qidiruv menyusi", callback_data="search:menu"))
    return builder.as_markup()


def anime_actions(
    anime_id: int,
    is_fav: bool,
    active_ep: int = 1,
    available_episodes: list[int] = None,
    total_episodes: int = 1,
    page: int = 0,
    anime_code: str = "",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Determine episode numbers to show
    if available_episodes:
        all_eps = available_episodes
    else:
        max_ep = max(total_episodes, active_ep, 1)
        all_eps = list(range(1, max_ep + 1))

    # Paginate episodes (9 episodes per page)
    EPS_PER_PAGE = 9
    total_pages = (len(all_eps) + EPS_PER_PAGE - 1) // EPS_PER_PAGE
    page = max(0, min(page, total_pages - 1)) if total_pages > 0 else 0

    page_eps = all_eps[page * EPS_PER_PAGE : (page + 1) * EPS_PER_PAGE]

    # Create 3-item rows for episode buttons
    row = []
    for ep in page_eps:
        if ep == active_ep:
            btn_text = f"✨ [{ep}] ✨"
        else:
            btn_text = f"▶️ {ep}"
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"ep:{anime_id}:{ep}:{page}"))
        if len(row) == 3:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)

    # Navigation row if pagination needed
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"ep_page:{anime_id}:{active_ep}:{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"ep_page:{anime_id}:{active_ep}:{page + 1}"))
    if nav:
        builder.row(*nav)

    # --- Action buttons ---
    # Button 1: next episode (if available)
    next_ep = next((ep for ep in all_eps if ep > active_ep), None)
    if next_ep is not None:
        builder.row(
            InlineKeyboardButton(text=f"⏭ {next_ep}-qism (keyingi)", callback_data=f"download_ep:{anime_id}:{next_ep}"),
        )

    # Button 2: all episodes
    if len(all_eps) > 1:
        builder.row(
            InlineKeyboardButton(text=f"📦 Barcha qismlarni olish ({len(all_eps)} ta)", callback_data=f"download_all:{anime_id}"),
        )

    fav_text = "❤️ Sevimlilardan o'chirish" if is_fav else "🤍 Sevimlilarga qo'shish"
    builder.row(
        InlineKeyboardButton(text=fav_text, callback_data=f"fav:{anime_id}:{active_ep}:{page}"),
        InlineKeyboardButton(text="⭐ Baholash", callback_data=f"rate_menu:{anime_id}:{active_ep}:{page}"),
    )
    if anime_code:
        builder.row(
            InlineKeyboardButton(text="🚀 Do'stlarga ulashish", switch_inline_query=f"{anime_code}"),
        )

    return builder.as_markup()


def rating_keyboard(anime_id: int, active_ep: int = 1, page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    row = [
        InlineKeyboardButton(text=f"⭐ {i}", callback_data=f"do_rate:{anime_id}:{i}:{active_ep}:{page}")
        for i in range(1, 6)
    ]
    builder.row(*row)
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"ep_page:{anime_id}:{active_ep}:{page}"))
    return builder.as_markup()


def cabinet_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📜 Ko'rish tarixi", callback_data="cabinet:history"),
        InlineKeyboardButton(text="❤️ Sevimlilar", callback_data="cabinet:favorites"),
    )
    builder.row(
        InlineKeyboardButton(text="📖 Qo'llanma", callback_data="cabinet:guide"),
        InlineKeyboardButton(text="📢 Reklama berish", callback_data="cabinet:reklama"),
    )
    builder.row(InlineKeyboardButton(text="🔙 Menyuga qaytish", callback_data="cabinet:back"))
    return builder.as_markup()


# ─── ADMIN ───────────────────────────────────────────────────────────────────

def admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Anime qo'shish", callback_data="admin:add"))
    builder.row(InlineKeyboardButton(text="🎬 Qism qo'shish", callback_data="admin:addep_select"))
    builder.row(InlineKeyboardButton(text="📋 Animeler ro'yxati", callback_data="admin:list:0"))
    builder.row(
        InlineKeyboardButton(text="📢 Obuna kanallar", callback_data="admin:subchannels"),
        InlineKeyboardButton(text="📣 Broadcast kanallar", callback_data="admin:bchannels"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats"),
        InlineKeyboardButton(text="📦 Zaxira (Backup)", callback_data="admin:backup"),
    )
    builder.row(
        InlineKeyboardButton(text="📥 Kanaldan import qilish", callback_data="admin:import_help"),
    )
    return builder.as_markup()


def sub_channels_menu(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.row(InlineKeyboardButton(
            text=f"🗑 {ch['channel_name']}",
            callback_data=f"admin:delsubch:{ch['id']}"
        ))
    builder.row(InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="admin:addsubch"))
    builder.row(InlineKeyboardButton(text="🔙 Panel", callback_data="admin:back"))
    return builder.as_markup()


def broadcast_channels_menu(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.row(InlineKeyboardButton(
            text=f"🗑 {ch['channel_name']}",
            callback_data=f"admin:delbch:{ch['id']}"
        ))
    builder.row(InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="admin:addbch"))
    builder.row(InlineKeyboardButton(text="🔙 Panel", callback_data="admin:back"))
    return builder.as_markup()


def admin_anime_list(animes: list, offset: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for anime in animes:
        builder.row(InlineKeyboardButton(
            text=f"🎬 {anime['name']} [{anime['code']}]",
            callback_data=f"admin:anime:{anime['id']}"
        ))
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin:list:{offset - 10}"))
    if offset + 10 < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin:list:{offset + 10}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="🔙 Panel", callback_data="admin:back"))
    return builder.as_markup()


def admin_anime_detail(anime_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎬 Yangi qism qo'shish", callback_data=f"admin:addep:{anime_id}"))
    builder.row(InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"admin:edit:{anime_id}"))
    builder.row(InlineKeyboardButton(text="📣 Qayta broadcast", callback_data=f"admin:rebroadcast:{anime_id}"))
    builder.row(InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin:delete:{anime_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Ro'yxat", callback_data="admin:list:0"))
    return builder.as_markup()


def admin_edit_fields(anime_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    fields = [
        ("🔑 Kod", "code"), ("📝 Nom", "name"), ("📊 Status", "status"),
        ("🎬 Jami qism", "total_episodes"), ("📺 Joriy qism", "current_episode"),
        ("🌐 Tarjima", "translation"), ("🎭 Janrlar", "genres"),
        ("🖼 Muqova", "thumbnail_file_id"), ("📄 Tavsif", "description"),
    ]
    for label, field in fields:
        builder.row(InlineKeyboardButton(text=label, callback_data=f"admin:editfield:{anime_id}:{field}"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin:anime:{anime_id}"))
    return builder.as_markup()


def confirm_delete(anime_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"admin:confirmdelete:{anime_id}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data=f"admin:anime:{anime_id}"),
    )
    return builder.as_markup()
