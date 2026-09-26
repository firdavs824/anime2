from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputMediaVideo, InputMediaDocument, InputMediaAnimation
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import SearchAnimeStates, AdminLoginStates
from config import ADMIN_SECRET_KEY, ADMIN_SECRET_KEYS

router = Router()
# Bot faqat shaxsiy yozishmada (lichkada) javob bersin, guruhlarda gapirmasin!
router.message.filter(F.chat.type == "private")



# ================== MAJBURIY OBUNA TEKSHIRUVI ==================

async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """Foydalanuvchi barcha majburiy kanallarga a'zo bo'lganligini tekshirish."""
    if await db.is_user_admin(user_id):
        return True

    channels = await db.get_all_channels()
    if not channels:
        # Agarda dinamik kanallar yo'q bo'lsa, eskisini tekshiramiz
        old_chan_id = await db.get_setting("channel_id")
        if not old_chan_id:
            return True
        channels = [{"channel_id": old_chan_id, "channel_name": "Kanalimiz", "channel_link": await db.get_setting("channel_link", "https://t.me/+pW5zQXdYETs1Y2Uy")}]

    for c in channels:
        try:
            chan_id_str = c["channel_id"]
            chat_id = int(chan_id_str) if chan_id_str.lstrip("-").isdigit() else chan_id_str
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status not in ["creator", "administrator", "member", "restricted"]:
                return False
        except Exception:
            # Agar bot kanalga admin qilinmagan bo'lsa tekshiruvdan o'tkaziladi
            continue

    return True


async def prompt_subscription(message: Message, anime_code: str = ""):
    """Obuna bo'lish talabi xabari."""
    channels = await db.get_all_channels()
    if not channels:
        link = await db.get_setting("channel_link", "https://t.me/+pW5zQXdYETs1Y2Uy")
        channels = [{"channel_name": "Kanalimiz", "channel_link": link}]

    text = (
        "⚠️ <b>Animeni tomosha qilish uchun avval quyidagi kanallarimizga a'zo bo'ling!</b>\n\n"
        "Kanallarga obuna bo'lib, so'ng <b>'🔄 Obunani tekshirish'</b> tugmasini bosing:"
    )
    await message.answer(
        text,
        reply_markup=kb.must_subscribe_keyboard(channels, anime_code=anime_code),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("checksub_"))
async def check_subscription_callback(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_", 1)
    anime_code = parts[1] if len(parts) > 1 else ""

    is_sub = await check_user_subscription(bot, callback.from_user.id)
    if is_sub:
        await callback.answer("✅ Rahmat! Obuna tasdiqlandi.")
        try:
            await callback.message.delete()
        except Exception:
            pass

        if anime_code and anime_code != "main":
            anime = await db.get_anime_by_code(anime_code)
            if anime:
                await send_anime_to_user(bot, callback.message.chat.id, anime)
                return

        is_admin = await db.is_user_admin(callback.from_user.id)
        await callback.message.answer(
            "🎉 <b>Obuna tasdiqlandi! Anime botga xush kelibsiz.</b>\n\n"
            "Endi sevimli animelaringiz kodini yozib bemalol tomosha qilishingiz mumkin.",
            reply_markup=kb.main_menu_keyboard(is_admin),
            parse_mode="HTML"
        )
    else:
        await callback.answer(
            "❌ Siz hali kanalga obuna bo'lmadingiz! Iltimos, havola orqali kanalga a'zo bo'ling.",
            show_alert=True
        )


# ================== ANIME YUBORISH ==================

async def send_anime_to_user(bot: Bot, chat_id: int, anime: dict, episode_num: int = 1, page: int = 0):
    """
    Anime qismini skrinshotdagi formatda yuborish:
    Caption:
    Anime nomi

    1-qism

    Inline tugmalar:
    [💽] - 1 | 2 | 3
    """
    anime_id = anime["id"]
    episodes = await db.get_anime_episodes(anime_id)

    if not episodes:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🎬 <b>{anime['title']}</b>\n\n⚠️ Ushbu anime uchun hali qismlar yuklanmagan.",
            parse_mode="HTML"
        )
        return

    # Kerakli qismni topish (agar topilmasa, mavjud birinchi qism)
    target_ep = next((e for e in episodes if e["episode_num"] == episode_num), episodes[0])
    actual_ep_num = target_ep["episode_num"]

    caption = f"{anime['title']}\n\n{actual_ep_num}-qism"
    markup = kb.episodes_inline_keyboard(
        anime_id=anime_id,
        episodes=episodes,
        current_ep=actual_ep_num,
        page=page
    )

    file_id = target_ep["file_id"]
    file_type = target_ep.get("file_type", "video")

    try:
        if file_type == "video":
            await bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=caption,
                reply_markup=markup
            )
        elif file_type == "document":
            await bot.send_document(
                chat_id=chat_id,
                document=file_id,
                caption=caption,
                reply_markup=markup
            )
        elif file_type == "animation":
            await bot.send_animation(
                chat_id=chat_id,
                animation=file_id,
                caption=caption,
                reply_markup=markup
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=markup
            )
    except Exception as e:
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ Faylni yuborishda xatolik: {e}"
        )


