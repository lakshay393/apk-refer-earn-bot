import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
ADMIN_ID: int = int(os.environ["ADMIN_ID"])
_notify_raw: str = os.getenv("NOTIFY_ID", "0") or "0"
NOTIFY_ID: int = int(_notify_raw) if _notify_raw.isdigit() and int(_notify_raw) != 0 else int(os.environ["ADMIN_ID"])
DATABASE_URL: str = os.environ["DATABASE_URL"]


def _make_async_url(url: str) -> str:
    import re
    url = url.replace("postgresql://", "postgresql+asyncpg://").replace("postgres://", "postgresql+asyncpg://")
    url = re.sub(r"[?&]sslmode=[^&]*", "", url)
    url = re.sub(r"\?$", "", url)
    return url


ASYNC_DATABASE_URL: str = _make_async_url(DATABASE_URL)

WITHDRAW_POINTS_DEFAULT: int = 5
REWARD_PER_REFERRAL_DEFAULT: int = 1
RENDER_URL: str = os.getenv("RENDER_URL", "")

# Auto-set at startup by main.py via bot.get_me()
BOT_USERNAME: str = ""
