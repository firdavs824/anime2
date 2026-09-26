import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import CreateAnimeStates, AddEpisodeStates, DeleteAnimeStates, BroadcastStates, ChannelPostStates, AddChannelStates

router = Router()
# Admin buyruqlari ham faqat shaxsiy yozishmada (lichkada) ishlasin
router.message.filter(F.chat.type == "private")



async def check_admin_permission(user_id: int) -> bool:
    return await db.is_user_admin(user_id)


# ================== ADMIN PANEL ASOSIY MENYU ==================

@router.message(Command("admin"))
@router.message(F.text == "👑 Admin Panel")
async def open_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    if not await check_admin_permission(message.from_user.id):
        await message.answer("⛔️ Kechirasiz, sizda adminlik huquqi yo'q!")
        return

    text = (
        "👑 <b>Admin Panelga xush kelibsiz!</b>\n\n"
        "Quyidagi boshqaruv bo'limlaridan birini tanlang:"
    )
    await message.answer(text, reply_markup=kb.admin_menu_keyboard(), parse_mode="HTML")


@router.message(F.text == "❌ Bekor qilish")
async def cancel_any_action(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    is_admin = await check_admin_permission(message.from_user.id)
    if is_admin:
        await message.answer("Amal bekor qilindi.", reply_markup=kb.admin_menu_keyboard())
    else:
        await message.answer("Amal bekor qilindi.", reply_markup=kb.main_menu_keyboard(is_admin=False))


# ================== 1. ANIME YUKLASH VA QISMLAR BOSHQARUVI ==================

@router.message(F.text.in_(["➕ Anime qo'shish", "➕ Yangi Anime yaratish", "➕ Qism qo'shish"]))
async def start_add_anime_menu(message: Message, state: FSMContext):
    if not await check_admin_permission(message.from_user.id):
        return

    await state.clear()
    animes = await db.get_all_animes(limit=30)

    text = (
        "📥 <b>Anime yuklash bo'limi:</b>\n\n"
        "Yangi anime yaratasizmi yoki avval qo'shilgan animega keyingi qismni yuklaysizmi?\n\n"
        "<i>Quyidagi tugmalardan birini tanlang:</i>"
    )
    await message.answer(
        text,
        reply_markup=kb.choose_anime_to_add_keyboard(animes),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "create_new_anime")
async def start_create_new_anime_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateAnimeStates.waiting_for_title)
    await callback.message.edit_text(
        "📝 <b>1-qadam: Yangi anime nomini kiriting:</b>\n\n"
        "<i>Masalan: O'lmas qirolning kundalik hayoti</i>\n\n"
        "(Bekor qilish uchun pastdagi menyudan ❌ Bekor qilish ni bosing)",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CreateAnimeStates.waiting_for_title, F.text)
