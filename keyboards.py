from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from typing import List, Dict, Any


def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Foydalanuvchi uchun asosiy menyu tugmalari."""
    keyboard = [
        [
            KeyboardButton(text="🔍 Kod orqali qidirish"),
            KeyboardButton(text="🎲 Tasodifiy anime")
        ],
        [
            KeyboardButton(text="⭐ Sevimlilarim"),
            KeyboardButton(text="🔥 TOP 10 Animelar")
        ],
        [
            KeyboardButton(text="🎭 Janrlar"),
            KeyboardButton(text="📋 So'nggi animelar")
        ],
        [
            KeyboardButton(text="ℹ️ Bot haqida")
        ]
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="👑 Admin Panel")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True
    )


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Admin panel menyusi."""
    keyboard = [
        [
            KeyboardButton(text="➕ Anime qo'shish"),
            KeyboardButton(text="📢 Kanalga uzatish")
        ],
        [
            KeyboardButton(text="📋 Animelar ro'yxati"),
            KeyboardButton(text="📊 Statistika")
        ],
        [
            KeyboardButton(text="📢 Kanallarni boshqarish"),
            KeyboardButton(text="🗑 Animeni o'chirish")
        ],
        [
            KeyboardButton(text="📢 Xabar tarqatish"),
            KeyboardButton(text="🔙 Asosiy menyu")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True
    )



def choose_anime_to_add_keyboard(animes: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Anime qo'shishda: Yangi qo'shish yoki mavjud animelardan tanlash."""
    buttons = [
        [
            InlineKeyboardButton(text="🆕 Yangi anime yaratish", callback_data="create_new_anime")
        ]
    ]

    if animes:
        for a in animes:
            title = a.get("title", "Nomsiz")
            code = a.get("code", "")
            eps = a.get("episodes_count", 0)
            buttons.append([
                InlineKeyboardButton(
                    text=f"🎬 {title} ({eps} qism) [Kod: {code}]",
                    callback_data=f"select_anime_ep_{a['id']}"
                )
            ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def code_exists_action_keyboard(anime_id: int, next_ep: int) -> InlineKeyboardMarkup:
    """Kod allaqachon mavjud bo'lganda tezkor keyingi qism yuklash tugmasi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"➕ Ha, {next_ep}-qismni yuklash", callback_data=f"quick_add_ep_{anime_id}_{next_ep}")
            ],
            [
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_code_input")
            ]
        ]
    )



def subscription_keyboard(channel_url: str, anime_code: str = "") -> InlineKeyboardMarkup:
    """Majburiy obuna tugmalari."""
    callback_data = f"checksub_{anime_code}" if anime_code else "checksub_main"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=channel_url)
            ],
            [
                InlineKeyboardButton(text="✅ A'zo bo'ldim / Tekshirish", callback_data=callback_data)
            ]
        ]
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Bekor qilish tugmasi."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def skip_or_cancel_keyboard() -> ReplyKeyboardMarkup:
    """O'tkazib yuborish yoki bekor qilish tugmasi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ O'tkazib yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def episodes_inline_keyboard(
    anime_id: int,
    episodes: List[Dict[str, Any]],
    current_ep: int = 1,
    page: int = 0,
    per_page: int = 15
) -> InlineKeyboardMarkup:
    """
    Rasmda ko'rsatilgandek qismlar inline klaviaturasi:
    [💽] - 1 | 2 | 3
    4        | 5 | 6
    """
    if not episodes:
        return InlineKeyboardMarkup(inline_keyboard=[])

    # Saralangan qismlar ro'yxati
    sorted_eps = sorted(episodes, key=lambda x: x["episode_num"])
    total_eps = len(sorted_eps)
    total_pages = (total_eps + per_page - 1) // per_page

    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0

    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_page_eps = sorted_eps[start_idx:end_idx]

    rows = []
    current_row = []

    for ep in current_page_eps:
        ep_num = ep["episode_num"]
        if ep_num == current_ep:
            btn_text = f"[💽] - {ep_num}"
        else:
            btn_text = str(ep_num)

        current_row.append(
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"ep_{anime_id}_{ep_num}_{page}"
            )
        )

        # 3 tadan joylashtirish (skrinshotdagidek)
        if len(current_row) == 3:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    # Agar 15 tadan ko'p qism bo'lsa sahifalash
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"eppage_{anime_id}_{current_ep}_{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"eppage_{anime_id}_{current_ep}_{page + 1}"))
        rows.append(nav)

    # Qo'shimcha tugmalar (Sevimlilar, Bildirishnoma, Reyting)
    fav_text = "⭐ Sevimlilar"
    sub_text = "🔔 Bildirishnoma"

    rows.append([
        InlineKeyboardButton(text=fav_text, callback_data=f"fav_{anime_id}"),
        InlineKeyboardButton(text=sub_text, callback_data=f"sub_{anime_id}")
    ])
    rows.append([
        InlineKeyboardButton(text="⭐ 1", callback_data=f"rate_{anime_id}_1"),
        InlineKeyboardButton(text="⭐ 2", callback_data=f"rate_{anime_id}_2"),
        InlineKeyboardButton(text="⭐ 3", callback_data=f"rate_{anime_id}_3"),
        InlineKeyboardButton(text="⭐ 4", callback_data=f"rate_{anime_id}_4"),
        InlineKeyboardButton(text="⭐ 5", callback_data=f"rate_{anime_id}_5")
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def anime_list_keyboard(animes: List[Dict[str, Any]], page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    """Admin uchun animelar ro'yxatini sahifalab ko'rsatish."""
    buttons = []
    for a in animes:
        title = a.get("title", "Nomsiz")
        code = a.get("code", "")
        eps_count = a.get("episodes_count", 0)
        buttons.append([
            InlineKeyboardButton(
                text=f"🎬 {title} ({eps_count} qism) [Kod: {code}]",
                callback_data=f"view_anime_{a['id']}"
            )
        ])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"anime_page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"anime_page_{page + 1}"))

    if nav_row:
        buttons.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def anime_admin_details_keyboard(anime_id: int, anime_code: str) -> InlineKeyboardMarkup:
    """Admin uchun animeni boshqarish tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Yangi qism qo'shish", callback_data=f"admin_addep_{anime_id}")
            ],
            [
                InlineKeyboardButton(text="🗑 Butun animeni o'chirish", callback_data=f"admin_del_{anime_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="back_to_anime_list")
            ]
        ]
    )


