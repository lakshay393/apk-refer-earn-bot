from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.db_service import get_or_create_user, get_all_channels, mark_user_verified, process_referral, get_user
from bot.keyboards.user_kb import join_channels_kb, recheck_channels_kb, main_menu_kb
from bot.utils.channel_checker import get_missing_channels
from bot.config import ADMIN_ID

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, bot: Bot):
    args = message.text.split(maxsplit=1)
    ref_id: int | None = None
    if len(args) > 1:
        try:
            ref_id = int(args[1])
            if ref_id == message.from_user.id:
                ref_id = None
        except ValueError:
            ref_id = None

    user, is_new = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        referred_by=ref_id if is_new_ref(ref_id) else None,
    )

    if user.blocked:
        await message.answer(
            "🚫 <b>Access Restricted</b>\n\n"
            "Your account has been suspended.\n"
            "Contact support if you believe this is a mistake.",
            parse_mode="HTML",
        )
        return

    channels = await get_all_channels(session)

    if not channels:
        await _send_welcome(message, user.verified, session, bot)
        return

    if user.verified:
        await message.answer(
            f"👋 <b>Welcome back, {message.from_user.first_name or 'there'}!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Use the menu below to navigate.",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
        return

    missing = await get_missing_channels(bot, message.from_user.id, channels)
    if not missing:
        await _complete_onboarding(message, session, bot, ref_id)
        return

    await message.answer(
        f"👋 <b>Welcome, {message.from_user.first_name or 'there'}!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔐 <b>One quick step before you begin</b>\n\n"
        f"Join <b>{len(channels)}</b> required channel(s) below, then tap <b>✅ I've Joined All Channels</b>.",
        parse_mode="HTML",
        reply_markup=join_channels_kb(channels),
    )


def is_new_ref(ref_id):
    return ref_id is not None


@router.callback_query(F.data == "check_join")
async def check_join(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    user = await get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("Please send /start first.", show_alert=True)
        return

    channels = await get_all_channels(session)
    if not channels:
        await _complete_onboarding_callback(callback, session, bot, user.referred_by)
        return

    missing = await get_missing_channels(bot, callback.from_user.id, channels)
    if missing:
        await callback.message.edit_text(
            "⚠️ <b>Channels Not Joined Yet</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"You still need to join <b>{len(missing)}</b> channel(s).\n"
            "Join them below and tap <b>🔄 Check Again</b>.",
            parse_mode="HTML",
            reply_markup=recheck_channels_kb(missing),
        )
        await callback.answer("❌ You haven't joined all channels yet.", show_alert=True)
        return

    await _complete_onboarding_callback(callback, session, bot, user.referred_by)


async def _complete_onboarding(message: Message, session: AsyncSession, bot: Bot, ref_id: int | None):
    await mark_user_verified(session, message.from_user.id)
    if ref_id:
        rewarded = await process_referral(session, ref_id, message.from_user.id)
        if rewarded:
            referrer = await get_user(session, ref_id)
            if referrer:
                try:
                    rwd = await _get_reward(session)
                    await bot.send_message(
                        ref_id,
                        f"🎉 <b>Referral Bonus!</b>\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"A new user joined via your link!\n\n"
                        f"💎 <b>+{rwd} Point(s)</b> added to your balance.\n"
                        f"🏆 Total Points: <b>{referrer.points}</b>",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

    await message.answer(
        "✅ <b>Verification Complete!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎉 Welcome aboard! You're all set.\n\n"
        "Use the menu below to get started.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


async def _complete_onboarding_callback(callback: CallbackQuery, session: AsyncSession, bot: Bot, ref_id: int | None):
    await mark_user_verified(session, callback.from_user.id)
    if ref_id:
        rewarded = await process_referral(session, ref_id, callback.from_user.id)
        if rewarded:
            referrer = await get_user(session, ref_id)
            if referrer:
                try:
                    rwd = await _get_reward(session)
                    await bot.send_message(
                        ref_id,
                        f"🎉 <b>Referral Bonus!</b>\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"A new user joined via your link!\n\n"
                        f"💎 <b>+{rwd} Point(s)</b> added to your balance.\n"
                        f"🏆 Total Points: <b>{referrer.points}</b>",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

    await callback.message.edit_text(
        "✅ <b>All Channels Joined!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎉 Welcome! You're all set to use the bot.",
        parse_mode="HTML",
    )
    await callback.message.answer(
        "🏠 <b>Main Menu</b>\n\nSelect an option below to get started.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


async def _send_welcome(message: Message, already_verified: bool, session: AsyncSession, bot: Bot):
    if not already_verified:
        await mark_user_verified(session, message.from_user.id)
    await message.answer(
        f"👋 <b>Welcome, {message.from_user.first_name or 'there'}!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎉 You're all set! Use the menu below to explore.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


async def _get_reward(session) -> int:
    from bot.services.db_service import get_reward_per_referral
    return await get_reward_per_referral(session)


@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    await callback.message.answer(
        "🏠 <b>Main Menu</b>",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
