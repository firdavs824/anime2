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
                InlineKeyboardButton(

