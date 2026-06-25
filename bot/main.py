import asyncio
import logging
import os
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

import bot.config as config
from bot.database import engine, Base
from bot.middlewares.db_middleware import DbSessionMiddleware
from bot.handlers import start, user, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PING_INTERVAL = 10 * 60  # 10 minutes


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")


async def start_webserver():
    """Minimal web server for Render health checks & keep-alive."""
    port = int(os.getenv("PORT", "8080"))

    async def health(request):
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/healthz", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server running on port {port}")


async def keep_alive():
    """Ping self every 10 min to prevent Render free tier sleep."""
    if not config.RENDER_URL:
        logger.info("RENDER_URL not set — keep-alive disabled.")
        return

    base = config.RENDER_URL if config.RENDER_URL.startswith("http") else f"https://{config.RENDER_URL}"
    ping_url = base.rstrip("/") + "/healthz"
    logger.info(f"Keep-alive started → pinging {ping_url} every 10 min.")

    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(PING_INTERVAL)
            try:
                async with session.get(ping_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    logger.info(f"Keep-alive ping OK ({resp.status})")
            except Exception as e:
                logger.warning(f"Keep-alive ping failed: {e}")


async def main():
    await create_tables()
    await start_webserver()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware())

    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(user.router)

    try:
        bot_info = await bot.get_me()
        # Auto-set username globally — no env var needed
        config.BOT_USERNAME = bot_info.username or ""
        logger.info(f"Starting bot: @{config.BOT_USERNAME}")
        await bot.send_message(
            config.ADMIN_ID,
            f"🤖 <b>Bot Started!</b>\n\n"
            f"@{config.BOT_USERNAME} is now online.\n"
            f"📱 APK Refer &amp; Earn Bot",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Could not send startup message: {e}")

    asyncio.create_task(keep_alive())

    logger.info("Polling started.")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