async def receive_create_title(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await cancel_any_action(message, state)
        return

    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(CreateAnimeStates.waiting_for_code)
    await message.answer(
        f"✅ Nomi saqlandi: <b>{title}</b>\n\n"
        "🔢 <b>2-qadam: Anime uchun maxsus KOD kiriting:</b>\n"
        "<i>Foydalanuvchilar aynan shu kodni yozganda anime chiqadi.</i>\n"
        "<i>Masalan: 1, 25, 101</i>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(CreateAnimeStates.waiting_for_code, F.text)
async def receive_create_code(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await cancel_any_action(message, state)
        return

    code = message.text.strip().lower()
    if not code:
        await message.answer("⚠️ Kod bo'sh bo'lmasligi kerak. Qaytadan kiriting:")
        return

    existing_anime = await db.get_anime_by_code(code, increment_views=False)
    if existing_anime:
        anime_id = existing_anime["id"]
        max_ep = await db.get_max_episode_num(anime_id)
        next_ep = max_ep + 1
        await state.update_data(anime_id=anime_id, title=existing_anime["title"], code=code, episode_num=next_ep)
        await message.answer(
            f"ℹ️ <b>'{existing_anime['title']}'</b> animosi allaqachon <code>{code}</code> kodi bilan mavjud!\n\n"
            f"Hozirda yuklangan qismlar: <b>{max_ep} ta</b>.\n"
            f"Ushbu animega keyingi <b>{next_ep}-qism</b> videosini yuklamoqchimisiz?",
            reply_markup=kb.code_exists_action_keyboard(anime_id, next_ep),
            parse_mode="HTML"
        )
        return

    await state.update_data(code=code)
    await state.set_state(CreateAnimeStates.waiting_for_video)
    await message.answer(
        f"✅ Kodi: <code>{code}</code>\n\n"
        "📹 <b>3-qadam: Animening 1-QISM videosini yuboring:</b>\n"
        "(Video yoki hujjat fayli shaklida)",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("quick_add_ep_"))
async def callback_quick_add_ep(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    anime_id = int(parts[3])
    next_ep = int(parts[4])

    anime = await db.get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi!", show_alert=True)
        return

    await state.update_data(anime_id=anime_id, title=anime["title"], code=anime["code"], episode_num=next_ep)
    await state.set_state(AddEpisodeStates.waiting_for_video)

    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b> (Kodi: <code>{anime['code']}</code>)\n\n"
        f"📹 <b>{next_ep}-qism videosini yuboring:</b>\n"
        "<i>(Bekor qilish uchun pastdagi '❌ Bekor qilish' ni bosing)</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_code_input")
async def cancel_code_input_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    animes = await db.get_all_animes(limit=30)
    await callback.message.edit_text(
        "Amal bekor qilindi.\n\nYangi anime yaratish yoki mavjudini tanlash:",
        reply_markup=kb.choose_anime_to_add_keyboard(animes)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_anime_ep_"))
async def callback_select_existing_anime(callback: CallbackQuery, state: FSMContext):
    anime_id = int(callback.data.split("_")[3])
    anime = await db.get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi!", show_alert=True)
        return

    max_ep = await db.get_max_episode_num(anime_id)
    next_ep = max_ep + 1

    await state.update_data(anime_id=anime_id, title=anime["title"], code=anime["code"], episode_num=next_ep)
    await state.set_state(AddEpisodeStates.waiting_for_video)

    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b> tanlandi! (Kodi: <code>{anime['code']}</code>)\n\n"
        f"Mavjud qismlar: <b>{max_ep} ta</b>.\n"
        f"Navbatdagi qism: <b>{next_ep}-qism</b>.\n\n"
        f"📹 <b>{next_ep}-qism videosini yuboring:</b>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CreateAnimeStates.waiting_for_video, F.video)
@router.message(CreateAnimeStates.waiting_for_video, F.document)
@router.message(CreateAnimeStates.waiting_for_video, F.animation)
async def receive_create_video(message: Message, state: FSMContext):
    data = await state.get_data()
    title = data["title"]
    code = data["code"]

    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    else:
        file_id = message.animation.file_id
        file_type = "animation"

    # Bazaga qo'shish
    try:
        anime_id = await db.add_or_get_anime(code=code, title=title)
        await db.add_episode(anime_id=anime_id, episode_num=1, file_id=file_id, file_type=file_type)

        # Navbatdagi 2-qismni kutish rejimiga o'tadi
        await state.update_data(anime_id=anime_id, episode_num=2)
        await state.set_state(AddEpisodeStates.waiting_for_video)

        await message.answer(
            f"🎉 <b>Anime muvaffaqiyatli yaratildi va 1-qism saqlandi!</b>\n\n"
            f"🎬 <b>Nomi:</b> {title}\n"
            f"🔢 <b>Kodi:</b> <code>{code}</code>\n"
            f"📼 <b>1-qism</b> tayyor!\n\n"
            f"💡 <i>Agar 2-qism videosi bo'lsa, to'g'ridan-to'g'ri hozir yuborishingiz mumkin (yoki menyuga o'ting).</i>",
            reply_markup=kb.admin_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}\nIltimos, qaytadan urinib ko'ring.")


@router.message(CreateAnimeStates.waiting_for_video)
async def invalid_create_video(message: Message):
    if message.text == "❌ Bekor qilish":
        return
    await message.answer("⚠️ Iltimos, video yoki fayl yuboring!")


# ================== MAVJUD ANIMEGA QISM YUKLASH ==================

@router.message(AddEpisodeStates.waiting_for_video, F.video)
@router.message(AddEpisodeStates.waiting_for_video, F.document)
@router.message(AddEpisodeStates.waiting_for_video, F.animation)
async def receive_episode_file(message: Message, state: FSMContext):
    data = await state.get_data()
    anime_id = data.get("anime_id")
    ep_num = data.get("episode_num", 1)
    title = data.get("title", "")
    code = data.get("code", "")

    if not anime_id:
        await message.answer("⚠️ Qaysi anime ekanligi aniqlanmadi, iltimos '➕ Anime qo'shish' orqali qaytadan tanlang.")
        await state.clear()
        return

    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    else:
        file_id = message.animation.file_id
        file_type = "animation"

    await db.add_episode(anime_id=anime_id, episode_num=ep_num, file_id=file_id, file_type=file_type)

    # Obunachilarga avtomatik bildirishnoma yuborish
    asyncio.create_task(notify_anime_subscribers(message.bot, anime_id, title, code, ep_num))

    next_ep = ep_num + 1
    await state.update_data(episode_num=next_ep)

    await message.answer(
        f"✅ <b>{title}</b> uchun <b>{ep_num}-qism</b> muvaffaqiyatli saqlandi!\n\n"
        f"Foydalanuvchilar <code>{code}</code> deb yozganda endi ushbu qism ham chiqadi.\n\n"
        f"💡 <i>Keyingi <b>{next_ep}-qism</b> videosi bo'lsa, uni ham darhol yuborishingiz mumkin!</i>",
        reply_markup=kb.admin_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(AddEpisodeStates.waiting_for_video)
async def invalid_episode_file(message: Message):
    if message.text == "❌ Bekor qilish":
        return
    await message.answer("⚠️ Iltimos, video yoki fayl yuboring!")


# ================== 3. ANIMELAR RO'YXATI ==================

ITEMS_PER_PAGE = 8

@router.message(F.text == "📋 Animelar ro'yxati")
async def show_anime_list(message: Message):
    if not await check_admin_permission(message.from_user.id):
        return

    total = await db.get_animes_count()
    if total == 0:
        await message.answer("📭 Hozircha botda animelar yo'q.")
        return

    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    animes = await db.get_all_animes(limit=ITEMS_PER_PAGE, offset=0)

    text = f"📋 <b>Barcha animelar ro'yxati</b> (Jami: {total} ta, Sahifa: 1/{total_pages}):\n\n"
    for a in animes:
        text += f"• <b>{a['title']}</b> ({a['episodes_count']} qism) | Kodi: <code>{a['code']}</code> | 👁 {a['views_count']}\n"

    keyboard = kb.anime_list_keyboard(animes, page=0, total_pages=total_pages)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("anime_page_"))
async def paginate_anime_list(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    total = await db.get_animes_count()
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0

    offset = page * ITEMS_PER_PAGE
    animes = await db.get_all_animes(limit=ITEMS_PER_PAGE, offset=offset)

    text = f"📋 <b>Barcha animelar ro'yxati</b> (Jami: {total} ta, Sahifa: {page + 1}/{total_pages}):\n\n"
    for a in animes:
        text += f"• <b>{a['title']}</b> ({a['episodes_count']} qism) | Kodi: <code>{a['code']}</code> | 👁 {a['views_count']}\n"

    keyboard = kb.anime_list_keyboard(animes, page=page, total_pages=total_pages)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("view_anime_"))
async def view_anime_detail(callback: CallbackQuery):
    anime_id = int(callback.data.split("_")[2])
    anime = await db.get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi!", show_alert=True)
        return

    episodes = await db.get_anime_episodes(anime_id)
    ep_numbers = [str(e["episode_num"]) for e in episodes]
    eps_str = ", ".join(ep_numbers) if ep_numbers else "Yo'q"

    text = (
        f"🎬 <b>{anime['title']}</b>\n\n"
        f"🔢 <b>Kodi:</b> <code>{anime['code']}</code>\n"
        f"👁 <b>Ko'rishlar:</b> {anime['views_count']} marta\n"
        f"📼 <b>Mavjud qismlar ({len(episodes)} ta):</b> {eps_str}\n"
    )

    keyboard = kb.anime_admin_details_keyboard(anime["id"], anime["code"])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "back_to_anime_list")
async def back_to_anime_list_callback(callback: CallbackQuery):
    total = await db.get_animes_count()
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    animes = await db.get_all_animes(limit=ITEMS_PER_PAGE, offset=0)

    text = f"📋 <b>Barcha animelar ro'yxati</b> (Jami: {total} ta, Sahifa: 1/{total_pages}):\n\n"
    for a in animes:
        text += f"• <b>{a['title']}</b> ({a['episodes_count']} qism) | Kodi: <code>{a['code']}</code> | 👁 {a['views_count']}\n"

    keyboard = kb.anime_list_keyboard(animes, page=0, total_pages=total_pages)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_del_"))
async def delete_anime_by_button(callback: CallbackQuery):
    anime_id = int(callback.data.split("_")[2])
    anime = await db.get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi!", show_alert=True)
        return

    await db.delete_anime_by_id(anime_id)
    await callback.message.edit_text(
        f"🗑 <b>{anime['title']}</b> (Kodi: <code>{anime['code']}</code>) va barcha qismlari o'chirildi!",
        parse_mode="HTML"
    )
    await callback.answer("Anime o'chirildi.")


# ================== 4. ANIMENI KOD ORQALI O'CHIRISH ==================

@router.message(F.text == "🗑 Animeni o'chirish")
async def ask_delete_anime_code(message: Message, state: FSMContext):
    if not await check_admin_permission(message.from_user.id):
        return

    await state.set_state(DeleteAnimeStates.waiting_for_code)
    await message.answer(
        "🗑 <b>O'chirmoqchi bo'lgan anime kodini kiriting:</b>\n\n"
        "<i>(Bekor qilish uchun '❌ Bekor qilish' ni bosing)</i>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(DeleteAnimeStates.waiting_for_code, F.text)
async def process_delete_anime(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await cancel_any_action(message, state)
        return

    code = message.text.strip().lower()
    anime = await db.get_anime_by_code(code, increment_views=False)
    if not anime:
        await message.answer(
            f"❌ <b>'{code}'</b> kodli anime topilmadi! Qaytadan tekshirib kiriting:",
            parse_mode="HTML"
        )
        return

    deleted = await db.delete_anime_by_code(code)
    await state.clear()
    if deleted:
        await message.answer(
            f"✅ <b>'{anime['title']}'</b> (Kodi: <code>{code}</code>) barcha qismlari bilan o'chirildi!",
            reply_markup=kb.admin_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ O'chirishda xatolik yuz berdi.", reply_markup=kb.admin_menu_keyboard())


# ================== 5. STATISTIKA VA KANAL SOZLAMALARI ==================

@router.my_chat_member()
async def bot_added_as_admin_channel(event: ChatMemberUpdated):
    """Bot kanalga admin qilib qo'shilganda kanal ID sini avtomatik saqlash."""
    if event.chat.type in ["channel", "supergroup"]:
        status = event.new_chat_member.status
        if status in ["administrator", "creator"]:
            chat_id = str(event.chat.id)
            chat_title = event.chat.title or "Kanal"
            await db.set_setting("channel_id", chat_id)
            await db.set_setting("channel_title", chat_title)

            admins = await db.get_all_admins()
            for adm in admins:
                try:
                    await event.bot.send_message(
                        adm,
                        f"🎉 <b>Bot '{chat_title}' kanaliga administrator qilindi!</b>\n\n"
                        f"🆔 Kanal ID: <code>{chat_id}</code>\n"
                        f"✅ Majburiy obuna ushbu kanal bo'yicha to'liq ishga tushdi!\n"
                        f"Endi botdan foydalanuvchilar faqat ushbu kanalga a'zo bo'lgach animeni ko'ra oladilar.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass


@router.message(F.forward_from_chat)
async def admin_forwarded_channel_post(message: Message):
    """Admin kanaldan post uzatganda kanal ID sini saqlash."""
    if not await check_admin_permission(message.from_user.id):
        return

    fchat = message.forward_from_chat
    if fchat.type in ["channel", "supergroup"]:
        chat_id = str(fchat.id)
        chat_title = fchat.title or "Kanal"
        await db.set_setting("channel_id", chat_id)
        await db.set_setting("channel_title", chat_title)
        link = await db.get_setting("channel_link", "https://t.me/+pW5zQXdYETs1Y2Uy")
        await message.answer(
            f"✅ <b>'{chat_title}' kanali muvaffaqiyatli ulandi!</b>\n\n"
            f"🆔 Kanal ID: <code>{chat_id}</code>\n"
            f"🔗 Havola: {link}\n\n"
            f"💡 <i>Muhim: Bot (@New_Anime_Uz_bot) ushbu kanalda administrator bo'lishi kerak.</i>",
            parse_mode="HTML"
        )


@router.message(Command("kanal"))
async def channel_settings_command(message: Message):
    if not await check_admin_permission(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        new_link = args[1].strip()
        await db.set_setting("channel_link", new_link)
        await message.answer(f"✅ Kanal havolasi yangilandi:\n{new_link}")
        return

    channel_id = await db.get_setting("channel_id", "Ulanmagan ❌ (Botni kanalga admin qiling)")
    channel_title = await db.get_setting("channel_title", "Noma'lum")
    channel_link = await db.get_setting("channel_link", "https://t.me/+pW5zQXdYETs1Y2Uy")

    text = (
        "📢 <b>Majburiy Obuna Sozlamalari:</b>\n\n"
        f"📌 <b>Kanal:</b> {channel_title}\n"
        f"🆔 <b>Kanal ID:</b> <code>{channel_id}</code>\n"
        f"🔗 <b>Havola:</b> {channel_link}\n\n"
        "💡 <b>Kanalni ulash bo'yicha ko'rsatma:</b>\n"
        "1. Botni (@New_Anime_Uz_bot) o'sha kanalingizga <b>ADMINISTRATOR</b> qilib qo'shing;\n"
        "2. Yoki kanaldagi istalgan xabarni botga <b>FORWARD (uzatish)</b> qilib yuboring;\n"
        "3. Havolani o'zgartirish uchun: <code>/kanal yangi_havola</code> deb yozing."
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    if not await check_admin_permission(message.from_user.id):
        return

    users_count = await db.get_users_count()
    animes_count = await db.get_animes_count()
    episodes_count = await db.get_total_episodes_count()
    views_count = await db.get_total_views()
    admins = await db.get_all_admins()
    channel_id = await db.get_setting("channel_id")
    channel_status = "Ulangan ✅" if channel_id else "Ulanmagan ⏳ (Botni kanalga admin qiling)"

    text = (
        "📊 <b>Bot Statistikasi:</b>\n\n"
        f"👥 <b>Foydalanuvchilar:</b> {users_count} ta\n"
        f"🎬 <b>Animelar soni:</b> {animes_count} ta\n"
        f"📼 <b>Yuklangan qismlar:</b> {episodes_count} ta\n"
        f"👁 <b>Jami tomosha qilishlar:</b> {views_count} marta\n"
        f"📢 <b>Majburiy kanal:</b> {channel_status}\n"
        f"👑 <b>Adminlar:</b> {len(admins)} ta\n"
    )
    await message.answer(text, parse_mode="HTML")


# ================== 6. XABAR TARQATISH ==================

@router.message(F.text == "📢 Xabar tarqatish")
async def start_broadcast(message: Message, state: FSMContext):
    if not await check_admin_permission(message.from_user.id):
        return

    await state.set_state(BroadcastStates.waiting_for_message)
    await message.answer(
        "📢 <b>Barcha foydalanuvchilarga yuboriladigan xabarni yozing:</b>\n\n"
        "Matn, rasm, video yoki havola yuborishingiz mumkin.\n"
        "<i>(Bekor qilish uchun '❌ Bekor qilish' ni bosing)</i>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(BroadcastStates.waiting_for_message)
async def receive_broadcast_message(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await cancel_any_action(message, state)
        return

    await state.update_data(msg_id=message.message_id, from_chat_id=message.chat.id)
    await state.set_state(BroadcastStates.confirm_send)

    users_count = await db.get_users_count()
    await message.answer(
        f"📢 <b>Xabar tayyor!</b>\n\n"
        f"Ushbu xabar <b>{users_count} ta</b> foydalanuvchiga yuboriladi.\n"
        "Tasdiqlaysizmi?",
        reply_markup=kb.confirm_broadcast_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_broadcast")
async def do_broadcast(callback: CallbackQuery, bot: Bot, state: FSMContext):
    data = await state.get_data()
    msg_id = data.get("msg_id")
    from_chat_id = data.get("from_chat_id")
    await state.clear()

    if not msg_id or not from_chat_id:
        await callback.answer("Xabar topilmadi!", show_alert=True)
        return

    await callback.message.edit_text("⏳ <b>Xabar yuborilmoqda, kuting...</b>", parse_mode="HTML")

    user_ids = await db.get_all_user_ids()
    sent_count = 0
    fail_count = 0

    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=from_chat_id, message_id=msg_id)
            sent_count += 1
            await asyncio.sleep(0.04)
        except Exception:
            fail_count += 1

    await callback.message.answer(
        f"📢 <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"✅ Yuborildi: {sent_count} ta\n"
        f"❌ Yetib bormadi (bloklangan): {fail_count} ta",
        reply_markup=kb.admin_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Xabar tarqatish bekor qilindi.")
    await callback.message.answer("Asosiy admin menyusi:", reply_markup=kb.admin_menu_keyboard())
    await callback.answer()


# ================== 7. KANALGA UZATISH ==================

@router.message(F.text.contains("Kanalga uzatish"))
async def channel_post_start(message: Message, state: FSMContext):
    if not await check_admin_permission(message.from_user.id):
        return

    channel_id = await db.get_setting("channel_id")
    channels = await db.get_all_channels()
    if not channel_id and not channels:
        await message.answer(
            "⚠️ <b>Kanal ulanmagan!</b>\n\n"
            "Iltimos, avval botingizni kanalga Administrator qilib qo'shing yoki "
            "kanaldan biror xabarni botga <b>forward (uzatish)</b> qilib yuboring.\n\n"
            "Kanal sozlamalari: /kanal",
            parse_mode="HTML"
        )
        return

    await state.clear()
    animes = await db.get_all_animes(limit=15)

    await message.answer(
        "📢 <b>Kanalga uzatish</b>\n\n"
        "Qaysi anime uchun post tayyorlamoqchisiz?\n"
        "<i>(Anime tanlansa, kanaldagi 'Tomosha qilish' tugmasini bosganlarga botda o'sha anime avtomatik ochiladi!)</i>",
        reply_markup=kb.channel_post_animes_keyboard(animes),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("sendtochan_"))
async def select_anime_for_channel_post(callback: CallbackQuery, state: FSMContext):
    anime_id = int(callback.data.split("_")[1])
    anime = await db.get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi!", show_alert=True)
        return

    await state.update_data(anime_id=anime_id, anime_code=anime["code"], anime_title=anime["title"])
    await state.set_state(ChannelPostStates.waiting_for_media)

    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b> tanlandi! (Kodi: <code>{anime['code']}</code>)\n\n"
        "📸 <b>1-qadam: Post uchun Rasm yoki Video yuboring:</b>\n\n"
        "<i>(Rasm/Video yuboring yoki '⏭ O'tkazib yuborish' tugmasini bosing)</i>",
        parse_mode="HTML"
    )
    await callback.answer()


# --- Media (Rasm / Video) qabul qilish ---
@router.message(ChannelPostStates.waiting_for_media, F.photo)
@router.message(ChannelPostStates.waiting_for_media, F.video)
@router.message(ChannelPostStates.waiting_for_media, F.animation)
async def receive_post_media(message: Message, state: FSMContext):
    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_id = message.video.file_id
        media_type = "video"
    else:
        media_id = message.animation.file_id
        media_type = "animation"

    await state.update_data(media_id=media_id, media_type=media_type)
    await ask_post_text(message, state)


@router.message(ChannelPostStates.waiting_for_media, F.text == "⏭ O'tkazib yuborish")
async def skip_post_media(message: Message, state: FSMContext):
    await state.update_data(media_id=None, media_type=None)
    await ask_post_text(message, state)


@router.message(ChannelPostStates.waiting_for_media, F.text == "❌ Bekor qilish")
async def cancel_post_flow(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=kb.admin_menu_keyboard())


async def ask_post_text(message: Message, state: FSMContext):
    await state.set_state(ChannelPostStates.waiting_for_text)
    await message.answer(
        "✍️ <b>2-qadam: Post matnini (caption) kiriting:</b>\n\n"
        "<i>(Kanalga yuboriladigan xabar matnini yozing. HTML va emojilardan foydalanishingiz mumkin)</i>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )


# --- Post matnini qabul qilish va Preview ko'rsatish ---
@router.message(ChannelPostStates.waiting_for_text, F.text)
async def receive_post_text(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.admin_menu_keyboard())
        return

    post_text = message.text.strip()
    await state.update_data(post_text=post_text)
    await state.set_state(ChannelPostStates.confirm_post)

    data = await state.get_data()
    media_id = data.get("media_id")
    media_type = data.get("media_type")

    confirm_kb = kb.confirm_channel_post_send_keyboard()

    await message.answer("👁 <b>Post ko'rinishi (Preview):</b>", parse_mode="HTML")

    try:
        if media_id and media_type == "photo":
            await message.answer_photo(
                photo=media_id,
                caption=post_text,
                parse_mode="HTML"
            )
        elif media_id and media_type == "video":
            await message.answer_video(
                video=media_id,
                caption=post_text,
                parse_mode="HTML"
            )
        elif media_id and media_type == "animation":
            await message.answer_animation(
                animation=media_id,
                caption=post_text,
                parse_mode="HTML"
            )
        else:
            await message.answer(post_text, parse_mode="HTML")
    except Exception:
        await message.answer(post_text, parse_mode="HTML")

    await message.answer(
        "🚀 <b>Ushbu postni kanalga joylashni tasdiqlaysizmi?</b>",
        reply_markup=confirm_kb,
        parse_mode="HTML"
    )


# --- Tasdiqlash va Kanalga joylash ---
@router.callback_query(F.data == "do_channel_post_send")
async def finalize_channel_post_send(callback: CallbackQuery, bot: Bot, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    channel_id = await db.get_setting("channel_id")
    if not channel_id:
        await callback.answer("Kanal ulanmagan!", show_alert=True)
        return

    me = await bot.get_me()
    bot_username = me.username or "anime_bot"

    post_text = data.get("post_text", "")
    media_id = data.get("media_id")
    media_type = data.get("media_type")
    anime_code = data.get("anime_code", "")
    markup = kb.channel_watch_button(bot_username, anime_code=anime_code)

    try:
        if media_id and media_type == "photo":
            await bot.send_photo(
                chat_id=int(channel_id),
                photo=media_id,
                caption=post_text,
                reply_markup=markup,
                parse_mode="HTML"
            )
        elif media_id and media_type == "video":
            await bot.send_video(
                chat_id=int(channel_id),
                video=media_id,
                caption=post_text,
                reply_markup=markup,
                parse_mode="HTML"
            )
        elif media_id and media_type == "animation":
            await bot.send_animation(
                chat_id=int(channel_id),
                animation=media_id,
                caption=post_text,
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=int(channel_id),
                text=post_text,
                reply_markup=markup,
                parse_mode="HTML"
            )

        channel_title = await db.get_setting("channel_title", "Kanal")
        await callback.message.edit_text(
            f"🎉 <b>Post muvaffaqiyatli <u>{channel_title}</u> kanaliga joylandi!</b>",
            parse_mode="HTML"
        )
        await callback.message.answer("Admin menyu:", reply_markup=kb.admin_menu_keyboard())

    except Exception as e:
        await callback.message.edit_text(
            f"❌ Kanalga joylashda xatolik:\n<code>{e}</code>\n\n"
            "Bot kanalda administrator ekanligini tekshiring.",
            parse_mode="HTML"
        )
        await callback.message.answer("Admin menyu:", reply_markup=kb.admin_menu_keyboard())

    await callback.answer()


@router.callback_query(F.data == "do_channel_post_cancel")
async def cancel_channel_post_send(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Kanalga joylash bekor qilindi.")
    await callback.message.answer("Admin menyu:", reply_markup=kb.admin_menu_keyboard())
    await callback.answer()


# ================== 8. MAJBURIY KANALLARNI BOSHQARISH ==================

async def notify_anime_subscribers(bot: Bot, anime_id: int, title: str, code: str, ep_num: int):
    """Anime kuzatuvchilariga yangi qism chiqqani haqida bildirishnoma yuborish."""
    subscribers = await db.get_anime_subscribers(anime_id)
    for uid in subscribers:
        try:
            await bot.send_message(
                chat_id=uid,
                text=f"🔔 <b>Yangi qism yuklandi!</b>\n\n🎬 <b>{title}</b> animesiga <b>{ep_num}-qism</b> joylandi!\n\n🔑 Kodi: <code>{code}</code>\n\n<i>Tomosha qilish uchun botga kodingizni yozing!</i>",
                parse_mode="HTML"
            )
            await asyncio.sleep(0.04)
        except Exception:
            pass


@router.message(F.text == "📢 Kanallarni boshqarish")
async def manage_channels_menu(message: Message):
    if not await check_admin_permission(message.from_user.id):
        return

    channels = await db.get_all_channels()
    text = "📢 <b>Majburiy kanallar ro'yxati:</b>\n\n"
    if not channels:
        text += "<i>Hozircha birorta ham majburiy kanal qo'shilmagan.</i>\n"
    else:
        for i, c in enumerate(channels, 1):
            text += f"{i}. <b>{c['channel_name']}</b>\n   🆔 <code>{c['channel_id']}</code> | 🔗 <a href='{c['channel_link']}'>Havola</a>\n\n"

    text += "\n<i>Yangi kanal qo'shish yoki mavjudini o'chirish uchun tugmalardan foydalaning:</i>"
    await message.answer(text, reply_markup=kb.channels_admin_keyboard(channels), parse_mode="HTML")


@router.callback_query(F.data == "admin_add_channel")
async def start_add_channel_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddChannelStates.waiting_for_channel_id)
    await callback.message.edit_text(
        "📢 <b>1-qadam: Kanal ID sini yoki username ini kiriting:</b>\n\n"
        "<i>Masalan: -1001234567890 yoki @kanal_username</i>\n\n"
        "💡 <i>Eslatma: Bot ushbu kanalda administrator bo'lishi kerak.</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AddChannelStates.waiting_for_channel_id, F.text)
async def receive_channel_id(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await cancel_any_action(message, state)
        return

    channel_id = message.text.strip()
    await state.update_data(channel_id=channel_id)
    await state.set_state(AddChannelStates.waiting_for_channel_name)
    await message.answer(
        "📝 <b>2-qadam: Kanal nomini kiriting:</b>\n\n"
        "<i>Masalan: Rasmiy Anime Kanalimiz</i>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AddChannelStates.waiting_for_channel_name, F.text)
async def receive_channel_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await cancel_any_action(message, state)
        return

    channel_name = message.text.strip()
    await state.update_data(channel_name=channel_name)
    await state.set_state(AddChannelStates.waiting_for_channel_link)
    await message.answer(
        "🔗 <b>3-qadam: Kanal taklif havolasini (Link) kiriting:</b>\n\n"
        "<i>Masalan: https://t.me/kanal_username yoki taklif havolasi</i>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AddChannelStates.waiting_for_channel_link, F.text)
async def receive_channel_link(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await cancel_any_action(message, state)
        return

    channel_link = message.text.strip()
    data = await state.get_data()
    channel_id = data["channel_id"]
    channel_name = data["channel_name"]

    await db.add_channel(channel_id, channel_name, channel_link)
    await state.clear()

    await message.answer(
        f"✅ <b>Kanal muvaffaqiyatli saqlandi!</b>\n\n"
        f"📢 <b>Nomi:</b> {channel_name}\n"
        f"🆔 <b>ID:</b> <code>{channel_id}</code>\n"
        f"🔗 <b>Link:</b> {channel_link}",
        reply_markup=kb.admin_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_del_chan_"))
async def delete_channel_callback(callback: CallbackQuery):
    chan_db_id = int(callback.data.split("_")[3])
    await db.remove_channel_by_id(chan_db_id)
    await callback.answer("Kanal o'chirildi!", show_alert=True)

    channels = await db.get_all_channels()
    text = "📢 <b>Majburiy kanallar ro'yxati:</b>\n\n"
    if not channels:
        text += "<i>Hozircha birorta ham majburiy kanal qo'shilmagan.</i>\n"
    else:
        for i, c in enumerate(channels, 1):
            text += f"{i}. <b>{c['channel_name']}</b>\n   🆔 <code>{c['channel_id']}</code> | 🔗 <a href='{c['channel_link']}'>Havola</a>\n\n"

    await callback.message.edit_text(text, reply_markup=kb.channels_admin_keyboard(channels), parse_mode="HTML")



