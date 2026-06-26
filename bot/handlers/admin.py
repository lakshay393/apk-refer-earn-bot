from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, Document
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import ADMIN_ID
from bot.services.db_service import (
    get_stats, get_all_users, get_user, block_user, unblock_user,
    get_all_channels, add_channel, remove_channel,
    get_all_apks, add_apk, remove_apk, set_all_apk_points,
    get_setting, set_setting, get_reward_per_referral
)
from bot.keyboards.admin_kb import (
    admin_panel_kb, admin_channels_kb, admin_apk_kb,
    admin_remove_channels_kb, admin_remove_apk_kb,
    admin_back_kb, admin_broadcast_type_kb, admin_skip_kb
)

router = Router()


class AdminStates(StatesGroup):
    waiting_channel = State()
    waiting_apk_name = State()
    waiting_apk_password = State()
    waiting_apk_points = State()
    waiting_apk_file = State()
    waiting_set_all_pts = State()
    waiting_broadcast_msg = State()
    waiting_broadcast_channel_msg = State()


# ── Admin Entry ────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    stats = await get_stats(session)
    await message.answer(
        f"🛡 <b>Admin Panel</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b> {stats['total_users']}\n"
        f"✅ <b>Verified:</b> {stats['verified_users']}\n"
        f"🎯 <b>Total Referrals:</b> {stats['total_referrals']}\n"
        f"📱 <b>APK Redemptions:</b> {stats['total_redemptions']}\n"
        f"📦 <b>Active APKs:</b> {stats['active_apks']}",
        parse_mode="HTML",
        reply_markup=admin_panel_kb(),
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await state.clear()
    stats = await get_stats(session)
    await callback.message.edit_text(
        f"🛡 <b>Admin Panel</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b> {stats['total_users']}\n"
        f"✅ <b>Verified:</b> {stats['verified_users']}\n"
        f"🎯 <b>Total Referrals:</b> {stats['total_referrals']}\n"
        f"📱 <b>APK Redemptions:</b> {stats['total_redemptions']}\n"
        f"📦 <b>Active APKs:</b> {stats['active_apks']}",
        parse_mode="HTML",
        reply_markup=admin_panel_kb(),
    )
    await callback.answer()


# ── Stats ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    stats = await get_stats(session)
    reward = await get_reward_per_referral(session)
    await callback.message.edit_text(
        f"📊 <b>Statistics</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b> {stats['total_users']}\n"
        f"✅ <b>Verified Users:</b> {stats['verified_users']}\n"
        f"🎯 <b>Total Referrals:</b> {stats['total_referrals']}\n"
        f"📱 <b>APK Redemptions:</b> {stats['total_redemptions']}\n"
        f"📦 <b>Active APKs:</b> {stats['active_apks']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>Reward/Referral:</b> {reward} pt(s)",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


# ── Channels ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_channels")
async def admin_channels(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.message.edit_text(
        "📡 <b>Channel Management</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Manage force-join channels here.",
        parse_mode="HTML",
        reply_markup=admin_channels_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_channel")
async def admin_add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_channel)
    await callback.message.edit_text(
        "📡 <b>Add Channel</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the channel username or ID.\n\n"
        "<b>Examples:</b>\n"
        "• <code>@mychannel</code>\n"
        "• <code>-1001234567890</code>\n\n"
        "<i>Make sure the bot is admin in the channel first!</i>",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_channel)
async def admin_add_channel_receive(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    raw = message.text.strip() if message.text else ""
    if not raw:
        await message.answer("❌ Please send a valid channel username or ID.", parse_mode="HTML")
        return
    try:
        if raw.lstrip("-").isdigit():
            chat = await bot.get_chat(int(raw))
            channel_id = str(chat.id)
            username = (chat.username or raw).lstrip("@")
        else:
            username = raw.lstrip("@")
            chat = await bot.get_chat(f"@{username}")
            channel_id = str(chat.id)
            username = chat.username or username
        title = chat.title or username
        await add_channel(session, channel_id, username, title)
        await message.answer(
            f"✅ <b>Channel Added!</b>\n\n"
            f"📢 <b>{title}</b> (@{username})\n"
            f"🆔 ID: <code>{channel_id}</code>",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
    except Exception as e:
        await message.answer(
            f"❌ <b>Failed to add channel</b>\n\n"
            f"<code>{e}</code>\n\n"
            f"<i>Make sure the bot is an admin in the channel.</i>",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )


@router.callback_query(F.data == "admin_remove_channel")
async def admin_remove_channel_prompt(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    channels = await get_all_channels(session)
    if not channels:
        await callback.answer("⚠️ No channels added yet.", show_alert=True)
        return
    await callback.message.edit_text(
        "🗑 <b>Remove Channel</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select a channel to remove:",
        parse_mode="HTML",
        reply_markup=admin_remove_channels_kb(channels),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_del_ch_"))
async def admin_del_channel(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    ch_id = int(callback.data.split("_")[-1])
    await remove_channel(session, ch_id)
    await callback.answer("✅ Channel removed.", show_alert=True)
    await callback.message.edit_text(
        "📡 <b>Channel Management</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Channel removed successfully.",
        parse_mode="HTML",
        reply_markup=admin_channels_kb(),
    )


@router.callback_query(F.data == "admin_list_channels")
async def admin_list_channels(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    channels = await get_all_channels(session)
    if not channels:
        await callback.answer("No channels added yet.", show_alert=True)
        return
    lines = ["📋 <b>Force-Join Channels</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"]
    for ch in channels:
        lines.append(f"• <b>{ch.channel_title or ch.channel_username}</b> | @{ch.channel_username}")
    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=admin_channels_kb()
    )
    await callback.answer()


# ── APK Manager ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_apks")
async def admin_apks(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.message.edit_text(
        "📱 <b>APK Manager</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Manage available APKs and their prices.",
        parse_mode="HTML",
        reply_markup=admin_apk_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_apk")
async def admin_add_apk_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_apk_name)
    await callback.message.edit_text(
        "📱 <b>Add New APK — Step 1/4</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the <b>APK Name</b>:\n"
        "<i>(e.g. Netflix Premium, Spotify Pro)</i>",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_apk_name)
async def admin_apk_name_receive(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.text:
        await message.answer("❌ Please send the APK name as text.", parse_mode="HTML")
        return
    await state.update_data(apk_name=message.text.strip())
    await state.set_state(AdminStates.waiting_apk_password)
    await message.answer(
        "📱 <b>Add New APK — Step 2/4</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>Name:</b> {message.text.strip()}\n\n"
        "Now send the <b>Password</b>:\n"
        "<i>(This will be auto-delivered to users on redemption)</i>",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


@router.message(AdminStates.waiting_apk_password)
async def admin_apk_password_receive(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.text:
        await message.answer("❌ Please send the password as text.", parse_mode="HTML")
        return
    await state.update_data(apk_password=message.text.strip())
    await state.set_state(AdminStates.waiting_apk_points)
    data = await state.get_data()
    await message.answer(
        "📱 <b>Add New APK — Step 3/4</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>Name:</b> {data.get('apk_name')}\n"
        f"✅ <b>Password:</b> Set ✓\n\n"
        "Now send the <b>Point Cost</b> (number):\n"
        "<i>(e.g. 5 — users need this many points to redeem)</i>",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


@router.message(AdminStates.waiting_apk_points)
async def admin_apk_points_receive(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.text:
        await message.answer("❌ Please send a number.", parse_mode="HTML")
        return
    try:
        pts = int(message.text.strip())
        if pts <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Please send a valid positive number.", parse_mode="HTML")
        return
    await state.update_data(apk_points=pts)
    await state.set_state(AdminStates.waiting_apk_file)
    data = await state.get_data()
    await message.answer(
        "📱 <b>Add New APK — Step 4/4</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>Name:</b> {data.get('apk_name')}\n"
        f"✅ <b>Password:</b> Set ✓\n"
        f"✅ <b>Cost:</b> {pts} pts\n\n"
        "Now <b>upload the APK file</b> (send as document):\n"
        "<i>Users will receive this file when they redeem.</i>\n\n"
        "Or tap <b>⏭ Skip</b> if you only want to deliver name + password.",
        parse_mode="HTML",
        reply_markup=admin_skip_kb(),
    )


@router.message(AdminStates.waiting_apk_file, F.document)
async def admin_apk_file_receive(message: Message, state: FSMContext, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    await state.clear()
    file_id = message.document.file_id
    apk = await add_apk(
        session,
        data["apk_name"],
        data["apk_password"],
        data["apk_points"],
        file_id=file_id,
    )
    await message.answer(
        f"✅ <b>APK Added Successfully!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>Name:</b> {apk.name}\n"
        f"🔑 <b>Password:</b> Set ✓\n"
        f"📎 <b>File:</b> Uploaded ✓\n"
        f"💎 <b>Cost:</b> {apk.point_cost} pts\n\n"
        f"<i>Users will receive the file + password on redemption.</i>",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


@router.callback_query(F.data == "admin_skip_file", AdminStates.waiting_apk_file)
async def admin_apk_skip_file(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    data = await state.get_data()
    await state.clear()
    apk = await add_apk(
        session,
        data["apk_name"],
        data["apk_password"],
        data["apk_points"],
        file_id=None,
    )
    await callback.message.edit_text(
        f"✅ <b>APK Added (No File)</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>Name:</b> {apk.name}\n"
        f"🔑 <b>Password:</b> Set ✓\n"
        f"📎 <b>File:</b> None (name+password only)\n"
        f"💎 <b>Cost:</b> {apk.point_cost} pts",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_apk_file)
async def admin_apk_file_wrong(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "⚠️ Please upload the APK as a <b>document/file</b>, or tap <b>⏭ Skip</b>.",
        parse_mode="HTML",
        reply_markup=admin_skip_kb(),
    )


@router.callback_query(F.data == "admin_remove_apk")
async def admin_remove_apk_prompt(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    apks = await get_all_apks(session)
    if not apks:
        await callback.answer("⚠️ No APKs added yet.", show_alert=True)
        return
    await callback.message.edit_text(
        "🗑 <b>Remove APK</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select an APK to remove:",
        parse_mode="HTML",
        reply_markup=admin_remove_apk_kb(apks),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_del_apk_"))
async def admin_del_apk(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    apk_id = int(callback.data.split("_")[-1])
    removed = await remove_apk(session, apk_id)
    if removed:
        await callback.answer("✅ APK removed successfully.", show_alert=True)
    else:
        await callback.answer("⚠️ APK not found.", show_alert=True)
    await callback.message.edit_text(
        "📱 <b>APK Manager</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "APK removed successfully.",
        parse_mode="HTML",
        reply_markup=admin_apk_kb(),
    )


@router.callback_query(F.data == "admin_list_apks")
async def admin_list_apks(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    apks = await get_all_apks(session)
    if not apks:
        await callback.answer("No APKs added yet.", show_alert=True)
        return
    lines = ["📋 <b>All APKs</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"]
    for apk in apks:
        file_status = "📎 File" if apk.file_id else "📝 Name+Pass only"
        lines.append(f"• <b>{apk.name}</b> — 💎 {apk.point_cost} pts — {file_status}")
    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=admin_apk_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_set_all_apk_pts")
async def admin_set_all_apk_pts_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_set_all_pts)
    await callback.message.edit_text(
        "🔁 <b>Set Same Points for All APKs</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the <b>point cost</b> to apply to all APKs:\n"
        "<i>(e.g. 5)</i>",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_set_all_pts)
async def admin_set_all_apk_pts_receive(message: Message, state: FSMContext, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        pts = int(message.text.strip())
        if pts <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("❌ Please send a valid positive number.", parse_mode="HTML")
        return
    await state.clear()
    count = await set_all_apk_points(session, pts)
    await message.answer(
        f"✅ <b>Updated {count} APK(s)!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 All APKs now cost <b>{pts} pt(s)</b> to redeem.",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


# ── Point Settings ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_points")
async def admin_points(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    reward = await get_reward_per_referral(session)
    await callback.message.edit_text(
        f"⚙️ <b>Point Settings</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>Referral Reward:</b> {reward} pt(s)\n\n"
        f"<b>Command:</b>\n"
        f"<code>/setreward NUMBER</code> — set points per referral",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(Command("setreward"))
async def cmd_setreward(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: <code>/setreward NUMBER</code>", parse_mode="HTML")
        return
    try:
        val = int(parts[1])
        if val <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Please provide a positive number.", parse_mode="HTML")
        return
    await set_setting(session, "reward_per_referral", str(val))
    await message.answer(f"✅ <b>Referral reward set to {val} pt(s)</b>", parse_mode="HTML")


# ── Users ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.message.edit_text(
        "👥 <b>User Management</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Available Commands:</b>\n\n"
        "<code>/block USER_ID</code> — block a user\n"
        "<code>/unblock USER_ID</code> — unblock a user\n"
        "<code>/addpts USER_ID AMOUNT</code> — add points\n"
        "<code>/rmpts USER_ID AMOUNT</code> — remove points\n"
        "<code>/userinfo USER_ID</code> — view user details",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(Command("block"))
async def cmd_block(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: <code>/block USER_ID</code>", parse_mode="HTML")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid user ID.", parse_mode="HTML")
        return
    await block_user(session, uid)
    await message.answer(f"🚫 User <code>{uid}</code> has been blocked.", parse_mode="HTML")


@router.message(Command("unblock"))
async def cmd_unblock(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: <code>/unblock USER_ID</code>", parse_mode="HTML")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid user ID.", parse_mode="HTML")
        return
    await unblock_user(session, uid)
    await message.answer(f"✅ User <code>{uid}</code> has been unblocked.", parse_mode="HTML")


@router.message(Command("addpts"))
async def cmd_addpts(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: <code>/addpts USER_ID AMOUNT</code>", parse_mode="HTML")
        return
    try:
        uid, amount = int(parts[1]), int(parts[2])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Invalid parameters.", parse_mode="HTML")
        return
    user = await get_user(session, uid)
    if not user:
        await message.answer("❌ User not found.", parse_mode="HTML")
        return
    user.points += amount
    await session.commit()
    await message.answer(
        f"✅ Added <b>{amount}</b> pts to <code>{uid}</code>\n"
        f"💰 New balance: <b>{user.points}</b>",
        parse_mode="HTML",
    )


@router.message(Command("rmpts"))
async def cmd_rmpts(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: <code>/rmpts USER_ID AMOUNT</code>", parse_mode="HTML")
        return
    try:
        uid, amount = int(parts[1]), int(parts[2])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Invalid parameters.", parse_mode="HTML")
        return
    user = await get_user(session, uid)
    if not user:
        await message.answer("❌ User not found.", parse_mode="HTML")
        return
    user.points = max(0, user.points - amount)
    await session.commit()
    await message.answer(
        f"✅ Removed <b>{amount}</b> pts from <code>{uid}</code>\n"
        f"💰 New balance: <b>{user.points}</b>",
        parse_mode="HTML",
    )


@router.message(Command("userinfo"))
async def cmd_userinfo(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: <code>/userinfo USER_ID</code>", parse_mode="HTML")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid user ID.", parse_mode="HTML")
        return
    user = await get_user(session, uid)
    if not user:
        await message.answer("❌ User not found.", parse_mode="HTML")
        return
    join_str = user.join_date.strftime("%d %b %Y %H:%M") if user.join_date else "N/A"
    await message.answer(
        f"👤 <b>User Info</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>ID:</b> <code>{user.telegram_id}</code>\n"
        f"👤 <b>Name:</b> {user.first_name or 'N/A'}\n"
        f"🔗 <b>Username:</b> @{user.username or 'N/A'}\n"
        f"💎 <b>Points:</b> {user.points}\n"
        f"👥 <b>Referrals:</b> {user.referrals}\n"
        f"✅ <b>Verified:</b> {'Yes' if user.verified else 'No'}\n"
        f"🚫 <b>Blocked:</b> {'Yes' if user.blocked else 'No'}\n"
        f"📅 <b>Joined:</b> {join_str}",
        parse_mode="HTML",
    )


# ── Broadcast ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "📢 <b>Broadcast</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choose broadcast target:",
        parse_mode="HTML",
        reply_markup=admin_broadcast_type_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_bc_channels")
async def admin_bc_channels_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    channels = await get_all_channels(session)
    if not channels:
        await callback.answer("⚠️ No channels added yet!", show_alert=True)
        return
    ch_list = "\n".join(f"• {ch.channel_title or '@' + ch.channel_username}" for ch in channels)
    await state.set_state(AdminStates.waiting_broadcast_channel_msg)
    await callback.message.edit_text(
        f"📢 <b>Broadcast to Channels ({len(channels)})</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ch_list}\n\n"
        "Send the message to broadcast:",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_channel_msg)
async def admin_broadcast_channel_send(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    channels = await get_all_channels(session)
    if not channels:
        await message.answer("❌ No channels found.", parse_mode="HTML")
        return
    status_msg = await message.answer(f"⏳ Sending to {len(channels)} channel(s)...", parse_mode="HTML")
    sent, failed = [], []
    for ch in channels:
        cid = ch.channel_id
        chat_ref = int(cid) if cid and cid.lstrip("-").isdigit() else f"@{(cid or ch.channel_username).lstrip('@')}"
        try:
            await bot.copy_message(chat_ref, message.chat.id, message.message_id)
            sent.append(ch.channel_title or ch.channel_username)
        except Exception as e:
            failed.append(f"{ch.channel_title or ch.channel_username} ({e.__class__.__name__})")
    lines = ["📢 <b>Broadcast Complete!</b>\n"]
    if sent:
        lines.append(f"✅ <b>Sent ({len(sent)}):</b>")
        lines += [f"  • {n}" for n in sent]
    if failed:
        lines.append(f"\n❌ <b>Failed ({len(failed)}):</b>")
        lines += [f"  • {n}" for n in failed]
    try:
        await status_msg.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=admin_back_kb())
    except Exception:
        await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_back_kb())


@router.callback_query(F.data == "admin_bc_users")
async def admin_bc_users_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_broadcast_msg)
    await callback.message.edit_text(
        "👥 <b>Broadcast to Users</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the message to broadcast to all verified users:",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_msg)
async def admin_broadcast_send(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    users = await get_all_users(session)
    verified = [u for u in users if u.verified and not u.blocked]
    status_msg = await message.answer(f"⏳ Sending to {len(verified)} user(s)...", parse_mode="HTML")
    sent = failed = 0
    for u in verified:
        try:
            await bot.copy_message(u.telegram_id, message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1
    try:
        await status_msg.edit_text(
            f"👥 <b>Broadcast Complete!</b>\n\n"
            f"✅ Sent: <b>{sent}</b>\n"
            f"❌ Failed: <b>{failed}</b>\n"
            f"📊 Total: {sent + failed}",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
    except Exception:
        await message.answer(f"✅ Sent: {sent} | ❌ Failed: {failed}", parse_mode="HTML")