# ================== QISMLARNI O'ZGARTIRISH (INLINE CALLBACK) ==================

@router.callback_query(F.data.startswith("ep_"))
async def switch_episode_callback(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    anime_id = int(parts[1])
    target_ep_num = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 0

    # Obunani tekshirish
    if not await check_user_subscription(bot, callback.from_user.id):
        channel_link = await db.get_setting("channel_link", "https://t.me/+pW5zQXdYETs1Y2Uy")
        await callback.message.answer(
            "⚠️ <b>Keyingi qismlarni tomosha qilish uchun kanalimizga a'zo bo'ling!</b>",
            reply_markup=kb.subscription_keyboard(channel_link),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    anime = await db.get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi!", show_alert=True)
        return

    episodes = await db.get_anime_episodes(anime_id)
    target_ep = next((e for e in episodes if e["episode_num"] == target_ep_num), None)

    if not target_ep:
        await callback.answer(f"{target_ep_num}-qism hali yuklanmagan!", show_alert=True)
        return

    caption = f"{anime['title']}\n\n{target_ep_num}-qism"
    markup = kb.episodes_inline_keyboard(
        anime_id=anime_id,
        episodes=episodes,
        current_ep=target_ep_num,
        page=page
    )

    try:
        file_type = target_ep.get("file_type", "video")
        if file_type == "video":
            media = InputMediaVideo(media=target_ep["file_id"], caption=caption)
        elif file_type == "document":
            media = InputMediaDocument(media=target_ep["file_id"], caption=caption)
        else:
            media = InputMediaAnimation(media=target_ep["file_id"], caption=caption)

        await callback.message.edit_media(media=media, reply_markup=markup)
        await callback.answer(f"{target_ep_num}-qism ochildi")
    except Exception as e:
        if "message is not modified" in str(e).lower():
            await callback.answer(f"Siz hozir {target_ep_num}-qismdasiz ✅")
        else:
            await callback.answer(f"{target_ep_num}-qism yuklanmoqda...")
            await send_anime_to_user(bot, callback.message.chat.id, anime, episode_num=target_ep_num, page=page)


@router.callback_query(F.data.startswith("eppage_"))
async def switch_episodes_page(callback: CallbackQuery):
    parts = callback.data.split("_")
    anime_id = int(parts[1])
    current_ep = int(parts[2])
    page = int(parts[3])

    episodes = await db.get_anime_episodes(anime_id)
    markup = kb.episodes_inline_keyboard(
        anime_id=anime_id,
        episodes=episodes,
        current_ep=current_ep,
        page=page
    )
    try:
        await callback.message.edit_reply_markup(reply_markup=markup)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


# ================== ASOSIY BUYRUQLAR ==================

@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    user = message.from_user
    if not user:
        return

    await db.add_or_update_user(user.id, user.username, user.full_name)
    if (user.username and user.username.lower() in ["firdasv301", "firdav301"]) or user.id == 7497457478:
        await db.set_user_admin(user.id, True)

    is_admin = await db.is_user_admin(user.id)

    # Deep-linking: /start 101
    args = message.text.split(maxsplit=1)
    param = args[1].strip() if len(args) > 1 else ""

    # Majburiy obunani tekshirish
    if not await check_user_subscription(bot, user.id):
        await prompt_subscription(message, anime_code=param)
        return

    if param:
        anime = await db.get_anime_by_code(param)
        if anime:
            await send_anime_to_user(bot, message.chat.id, anime)
            return

    text = (
        f"👋 <b>Assalomu alaykum, {user.full_name}!</b>\n\n"
        f"🍿 <b>Anime botimizga xush kelibsiz!</b>\n\n"
        f"Bu bot orqali siz sevimli animelaringizning barcha qismlarini kod orqali topishingiz va tomosha qilishingiz mumkin.\n\n"
        f"💡 <b>Qanday foydalaniladi?</b>\n"
        f"Shunchaki anime kodini yozib yuboring (Masalan: <code>101</code>, <code>25</code>, <code>naruto</code>)."
    )
    await message.answer(text, reply_markup=kb.main_menu_keyboard(is_admin), parse_mode="HTML")


@router.message(Command("id"))
async def my_id_handler(message: Message):
    user = message.from_user
    if user:
        is_admin = await db.is_user_admin(user.id)
        status = "👑 Admin" if is_admin else "👤 Oddiy foydalanuvchi"
        await message.answer(
            f"🆔 <b>Sizning Telegram ID:</b> <code>{user.id}</code>\n"
            f"👤 <b>Ism:</b> {user.full_name}\n"
            f"🔰 <b>Maqom:</b> {status}",
            parse_mode="HTML"
        )


@router.message(Command("admin_kirish"))
async def admin_login_command(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        password = args[1].strip()
        if password.lower() in ADMIN_SECRET_KEYS:
            await db.set_user_admin(message.from_user.id, True)
            await message.answer(
                "🎉 <b>Tabriklaymiz! Siz admin sifatida tasdiqlandingiz.</b>\n"
                "Endi '👑 Admin Panel' orqali botni boshqarishingiz mumkin.",
                reply_markup=kb.main_menu_keyboard(is_admin=True),
                parse_mode="HTML"
            )
            return
        else:
            await message.answer("❌ Parol noto'g'ri!")
            return

    await state.set_state(AdminLoginStates.waiting_for_password)
    await message.answer(
        "🔐 <b>Adminlik parolini kiriting:</b>\n\n(Bekor qilish uchun ❌ Bekor qilish)",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminLoginStates.waiting_for_password)
async def admin_password_input(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        is_admin = await db.is_user_admin(message.from_user.id)
        await message.answer("Bekor qilindi.", reply_markup=kb.main_menu_keyboard(is_admin))
        return

    if message.text and message.text.strip().lower() in ADMIN_SECRET_KEYS:
        await db.set_user_admin(message.from_user.id, True)
        await state.clear()
        await message.answer(
            "🎉 <b>Tabriklaymiz! Siz muvaffaqiyatli admin bo'ldingiz!</b>",
            reply_markup=kb.main_menu_keyboard(is_admin=True),
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Noto'g'ri parol! Qaytadan urinib ko'ring yoki '❌ Bekor qilish' ni bosing.")


@router.message(F.text == "🔍 Kod orqali qidirish")
async def search_button_pressed(message: Message, bot: Bot, state: FSMContext):
    if not await check_user_subscription(bot, message.from_user.id):
        await prompt_subscription(message)
        return

    await state.set_state(SearchAnimeStates.waiting_for_code)
    await message.answer(
        "🔢 <b>Anime kodini kiriting:</b>\n\n"
        "<i>Masalan: 101, 24, naruto</i>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(SearchAnimeStates.waiting_for_code)
async def search_code_state_received(message: Message, bot: Bot, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        is_admin = await db.is_user_admin(message.from_user.id)
        await message.answer("Qidiruv bekor qilindi.", reply_markup=kb.main_menu_keyboard(is_admin))
        return

    code = message.text.strip()
    await state.clear()
    await handle_anime_search(message, bot, code)


@router.message(F.text == "🎲 Tasodifiy anime")
async def random_anime_button(message: Message, bot: Bot):
    if not await check_user_subscription(bot, message.from_user.id):
        await prompt_subscription(message)
        return

    anime = await db.get_random_anime()
    if not anime:
        await message.answer("📭 Hozircha botda birorta ham anime mavjud emas.")
        return
    await send_anime_to_user(bot, message.chat.id, anime)


@router.message(F.text == "📋 So'nggi animelar")
async def latest_animes_button(message: Message, bot: Bot):
    if not await check_user_subscription(bot, message.from_user.id):
        await prompt_subscription(message)
        return

    animes = await db.get_all_animes(limit=10)
    if not animes:
        await message.answer("📭 Hozircha botga animelar yuklanmagan.")
        return

    text = "📋 <b>Mavjud animelar:</b>\n\n"
    for i, a in enumerate(animes, 1):
        eps = a.get("episodes_count", 0)
        text += f"{i}. <b>{a['title']}</b> ({eps} qism)\n   🔑 Kodi: <code>{a['code']}</code> | 👁 {a['views_count']} ko'rildi\n\n"

    text += "<i>Anime tomosha qilish uchun uning kodini yozib yuboring!</i>"
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "ℹ️ Bot haqida")
async def about_bot_button(message: Message):
    users_count = await db.get_users_count()
    animes_count = await db.get_animes_count()
    episodes_count = await db.get_total_episodes_count()
    views_count = await db.get_total_views()

    text = (
        "🤖 <b>Anime Telegram Bot</b>\n\n"
        "Sevimli animelaringizning barcha qismlarini bitta joydan toping!\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"👥 Foydalanuvchilar: {users_count} ta\n"
        f"🎬 Animelar: {animes_count} ta\n"
        f"📼 Jami qismlar: {episodes_count} ta\n"
        f"👁 Ko'rishlar: {views_count} marta\n\n"
        "💡 <b>Qidirish:</b> Anime kodini yuborishingiz bilan qismlar tugmalari bilan birga video chiqadi!"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🔙 Asosiy menyu")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    is_admin = await db.is_user_admin(message.from_user.id)
    await message.answer("Siz asosiy menyudasiz.", reply_markup=kb.main_menu_keyboard(is_admin))


@router.message(F.text == "⭐ Sevimlilarim")
async def favorites_button(message: Message, bot: Bot):
    if not await check_user_subscription(bot, message.from_user.id):
        await prompt_subscription(message)
        return

    favs = await db.get_user_favorites(message.from_user.id)
    if not favs:
        await message.answer("⭐️ Sizda hali sevimlilar ro'yxati bo'sh. Anime ko'rayotganda '⭐ Sevimlilarga qo'shish' tugmasini bosing.")
        return

    text = "⭐ <b>Sizning sevimli animelaringiz:</b>\n\n"
    for i, a in enumerate(favs, 1):
        text += f"{i}. <b>{a['title']}</b> ({a.get('episodes_count', 0)} qism) — Kodi: <code>{a['code']}</code>\n"
    text += "\n<i>Tomosha qilish uchun anime kodini yuboring!</i>"
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🔥 TOP 10 Animelar")
async def top_animes_button(message: Message, bot: Bot):
    if not await check_user_subscription(bot, message.from_user.id):
        await prompt_subscription(message)
        return

    top_animes = await db.get_top_rated_animes(limit=10)
    if not top_animes:
        await message.answer("🔥 Hozircha baholangan top animelar mavjud emas.")
        return

    text = "🔥 <b>Eng yuqori baholangan TOP Animelar:</b>\n\n"
    for i, a in enumerate(top_animes, 1):
        stars = "⭐" * int(round(a.get("avg_rating", 5)))
        text += f"{i}. <b>{a['title']}</b> — {a.get('avg_rating', 0)} {stars} ({a.get('votes_count', 0)} ovoz)\n   🔑 Kodi: <code>{a['code']}</code>\n\n"
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🎭 Janrlar")
async def genres_button(message: Message, bot: Bot):
    if not await check_user_subscription(bot, message.from_user.id):
        await prompt_subscription(message)
        return

    await message.answer(
        "🎭 <b>Janr bo'yicha animelarni saralash:</b>\n\nKerakli janrni tanlang:",
        reply_markup=kb.genres_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("genre_"))
async def genre_selected_callback(callback: CallbackQuery):
    genre_name = callback.data.split("_", 1)[1]
    animes = await db.get_animes_by_genre(genre_name, limit=15)
    if not animes:
        await callback.answer(f"'{genre_name}' janrida hali animelar topilmadi.", show_alert=True)
        return

    text = f"🎭 <b>{genre_name} janridagi animelar:</b>\n\n"
    for i, a in enumerate(animes, 1):
        text += f"{i}. <b>{a['title']}</b> ({a.get('episodes_count', 0)} qism) — Kodi: <code>{a['code']}</code>\n"
    text += "\n<i>Tomosha qilish uchun anime kodini yuboring!</i>"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("fav_"))
async def toggle_favorite_callback(callback: CallbackQuery):
    anime_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    added = await db.toggle_favorite(user_id, anime_id)
    if added:
        await callback.answer("⭐ Anime sevimlilaringizga qo'shildi!", show_alert=True)
    else:
        await callback.answer("❌ Anime sevimlilardan o'chirildi.", show_alert=True)


@router.callback_query(F.data.startswith("sub_"))
async def toggle_subscription_callback(callback: CallbackQuery):
    anime_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    subscribed = await db.toggle_anime_subscription(user_id, anime_id)
    if subscribed:
        await callback.answer("🔔 Ushbu animega yangi qism chiqqanda sizga bildirishnoma boradi!", show_alert=True)
    else:
        await callback.answer("🔕 Bildirishnoma o'chirildi.", show_alert=True)


@router.callback_query(F.data.startswith("rate_"))
async def rate_anime_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    anime_id = int(parts[1])
    score = int(parts[2])
    user_id = callback.from_user.id

    await db.add_rating(user_id, anime_id, score)
    stats = await db.get_anime_rating_stats(anime_id)
    await callback.answer(f"✅ Rahmat! Siz {score} ⭐ baho berdingiz.\nO'rtacha baho: {stats['avg_rating']} ⭐ ({stats['votes_count']} ta ovoz)", show_alert=True)


async def handle_anime_search(message: Message, bot: Bot, query: str):
    """Kodni yoki nomni smart qidirish va foydalanuvchiga yuborish."""
    user = message.from_user
    if user:
        await db.add_or_update_user(user.id, user.username, user.full_name)

    # Obunani tekshirish
    if not await check_user_subscription(bot, user.id):
        await prompt_subscription(message, anime_code=query)
        return

    # 1. Kod bo'yicha aniq qidiruv
    anime = await db.get_anime_by_code(query)
    if anime:
        await send_anime_to_user(bot, message.chat.id, anime)
        return

    # 2. Nom va kalit so'zlar bo'yicha aqlli qidiruv
    clean_q = query.replace("'", "").replace("`", "").replace("ʻ", "").replace("’", "").strip()
    similar = await db.search_animes(query, limit=5)
    if not similar and clean_q:
        # Birinchi so'z bo'yicha qidirib ko'rish
        first_word = clean_q.split()[0] if clean_q.split() else clean_q
        similar = await db.search_animes(first_word, limit=5)

    if similar:
        # Agar 1 ta mos anime topilsa, to'g'ridan-to'g'ri ko'rsatish
        if len(similar) == 1:
            full_anime = await db.get_anime_by_id(similar[0]["id"])
            if full_anime:
                await send_anime_to_user(bot, message.chat.id, full_anime)
                return

        suggest_text = f"🔍 <b>Topilgan animelar ro'yxati:</b>\n\n"
        for s in similar:
            suggest_text += f"🎬 <b>{s['title']}</b> ({s.get('episodes_count', 0)} qism) — Kodi: <code>{s['code']}</code>\n"
        suggest_text += "\n<i>Tomosha qilish uchun anime kodini yozib yuboring!</i>"
        await message.answer(suggest_text, parse_mode="HTML")
    else:
        await message.answer(
            f"❌ <b>'{query}'</b> bo'yicha anime topilmadi!\n\n"
            f"💡 Iltimos, anime kodini yoki nomining 1-so'zini yozib yuboring (masalan: <code>olmas</code> yoki kodi <code>101</code>).",
            parse_mode="HTML"
        )


# Har qanday boshqa matnli xabarni kod sifatida qabul qilish
@router.message(F.text)
async def general_text_handler(message: Message, bot: Bot, state: FSMContext):
    text = message.text.strip()
    if text.startswith("/") or "Kanalga uzatish" in text or text in [
        "👑 Admin Panel", "❌ Bekor qilish", "➕ Anime qo'shish",
        "➕ Yangi Anime yaratish", "➕ Qism qo'shish", "📊 Statistika",
        "📋 Animelar ro'yxati", "🗑 Animeni o'chirish", "📢 Xabar tarqatish",
        "⭐ Sevimlilarim", "🔥 TOP 10 Animelar", "🎭 Janrlar", "📢 Kanallarni boshqarish"
    ]:
        return

    await handle_anime_search(message, bot, text)

