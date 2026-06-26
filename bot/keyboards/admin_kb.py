from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.models import Channel, Apk


def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistics",     callback_data="admin_stats"),
            InlineKeyboardButton(text="📢 Broadcast",      callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="📡 Channels",       callback_data="admin_channels"),
            InlineKeyboardButton(text="📱 APK Manager",    callback_data="admin_apks"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Point Settings", callback_data="admin_points"),
            InlineKeyboardButton(text="👥 Users",           callback_data="admin_users"),
        ],
    ])


def admin_channels_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Channel",     callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="➖ Remove Channel",  callback_data="admin_remove_channel")],
        [InlineKeyboardButton(text="📋 List Channels",   callback_data="admin_list_channels")],
        [InlineKeyboardButton(text="◀️ Back",            callback_data="admin_back")],
    ])


def admin_apk_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add APK",              callback_data="admin_add_apk")],
        [InlineKeyboardButton(text="➖ Remove APK",           callback_data="admin_remove_apk")],
        [InlineKeyboardButton(text="📋 List APKs",            callback_data="admin_list_apks")],
        [InlineKeyboardButton(text="🔁 Set All Same Points",  callback_data="admin_set_all_apk_pts")],
        [InlineKeyboardButton(text="◀️ Back",                 callback_data="admin_back")],
    ])


def admin_remove_apk_kb(apks: list[Apk]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for apk in apks:
        file_icon = "📎" if apk.file_id else "📝"
        builder.row(InlineKeyboardButton(
            text=f"🗑 {file_icon} {apk.name}  ({apk.point_cost} pts)",
            callback_data=f"admin_del_apk_{apk.id}",
        ))
    builder.row(InlineKeyboardButton(text="◀️ Back", callback_data="admin_apks"))
    return builder.as_markup()


def admin_remove_channels_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        title = ch.channel_title or ch.channel_username
        builder.row(InlineKeyboardButton(
            text=f"🗑 {title}",
            callback_data=f"admin_del_ch_{ch.id}",
        ))
    builder.row(InlineKeyboardButton(text="◀️ Back", callback_data="admin_channels"))
    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Admin Panel", callback_data="admin_back")]
    ])


def admin_broadcast_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Send to Channels", callback_data="admin_bc_channels")],
        [InlineKeyboardButton(text="👥 Send to Users",    callback_data="admin_bc_users")],
        [InlineKeyboardButton(text="◀️ Back",             callback_data="admin_back")],
    ])


def admin_skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Skip (No File)", callback_data="admin_skip_file")],
        [InlineKeyboardButton(text="◀️ Back to Admin Panel", callback_data="admin_back")],
    ])
