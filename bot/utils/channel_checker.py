from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from bot.models import Channel


async def check_user_in_channel(bot: Bot, user_id: int, channel: Channel) -> bool:
    try:
        channel_ref = channel.channel_id if channel.channel_id.startswith("-") else f"@{channel.channel_username.lstrip('@')}"
        member = await bot.get_chat_member(chat_id=channel_ref, user_id=user_id)
        return member.status not in ("left", "kicked", "banned")
    except (TelegramBadRequest, TelegramForbiddenError, Exception):
        return True


async def get_missing_channels(bot: Bot, user_id: int, channels: list[Channel]) -> list[Channel]:
    missing = []
    for channel in channels:
        if not await check_user_in_channel(bot, user_id, channel):
            missing.append(channel)
    return missing
