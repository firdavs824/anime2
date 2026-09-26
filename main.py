import asyncio
import logging
import sys

# Windows konsolida emoji va maxsus belgilarni to'g'ri chiqarish
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.exceptions import TelegramNetworkError, TelegramConflictError

from config import BOT_TOKEN
import database as db
from handlers import admin, user


async def set_commands(bot: Bot):
    try:
        commands = [
            BotCommand(command="start", description="Botni ishga tushirish"),
            BotCommand(command="admin", description="Admin panel"),
            BotCommand(command="id", description="Telegram ID raqamim"),
        ]
        await bot.set_my_commands(commands)
    except Exception as e:
        logging.getLogger("AnimeBot").warning(f"Buyruqlarni o'rnatishda xatolik: {e}")


import os
from aiohttp import web

async def start_healthcheck_server():
    try:
        port = int(os.getenv("PORT", 8080))
        app = web.Application()
        app.router.add_get("/", lambda req: web.Response(text="Anime Bot Status: OK 200"))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logging.getLogger("AnimeBot").info(f"Healthcheck HTTP server {port}-portda ishga tushdi.")
    except Exception as e:
        logging.getLogger("AnimeBot").warning(f"Healthcheck serverini yoqishda ogohlantirish: {e}")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger("AnimeBot")
    logger.info("Bot ishga tushirilmoqda...")

    # Healthcheck HTTP serverini ishga tushirish (Bulutli bepul hostinglar uchun)
    await start_healthcheck_server()

    # Ma'lumotlar bazasini tayyorlash
    await db.init_db()
    logger.info("Ma'lumotlar bazasi muvaffaqiyatli yuklandi.")

    # Bot va Dispatcher yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Routerni ro'yxatdan o'tkazish (admin birinchi, keyin user)
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Bot buyruqlarini sozlash
    await set_commands(bot)

    # Bot ma'lumotlarini olish
    try:
        me = await bot.get_me()
        print("=" * 50)
        print(f"  🤖 Anime Bot ishga tushdi: @{me.username} ({me.first_name})")
        print("  ✅ Token to'g'ri ishlamoqda va uzluksiz rejim yoqildi!")
        print("  🚀 Telegramdan botingizga /start bosing!")
        print("=" * 50)
    except Exception as e:
        logger.error(f"Telegramga ulanishda xatolik: {e}")

    # Uzluksiz polling sikli (Internet uzilsa yoki xato bo'lsa avtomattik qayta ulanadi)
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            break
        except TelegramConflictError:
            logger.critical("❌ XATOLIK: Bot boshqa konsol yoki serverda ham ishga tushirilgan! Telegram ziddiyati berdi. 10 soniyadan so'ng qayta urinib ko'riladi...")
            await asyncio.sleep(10)
        except (TelegramNetworkError, Exception) as e:
            logger.warning(f"⚠️ Internet yoki Telegram ulanishida uzilish: {e}. 5 soniyadan so'ng qayta ulanadi...")
            await asyncio.sleep(5)

    try:
        await bot.session.close()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nBot to'xtatildi.")

