from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.db_service import (
    get_or_create_user, get_all_channels, mark_user_verified,
    process_referral, get_user, get_reward_per_referral
)
from bot.keyboards.user_kb import join_channels_kb, recheck_channels_kb, main_menu_kb
from bot.utils.channel_checker import get_missing_channels

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

    # NOTE: ref_id is passed here; get_or_create_user only sets it for NEW users
    user, is_new = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        referred_by=ref_id,  # db_service ignores this for existing users
    )

    if user.blocked:
        await message.answer(
            "🚫  <b>Account Suspended</b>\n\n"
            "Your account has been suspended.\n"
            "Contact support if you think this is a mistake.",
            parse_mode="HTML",
        )
        return

    channels = await get_all_channels(session)

    # No channels configured — skip force join, verify immediately
    if not channels:
        await _send_welcome(message, user, session, bot, ref_id if is_new else None)
        return

    # Already verified — just show menu
    if user.verified:
        name = message.from_user.first_name or "there"
        await message.answer(
            f"👋  <b>Welcome back, {name}!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Use the menu below to navigate.",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
        return

    # New/unverified user — check channels
    missing = await get_missing_channels(bot, message.from_user.id, channels)
    if not missing:
        # Already in all channels — complete onboarding immediately
        await _complete_onboarding(message, session, bot, ref_id if is_new else None)
        return

    name = message.from_user.first_name or "there"
    await message.answer(
        f"👋  <b>Welcome, {name}!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔐  <b>Step 1 of 1 — Join our channel(s)</b>\n\n"
        f"Join the {len(channels)} channel(s) below,\n"
        f"then tap  <b>✅ I've Joined All</b>  to continue.",
        parse_mode="HTML",
        reply_markup=join_channels_kb(channels),
    )


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
            f"⚠️  <b>Not Joined Yet</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"You still need to join <b>{len(missing)}</b> channel(s).\n"
            f"Join them then tap  <b>🔄 Check Again</b>.",
            parse_mode="HTML",
            reply_markup=recheck_channels_kb(missing),
        )
        await callback.answer("❌ Still not joined all channels.", show_alert=True)
        return

    await _complete_onboarding_callback(callback, session, bot, user.referred_by)


async def _complete_onboarding(message: Message, session: AsyncSession, bot: Bot, ref_id: int | None):
    await mark_user_verified(session, message.from_user.id)
    await _award_referral(session, bot, ref_id, message.from_user.id)
    await message.answer(
        "✅  <b>All done! You're verified!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎉  Welcome aboard! Use the menu below.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


async def _complete_onboarding_callback(callback: CallbackQuery, session: AsyncSession, bot: Bot, ref_id: int | None):
    await mark_user_verified(session, callback.from_user.id)
    await _award_referral(session, bot, ref_id, callback.from_user.id)
    try:
        await callback.message.edit_text(
            "✅  <b>Channels Joined — Verified!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎉  Welcome! You're all set.",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.message.answer(
        "🏠  <b>Main Menu</b>\n\nSelect an option below:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


async def _send_welcome(message: Message, user, session: AsyncSession, bot: Bot, ref_id: int | None):
    if not user.verified:
        await mark_user_verified(session, message.from_user.id)
        await _award_referral(session, bot, ref_id, message.from_user.id)
    name = message.from_user.first_name or "there"
    await message.answer(
        f"👋  <b>Welcome, {name}!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎉  You're all set! Explore using the menu below.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


async def _award_referral(session: AsyncSession, bot: Bot, ref_id: int | None, new_user_id: int):
    if not ref_id:
        return
    rewarded = await process_referral(session, ref_id, new_user_id)
    if not rewarded:
        return
    referrer = await get_user(session, ref_id)
    if not referrer:
        return
    try:
        rwd = await get_reward_per_referral(session)
        await bot.send_message(
            ref_id,
            f"🎉  <b>Referral Bonus!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Someone joined via your link!\n\n"
            f"💎  <b>+{rwd} Point(s)</b> added to your account.\n"
            f"🏆  <b>New Balance:</b>  {referrer.points} pts",
            parse_mode="HTML",
        )
    except Exception:
        pass
