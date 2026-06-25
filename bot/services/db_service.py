from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import User, Channel, Referral, Apk, Redemption, Setting
from bot.config import REWARD_PER_REFERRAL_DEFAULT, WITHDRAW_POINTS_DEFAULT


# ── Settings ───────────────────────────────────────────────────────────────────

async def get_setting(session: AsyncSession, key: str, default: str = "") -> str:
    result = await session.execute(select(Setting).where(Setting.key == key))
    s = result.scalar_one_or_none()
    return s.value if s else default


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    result = await session.execute(select(Setting).where(Setting.key == key))
    s = result.scalar_one_or_none()
    if s:
        s.value = value
    else:
        session.add(Setting(key=key, value=value))
    await session.commit()


async def get_reward_per_referral(session: AsyncSession) -> int:
    val = await get_setting(session, "reward_per_referral", str(REWARD_PER_REFERRAL_DEFAULT))
    try:
        return int(val)
    except ValueError:
        return REWARD_PER_REFERRAL_DEFAULT


# ── Users ──────────────────────────────────────────────────────────────────────

async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    referred_by: int | None = None,
) -> tuple[User, bool]:
    user = await get_user(session, telegram_id)
    if user:
        user.username = username
        user.first_name = first_name
        await session.commit()
        return user, False
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        referred_by=referred_by,
        points=0,
    )
    session.add(user)
    await session.commit()
    return user, True


async def mark_user_verified(session: AsyncSession, telegram_id: int) -> None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user and not user.verified:
        user.verified = True
        await session.commit()


async def get_all_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User))
    return list(result.scalars().all())


async def block_user(session: AsyncSession, telegram_id: int) -> None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        user.blocked = True
        await session.commit()


async def unblock_user(session: AsyncSession, telegram_id: int) -> None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        user.blocked = False
        await session.commit()


# ── Referrals ──────────────────────────────────────────────────────────────────

async def process_referral(session: AsyncSession, referrer_id: int, referred_id: int) -> bool:
    existing = await session.execute(
        select(Referral).where(Referral.referred_id == referred_id)
    )
    if existing.scalar_one_or_none():
        return False

    referrer = await get_user(session, referrer_id)
    if not referrer or referrer.telegram_id == referred_id:
        return False

    reward = await get_reward_per_referral(session)

    session.add(Referral(referrer_id=referrer_id, referred_id=referred_id))
    referrer.points += reward
    referrer.referrals += 1
    await session.commit()
    return True


# ── Channels ───────────────────────────────────────────────────────────────────

async def get_all_channels(session: AsyncSession) -> list[Channel]:
    result = await session.execute(select(Channel))
    return list(result.scalars().all())


async def add_channel(session: AsyncSession, channel_id: str, username: str, title: str | None) -> Channel:
    ch = Channel(channel_id=channel_id, channel_username=username, channel_title=title)
    session.add(ch)
    await session.commit()
    return ch


async def remove_channel(session: AsyncSession, channel_db_id: int) -> None:
    result = await session.execute(select(Channel).where(Channel.id == channel_db_id))
    ch = result.scalar_one_or_none()
    if ch:
        await session.delete(ch)
        await session.commit()


# ── APKs ───────────────────────────────────────────────────────────────────────

async def get_all_apks(session: AsyncSession, active_only: bool = False) -> list[Apk]:
    q = select(Apk)
    if active_only:
        q = q.where(Apk.is_active == True)
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_apk(session: AsyncSession, apk_id: int) -> Apk | None:
    result = await session.execute(select(Apk).where(Apk.id == apk_id))
    return result.scalar_one_or_none()


async def add_apk(session: AsyncSession, name: str, password: str, point_cost: int) -> Apk:
    apk = Apk(name=name, password=password, point_cost=point_cost, is_active=True)
    session.add(apk)
    await session.commit()
    return apk


async def remove_apk(session: AsyncSession, apk_id: int) -> None:
    result = await session.execute(select(Apk).where(Apk.id == apk_id))
    apk = result.scalar_one_or_none()
    if apk:
        await session.delete(apk)
        await session.commit()


async def set_all_apk_points(session: AsyncSession, points: int) -> int:
    result = await session.execute(select(Apk))
    apks = list(result.scalars().all())
    for apk in apks:
        apk.point_cost = points
    await session.commit()
    return len(apks)


# ── Redemptions ────────────────────────────────────────────────────────────────

async def redeem_apk(session: AsyncSession, telegram_id: int, apk_id: int) -> tuple[bool, str]:
    user = await get_user(session, telegram_id)
    if not user:
        return False, "User not found."

    apk = await get_apk(session, apk_id)
    if not apk or not apk.is_active:
        return False, "APK not available."

    if user.points < apk.point_cost:
        return False, f"Insufficient points. You need {apk.point_cost} pts, you have {user.points}."

    user.points -= apk.point_cost
    session.add(Redemption(
        user_telegram_id=telegram_id,
        apk_id=apk_id,
        points_spent=apk.point_cost,
    ))
    await session.commit()
    return True, f"{apk.name}|{apk.password}"


async def get_user_redemptions(session: AsyncSession, telegram_id: int) -> list[Redemption]:
    result = await session.execute(
        select(Redemption).where(Redemption.user_telegram_id == telegram_id).order_by(Redemption.date.desc())
    )
    return list(result.scalars().all())


# ── Stats ──────────────────────────────────────────────────────────────────────

async def get_stats(session: AsyncSession) -> dict:
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    verified_users = (await session.execute(select(func.count(User.id)).where(User.verified == True))).scalar() or 0
    total_referrals = (await session.execute(select(func.count(Referral.id)))).scalar() or 0
    total_redemptions = (await session.execute(select(func.count(Redemption.id)))).scalar() or 0
    active_apks = (await session.execute(select(func.count(Apk.id)).where(Apk.is_active == True))).scalar() or 0
    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "total_referrals": total_referrals,
        "total_redemptions": total_redemptions,
        "active_apks": active_apks,
    }
