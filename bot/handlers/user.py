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


# ── Access Guard ───────────────────────────────────────────────────────────────
# Returns (ok, user). Always calls callback.answer() before returning False for callbacks.

async def _guard(event, session: AsyncSession, bot: Bot):
    is_cb = isinstance(event, CallbackQuery)
    uid = event.from_user.id
    reply = event.message.answer if is_cb else event.answer

    user = await get_user(session, uid)
    if not user:
        await reply("⚡ Pehle /start bhejo!", parse_mode="HTML")
        if is_cb:
            await event.answer()
        return False, None

    if user.blocked:
        await reply(
            "🚫 <b>Account Suspended</b>\n\nContact support for help.",
            parse_mode="HTML",
        )
        if is_cb:
            await event.answer()
        return False, None

    if not user.verified:
        channels = await get_all_channels(session)
        if channels:
            missing = await get_missing_channels(bot, uid, channels)
            if missing:
                await reply(
                    "🔐 <b>Join Required Channels First</b>\n\n"
                    "You need to join our channels before using the bot.",
                    parse_mode="HTML",
                    reply_markup=join_channels_kb(channels),
                )
                if is_cb:
                    await event.answer()
                return False, None

    return True, user


# ── 👤 My Profile ──────────────────────────────────────────────────────────────

