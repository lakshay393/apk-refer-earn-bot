from aiogram import Bot
from bot.config import ADMIN_ID, NOTIFY_ID


async def notify(bot: Bot, text: str) -> None:
    for uid in {ADMIN_ID, NOTIFY_ID}:
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
        except Exception:
            pass
