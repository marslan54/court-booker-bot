import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import requests
from zoneinfo import ZoneInfo

from bot.booking_engine import BookingRequest
from bot.scheduler import BookingScheduler
from config.settings import Settings


REQUEST_REGEX = re.compile(
    (
        r"book\s+(?P<court>[\w\s-]+?)\s+at\s+"
        r"(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s+on\s+"
        r"(?P<day>[a-zA-Z]+)(?:\s+for\s+(?P<duration>\d+)\s*(?:m|min|minutes)?)?"
    ),
    re.IGNORECASE,
)

WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass
class ParsedRequest:
    court_name: str
    start_time: datetime
    duration_minutes: int


class TelegramBotHandler:
    def __init__(self, settings: Settings, scheduler: BookingScheduler, logger) -> None:
        self.settings = settings
        self.scheduler = scheduler
        self.logger = logger
        self.base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        self.last_update_id: int | None = None

    def run_polling(self) -> None:
        if not self.settings.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

        self.scheduler.start()
        self.logger.info("Telegram polling started")
        while True:
            updates = self._fetch_updates()
            for update in updates:
                self._handle_update(update)

    def send_message(self, chat_id: int, text: str) -> None:
        requests.post(
            f"{self.base_url}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=20,
        )

    def _fetch_updates(self) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": 25,
            "allowed_updates": ["message"],
        }
        if self.last_update_id is not None:
            payload["offset"] = self.last_update_id + 1

        response = requests.get(f"{self.base_url}/getUpdates", params=payload, timeout=35)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            self.logger.error("Telegram getUpdates failed: %s", data)
            return []
        return data.get("result", [])

    def _handle_update(self, update: dict[str, Any]) -> None:
        self.last_update_id = update.get("update_id", self.last_update_id)
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        if not text or not chat_id:
            return

        lowered = text.strip().lower()
        if lowered.startswith("/status"):
            self._handle_status(chat_id)
            return
        if lowered.startswith("/cancel"):
            self._handle_cancel(chat_id, text)
            return
        if lowered.startswith("/book "):
            text = text[6:].strip()

        try:
            parsed = parse_booking_message(text, self.settings.booking_timezone)
            booking_request = BookingRequest(
                chat_id=chat_id,
                court_name=parsed.court_name,
                start_time=parsed.start_time,
                duration_minutes=parsed.duration_minutes,
            )
            run_at = parsed.start_time
            job_id = self.scheduler.schedule_booking(booking_request, run_at=run_at)
            self.send_message(
                chat_id,
                (
                    "Got it - I'll attempt booking "
                    f"{parsed.court_name} at {parsed.start_time.strftime('%I:%M%p on %A')}. "
                    f"Job ID: {job_id}. I'll notify you once confirmed."
                ),
            )
        except ValueError as exc:
            self.send_message(
                chat_id,
                (
                    f"Couldn't parse that request: {exc}. "
                    "Try: /book Court 3 at 7pm on Saturday for 60 minutes"
                ),
            )

    def _handle_status(self, chat_id: int) -> None:
        lines = self.scheduler.list_bookings(chat_id)
        self.send_message(chat_id, "Your booking jobs:\n" + "\n".join(lines))

    def _handle_cancel(self, chat_id: int, text: str) -> None:
        parts = text.strip().split(maxsplit=1)
        if len(parts) < 2:
            self.send_message(chat_id, "Usage: /cancel <job_id>")
            return
        cancelled = self.scheduler.cancel_booking(parts[1], chat_id=chat_id)
        if cancelled:
            self.send_message(chat_id, f"Cancelled job {parts[1]}.")
        else:
            self.send_message(chat_id, "Could not find that job id.")


def parse_booking_message(text: str, timezone_name: str) -> ParsedRequest:
    match = REQUEST_REGEX.search(text.strip())
    if not match:
        raise ValueError("Use format: Book Court 3 at 7pm on Saturday for 60 minutes")

    court_name = match.group("court").strip().title()
    time_raw = match.group("time").replace(" ", "").lower()
    day_raw = match.group("day").strip().lower()
    duration_raw = match.group("duration")
    duration = int(duration_raw) if duration_raw else 60

    if day_raw not in WEEKDAY_INDEX:
        raise ValueError(f"Unknown day '{day_raw}'")

    target_date = _next_weekday(WEEKDAY_INDEX[day_raw], timezone_name)
    target_time = _parse_time(time_raw)
    start_time = datetime(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=target_time.hour,
        minute=target_time.minute,
        tzinfo=ZoneInfo(timezone_name),
    )

    return ParsedRequest(
        court_name=court_name,
        start_time=start_time,
        duration_minutes=duration,
    )


def _next_weekday(target_weekday: int, timezone_name: str) -> datetime:
    now = datetime.now(ZoneInfo(timezone_name))
    days_ahead = (target_weekday - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return now + timedelta(days=days_ahead)


def _parse_time(time_raw: str) -> datetime:
    formats = ("%I%p", "%I:%M%p", "%H:%M", "%H")
    for fmt in formats:
        try:
            return datetime.strptime(time_raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported time format '{time_raw}'")
