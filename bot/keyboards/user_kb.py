from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.models import Channel, Apk


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Refer & Earn"), KeyboardButton(text="📱 Get APK")],
            [KeyboardButton(text="👤 My Profile"),   KeyboardButton(text="📜 History")],
            [KeyboardButton(text="💬 Support")],
        ],
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Select an option…",
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def join_channels_kb(channels: list[Channel], show_check: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        username = ch.channel_username.lstrip("@")
        title = ch.channel_title or ch.channel_username
        builder.row(InlineKeyboardButton(text=f"📢 {title}", url=f"https://t.me/{username}"))
    if show_check:
        builder.row(InlineKeyboardButton(text="✅ I've Joined All Channels", callback_data="check_join"))
    return builder.as_markup()


def recheck_channels_kb(missing: list[Channel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in missing:
        username = ch.channel_username.lstrip("@")
        title = ch.channel_title or ch.channel_username
        builder.row(InlineKeyboardButton(text=f"📢 Join {title}", url=f"https://t.me/{username}"))
    builder.row(InlineKeyboardButton(text="🔄 Check Again", callback_data="check_join"))
    return builder.as_markup()


def apk_list_kb(apks: list[Apk]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for apk in apks:
        builder.row(InlineKeyboardButton(
            text=f"📦 {apk.name}  ·  {apk.point_cost} pts",
            callback_data=f"apk_select_{apk.id}",
        ))
    return builder.as_markup()


def apk_confirm_kb(apk_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm Redeem", callback_data=f"apk_confirm_{apk_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="apk_cancel"),
        ]
    ])


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Back to Menu", callback_data="main_menu")]
    ])


def support_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Contact Support", url="https://t.me/ZEXUS_HERE")]
    ])
