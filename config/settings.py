import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_poll_interval: float
    booking_target_url: str
    booking_headless: bool
    booking_timezone: str
    screenshot_dir: Path
    max_retries: int
    retry_step_minutes: int
    booking_user_name: str
    booking_user_email: str
    booking_user_phone: str
    bookings_db_path: Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def load_settings() -> Settings:
    screenshot_dir = BASE_DIR / os.getenv("SCREENSHOT_DIR", "artifacts/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_poll_interval=_env_float("TELEGRAM_POLL_INTERVAL", 1.0),
        booking_target_url=os.getenv("BOOKING_TARGET_URL", "https://www.opencourt-tennis.co.uk"),
        booking_headless=_env_bool("BOOKING_HEADLESS", True),
        booking_timezone=os.getenv("BOOKING_TIMEZONE", "Europe/London"),
        screenshot_dir=screenshot_dir,
        max_retries=_env_int("MAX_RETRIES", 2),
        retry_step_minutes=_env_int("RETRY_STEP_MINUTES", 30),
        booking_user_name=os.getenv("BOOKING_USER_NAME", "Automation User"),
        booking_user_email=os.getenv("BOOKING_USER_EMAIL", "automation@example.com"),
        booking_user_phone=os.getenv("BOOKING_USER_PHONE", "+440000000000"),
        bookings_db_path=BASE_DIR / os.getenv("BOOKINGS_DB_PATH", "artifacts/bookings.db"),
    )
