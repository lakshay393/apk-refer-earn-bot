import bot.config as config
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.db_service import (
    get_user, get_all_apks, get_apk, redeem_apk,
    get_user_redemptions, get_all_channels, get_reward_per_referral
)
from bot.keyboards.user_kb import (
    main_menu_kb, apk_list_kb, apk_confirm_kb, back_to_menu_kb, support_kb, join_channels_kb
)
from bot.utils.channel_checker import get_missing_channels

router = Router()


async def _check_access(message_or_callback, session: AsyncSession, bot: Bot) -> tuple[bool, object | None]:
    if isinstance(message_or_callback, Message):
        uid = message_or_callback.from_user.id
        send = message_or_callback.answer
    else:
        uid = message_or_callback.from_user.id
        send = message_or_callback.message.answer

    user = await get_user(session, uid)
    if not user:
        await send("Please send /start to begin.", parse_mode="HTML")
        return False, None
    if user.blocked:
        await send("🚫 <b>Your account is suspended.</b>", parse_mode="HTML")
        return False, None

    if not user.verified:
        channels = await get_all_channels(session)
        if channels:
            missing = await get_missing_channels(bot, uid, channels)
            if missing:
                await send(
                    "⚠️ <b>Join Required Channels First</b>\n\n"
                    "Please join all required channels before using the bot.",
                    parse_mode="HTML",
                    reply_markup=join_channels_kb(channels),
                )
                return False, None
    return True, user


# ── Profile ────────────────────────────────────────────────────────────────────