@router.message(F.text == "👤 My Profile")
async def show_profile(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _guard(message, session, bot)
    if not ok:
        return

    join_str = user.join_date.strftime("%d %b %Y") if user.join_date else "—"

    await message.answer(
        f"┌─────────────────────┐\n"
        f"      👤  <b>MY PROFILE</b>\n"
        f"└─────────────────────┘\n\n"
        f"🆔  <b>User ID</b>  →  <code>{user.telegram_id}</code>\n"
        f"📛  <b>Name</b>  →  {user.first_name or '—'}\n"
        f"🔗  <b>Username</b>  →  {'@' + user.username if user.username else '—'}\n"
        f"📅  <b>Joined</b>  →  {join_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎  <b>Points Balance</b>  →  <b>{user.points} pts</b>\n"
        f"👥  <b>Total Referrals</b>  →  <b>{user.referrals}</b>\n"
        f"✅  <b>Status</b>  →  {'🟢 Active' if not user.blocked else '🔴 Blocked'}",
        parse_mode="HTML",
    )


# ── 🎯 Refer & Earn ────────────────────────────────────────────────────────────

@router.message(F.text == "🎯 Refer & Earn")
async def refer_earn(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _guard(message, session, bot)
    if not ok:
        return

    bot_username = config.BOT_USERNAME
    if bot_username:
        ref_link = f"https://t.me/{bot_username}?start={user.telegram_id}"
    else:
        ref_link = "⚠️ Link unavailable — contact admin"

    reward = await get_reward_per_referral(session)

    await message.answer(
        f"┌─────────────────────┐\n"
        f"    🎯  <b>REFER &amp; EARN</b>\n"
        f"└─────────────────────┘\n\n"
        f"💸 <b>Earn {reward} point(s) per referral!</b>\n\n"
        f"<b>How it works:</b>\n"
        f"  1️⃣  Share your unique link\n"
        f"  2️⃣  Friend joins the bot\n"
        f"  3️⃣  You get <b>{reward} pt(s)</b> instantly ✅\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗  <b>Your Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥  <b>Friends Referred:</b>  {user.referrals}\n"
        f"💰  <b>Points Earned:</b>  {user.points} pts",
        parse_mode="HTML",
    )


# ── 📱 Get APK ─────────────────────────────────────────────────────────────────

@router.message(F.text == "📱 Get APK")
async def get_apk_menu(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _guard(message, session, bot)
    if not ok:
        return

    apks = await get_all_apks(session, active_only=True)
    if not apks:
        await message.answer(
            f"┌─────────────────────┐\n"
            f"    📭  <b>NO APKs AVAILABLE</b>\n"
            f"└─────────────────────┘\n\n"
            f"No APKs are available right now.\n"
            f"Check back soon! 🔄",
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"┌─────────────────────┐\n"
        f"    📱  <b>GET APK</b>\n"
        f"└─────────────────────┘\n\n"
        f"💰  <b>Your Balance:</b>  <b>{user.points} pts</b>\n\n"
        f"👇  Select an APK to redeem:",
        parse_mode="HTML",
        reply_markup=apk_list_kb(apks),
    )


@router.callback_query(F.data.startswith("apk_select_"))
async def apk_selected(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    ok, user = await _guard(callback, session, bot)
    if not ok:
        return

    try:
        apk_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid APK.", show_alert=True)
        return

    apk = await get_apk(session, apk_id)
    if not apk or not apk.is_active:
        await callback.answer("⚠️ This APK is no longer available.", show_alert=True)
        return

    can_afford = user.points >= apk.point_cost
    need_more = apk.point_cost - user.points
    delivery = "📎 APK File + Password" if apk.file_id else "🔑 Name + Password"

    if can_afford:
        status = "✅  <b>You can redeem this!</b>"
        footer = "Tap ✅ <b>Confirm</b> to redeem instantly."
    else:
        status = f"❌  <b>Need {need_more} more point(s)</b>"
        footer = "Refer friends to earn more points! 👥"

    await callback.message.edit_text(
        f"┌─────────────────────┐\n"
        f"   📦  <b>CONFIRM REDEMPTION</b>\n"
        f"└─────────────────────┘\n\n"
        f"🏷  <b>APK:</b>  {apk.name}\n"
        f"💎  <b>Cost:</b>  {apk.point_cost} pts\n"
        f"📦  <b>Delivery:</b>  {delivery}\n"
        f"💰  <b>Your Balance:</b>  {user.points} pts\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{status}\n\n"
        f"<i>{footer}</i>",
        parse_mode="HTML",
        reply_markup=apk_confirm_kb(apk_id) if can_afford else back_to_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("apk_confirm_"))
async def apk_confirm(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    ok, user = await _guard(callback, session, bot)
    if not ok:
        return

    try:
        apk_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid request.", show_alert=True)
        return

    success, result = await redeem_apk(session, callback.from_user.id, apk_id)
    if not success:
        await callback.answer(f"❌ {result}", show_alert=True)
        return

    parts = result.split("|", 2)
    apk_name = parts[0]
    apk_password = parts[1]
    file_id = parts[2] if len(parts) > 2 else ""

    fresh = await get_user(session, callback.from_user.id)
    remaining = fresh.points if fresh else 0

    await callback.message.edit_text(
        f"┌─────────────────────┐\n"
        f"  🎉  <b>REDEMPTION SUCCESSFUL!</b>\n"
        f"└─────────────────────┘\n\n"
        f"📱  <b>APK:</b>  {apk_name}\n"
        f"🔑  <b>Password:</b>  <code>{apk_password}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰  <b>Remaining Balance:</b>  {remaining} pts\n\n"
        f"📸  <i>Screenshot karein — password ek baar hi dikhega!</i>",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb(),
    )

    if file_id:
        try:
            await bot.send_document(
                callback.from_user.id,
                document=file_id,
                caption=(
                    f"📱  <b>{apk_name}</b>\n\n"
                    f"🔑  <b>Password:</b>  <code>{apk_password}</code>\n\n"
                    f"<i>Saved for you!</i>"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

    await callback.answer("🎉 Redeemed!", show_alert=False)


@router.callback_query(F.data == "apk_cancel")
async def apk_cancel(callback: CallbackQuery):
    await callback.message.edit_text(
        "❌  <b>Cancelled</b>\n\n"
        "No points were deducted. Come back anytime!",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


# ── 📜 History ─────────────────────────────────────────────────────────────────

@router.message(F.text == "📜 History")
async def show_history(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _guard(message, session, bot)
    if not ok:
        return

    redemptions = await get_user_redemptions(session, user.telegram_id)
    if not redemptions:
        await message.answer(
            f"┌─────────────────────┐\n"
            f"   📭  <b>NO HISTORY YET</b>\n"
            f"└─────────────────────┘\n\n"
            f"You haven't redeemed any APKs yet.\n\n"
            f"Refer friends → earn points → get APKs! 🚀",
            parse_mode="HTML",
        )
        return

    lines = [
        f"┌─────────────────────┐\n"
        f"   📜  <b>REDEMPTION HISTORY</b>\n"
        f"└─────────────────────┘\n"
    ]
    for i, r in enumerate(redemptions[:15], 1):
        date_str = r.date.strftime("%d %b %Y") if r.date else "—"
        # Use snapshot name (safe from async lazy-load crash)
        name = r.apk_name_snapshot or (r.apk.name if r.apk else "Deleted APK")
        lines.append(f"{i}.  📦 <b>{name}</b>  ·  {r.points_spent} pts  ·  {date_str}")

    if len(redemptions) > 15:
        lines.append(f"\n<i>Showing 15 of {len(redemptions)} total redemptions.</i>")

    await message.answer("\n".join(lines), parse_mode="HTML")


# ── 💬 Support ─────────────────────────────────────────────────────────────────

@router.message(F.text == "💬 Support")
async def support(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _guard(message, session, bot)
    if not ok:
        return

    await message.answer(
        f"┌─────────────────────┐\n"
        f"      💬  <b>SUPPORT</b>\n"
        f"└─────────────────────┘\n\n"
        f"Need help? We're here for you! 💪\n\n"
        f"Tap the button below to contact our support team.",
        parse_mode="HTML",
        reply_markup=support_kb(),
    )


# ── Back to Menu ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    await callback.message.answer(
        "🏠  <b>Main Menu</b>\n\nSelect an option below:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
