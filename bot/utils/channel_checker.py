import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from bot.models import Channel


async def check_user_in_channel(bot: Bot, user_id: int, channel: Channel) -> bool:
    try:
        ref = (
            channel.channel_id
            if channel.channel_id and channel.channel_id.startswith("-")
            else f"@{channel.channel_username.lstrip('@')}"
        )
        member = await bot.get_chat_member(chat_id=ref, user_id=user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return True  # Give benefit of doubt on API errors


async def get_missing_channels(bot: Bot, user_id: int, channels: list[Channel]) -> list[Channel]:
    if not channels:
        return []
    # Check ALL channels in parallel — much faster than sequential
    results = await asyncio.gather(
        *[check_user_in_channel(bot, user_id, ch) for ch in channels],
        return_exceptions=True,
    )
    return [ch for ch, joined in zip(channels, results) if joined is not True]