@router.message(F.text == "👤 My Profile")
async def show_profile(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(message, session, bot)
    if not ok:
        return

    bot_username = config.BOT_USERNAME
    ref_link = f"https://t.me/{bot_username}?start={user.telegram_id}" if bot_username else "⚠️ Contact admin"
    join_str = user.join_date.strftime("%d %b %Y") if user.join_date else "N/A"

    await message.answer(
        f"👤 <b>Your Profile</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>ID:</b> <code>{user.telegram_id}</code>\n"
        f"👤 <b>Name:</b> {user.first_name or 'N/A'}\n"
        f"📅 <b>Joined:</b> {join_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>Points:</b> {user.points}\n"
        f"👥 <b>Referrals:</b> {user.referrals}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>Your Refer Link:</b>\n"
        f"<code>{ref_link}</code>",
        parse_mode="HTML",
    )


# ── Refer & Earn ───────────────────────────────────────────────────────────────

@router.message(F.text == "🎯 Refer & Earn")
async def refer_earn(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(message, session, bot)
    if not ok:
        return

    bot_username = config.BOT_USERNAME
    ref_link = f"https://t.me/{bot_username}?start={user.telegram_id}" if bot_username else "⚠️ Contact admin"
    reward = await get_reward_per_referral(session)

    await message.answer(
        f"🎯 <b>Refer & Earn</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>Earn {reward} Point(s)</b> for every friend you refer!\n\n"
        f"📌 <b>How it works:</b>\n"
        f"  1️⃣ Share your unique referral link\n"
        f"  2️⃣ Friend joins &amp; completes setup\n"
        f"  3️⃣ You earn <b>{reward} point(s)</b> instantly\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>Your Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 <b>Total Referrals:</b> {user.referrals}\n"
        f"💰 <b>Points Balance:</b> {user.points}",
        parse_mode="HTML",
    )


# ── Get APK ────────────────────────────────────────────────────────────────────

@router.message(F.text == "📱 Get APK")
async def get_apk_menu(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(message, session, bot)
    if not ok:
        return

    apks = await get_all_apks(session, active_only=True)
    if not apks:
        await message.answer(
            "📭 <b>No APKs Available</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "There are no APKs available at the moment.\n"
            "Check back soon!",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb(),
        )
        return

    await message.answer(
        f"📱 <b>Available APKs</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Your Balance:</b> {user.points} pts\n\n"
        f"Select an APK to redeem:",
        parse_mode="HTML",
        reply_markup=apk_list_kb(apks),
    )


@router.callback_query(F.data.startswith("apk_select_"))
async def apk_selected(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(callback, session, bot)
    if not ok:
        await callback.answer()
        return

    apk_id = int(callback.data.split("_")[-1])
    apk = await get_apk(session, apk_id)
    if not apk or not apk.is_active:
        await callback.answer("⚠️ This APK is no longer available.", show_alert=True)
        return

    can_afford = user.points >= apk.point_cost
    status_line = (
        f"✅ <b>You have enough points!</b>"
        if can_afford
        else f"❌ <b>Insufficient points</b> (need {apk.point_cost - user.points} more)"
    )

    await callback.message.edit_text(
        f"📦 <b>Confirm Redemption</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷 <b>APK:</b> {apk.name}\n"
        f"💎 <b>Cost:</b> {apk.point_cost} pts\n"
        f"💰 <b>Your Balance:</b> {user.points} pts\n\n"
        f"{status_line}\n\n"
        f"{'Tap ✅ Confirm to redeem instantly.' if can_afford else 'Refer more friends to earn points.'}",
        parse_mode="HTML",
        reply_markup=apk_confirm_kb(apk_id) if can_afford else back_to_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("apk_confirm_"))
async def apk_confirm(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(callback, session, bot)
    if not ok:
        await callback.answer()
        return

    apk_id = int(callback.data.split("_")[-1])
    success, result = await redeem_apk(session, callback.from_user.id, apk_id)

    if not success:
        await callback.answer(f"❌ {result}", show_alert=True)
        return

    apk_name, apk_password = result.split("|", 1)

    # Fetch fresh user to get updated points after deduction
    fresh_user = await get_user(session, callback.from_user.id)
    remaining = fresh_user.points if fresh_user else 0

    await callback.message.edit_text(
        f"🎉 <b>Redemption Successful!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>APK Name:</b> {apk_name}\n"
        f"🔑 <b>Password:</b> <code>{apk_password}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Remaining Balance:</b> {remaining} pts\n\n"
        f"<i>📸 Screenshot this message — password shown only once!</i>",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer("✅ APK redeemed successfully!")


@router.callback_query(F.data == "apk_cancel")
async def apk_cancel(callback: CallbackQuery):
    await callback.message.edit_text(
        "❌ <b>Redemption Cancelled</b>\n\nNo points were deducted.",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


# ── History ────────────────────────────────────────────────────────────────────

@router.message(F.text == "📜 History")
async def show_history(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(message, session, bot)
    if not ok:
        return

    redemptions = await get_user_redemptions(session, user.telegram_id)
    if not redemptions:
        await message.answer(
            "📭 <b>No Redemption History</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "You haven't redeemed any APKs yet.\n"
            "Refer friends to earn points and get started!",
            parse_mode="HTML",
        )
        return

    lines = [f"📜 <b>Redemption History</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"]
    for i, r in enumerate(redemptions[:15], 1):
        date_str = r.date.strftime("%d %b %Y") if r.date else "N/A"
        apk_name = r.apk.name if r.apk else "Deleted APK"
        lines.append(f"{i}. 📦 <b>{apk_name}</b> — {r.points_spent} pts — {date_str}")

    if len(redemptions) > 15:
        lines.append(f"\n<i>Showing last 15 of {len(redemptions)} redemptions.</i>")

    await message.answer("\n".join(lines), parse_mode="HTML")


# ── Support ────────────────────────────────────────────────────────────────────

@router.message(F.text == "💬 Support")
async def support(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(message, session, bot)
    if not ok:
        return

    await message.answer(
        "💬 <b>Support</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Need help? Our support team is here for you.\n\n"
        "📩 Tap the button below to reach us directly.",
        parse_mode="HTML",
        reply_markup=support_kb(),
    )