def confirm_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Xabar tarqatishni tasdiqlash."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 Hammaga yuborish", callback_data="confirm_broadcast"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_broadcast")
            ]
        ]
    )


def channel_post_animes_keyboard(animes: List[Dict[str, Any]], page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    """Kanalga uzatish uchun animelar ro'yxati."""
    buttons = []
    for a in animes:
        title = a.get("title", "Nomsiz")
        code = a.get("code", "")
        eps = a.get("episodes_count", 0)
        buttons.append([
            InlineKeyboardButton(
                text=f"🎬 {title} ({eps} qism) [Kod: {code}]",
                callback_data=f"sendtochan_{a['id']}"
            )
        ])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"chanpage_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"chanpage_{page + 1}"))

    if nav_row:
        buttons.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_channel_post_keyboard(anime_id: int) -> InlineKeyboardMarkup:
    """Kanalga joylash usullari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📹 1-qism videosi bilan kanalga joylash", callback_data=f"do_post_vid_{anime_id}")
            ],
            [
                InlineKeyboardButton(text="📝 Faqat e'lon (Matn + Tugma) sifatida joylash", callback_data=f"do_post_text_{anime_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 Boshqa anime tanlash", callback_data="back_to_post_list")
            ]
        ]
    )


def channel_watch_button(bot_username: str, anime_code: str = "") -> InlineKeyboardMarkup:
    """Kanalga tashlangan post ostidagi tugma."""
    url = f"https://t.me/{bot_username}?start={anime_code}" if anime_code else f"https://t.me/{bot_username}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🍿 Botga o'tish / Tomosha qilish",
                    url=url
                )
            ]
        ]
    )


def anime_actions_keyboard(
    anime_id: int,
    is_fav: bool = False,
    is_sub: bool = False,
    avg_rating: float = 0.0,
    votes_count: int = 0
) -> InlineKeyboardMarkup:
    """Anime tafsilotlari ostidagi qo'shimcha tugmalar (Sevimlilar, Bildirishnoma, Reyting, Ulashish)."""
    fav_text = "❌ Sevimlilardan o'chirish" if is_fav else "⭐ Sevimlilarga qo'shish"
    sub_text = "🔕 Bildirishnomani o'chirish" if is_sub else "🔔 Yangi qism bildirishnomasi"

    buttons = [
        [
            InlineKeyboardButton(text=fav_text, callback_data=f"fav_{anime_id}")
        ],
        [
            InlineKeyboardButton(text=sub_text, callback_data=f"sub_{anime_id}")
        ],
        [
            InlineKeyboardButton(text="⭐ 1", callback_data=f"rate_{anime_id}_1"),
            InlineKeyboardButton(text="⭐ 2", callback_data=f"rate_{anime_id}_2"),
            InlineKeyboardButton(text="⭐ 3", callback_data=f"rate_{anime_id}_3"),
            InlineKeyboardButton(text="⭐ 4", callback_data=f"rate_{anime_id}_4"),
            InlineKeyboardButton(text="⭐ 5", callback_data=f"rate_{anime_id}_5")
        ],
        [
            InlineKeyboardButton(text="📤 Do'stlarga ulashish", switch_inline_query=str(anime_id))
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def must_subscribe_keyboard(channels: List[Dict[str, Any]], anime_code: str = "") -> InlineKeyboardMarkup:
    """Dinmik majburiy kanallar klaviaturasi."""
    buttons = []
    for c in channels:
        buttons.append([
            InlineKeyboardButton(text=f"📢 {c['channel_name']}", url=c['channel_link'])
        ])
    
    cb_data = f"checksub_{anime_code}" if anime_code else "checksub_main"
    buttons.append([
        InlineKeyboardButton(text="🔄 Obunani tekshirish", callback_data=cb_data)
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def genres_keyboard() -> InlineKeyboardMarkup:
    """Janrlar ro'yxati inline klaviaturasi."""
    genres = [
        "Jangovar", "Fantastika", "Romantika", "Komediya",
        "Sarguzasht", "Dramatika", "Sport", "Sehr-jodu", "Maktab", "Triller"
    ]
    rows = []
    current_row = []
    for g in genres:
        current_row.append(InlineKeyboardButton(text=f"🎭 {g}", callback_data=f"genre_{g}"))
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def channels_admin_keyboard(channels: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Admin uchun kanallarni boshqarish klaviaturasi."""
    buttons = [
        [
            InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="admin_add_channel")
        ]
    ]
    for c in channels:
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {c['channel_name']} (O'chirish)",
                callback_data=f"admin_del_chan_{c['id']}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



