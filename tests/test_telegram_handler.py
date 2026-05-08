from pathlib import Path

from bot.booking_engine import BookingRequest
from bot.telegram_handler import TelegramBotHandler, parse_booking_message
from config.settings import Settings
from utils.logger import setup_logger


def test_parse_booking_message_extracts_fields() -> None:
    parsed = parse_booking_message("Book Court 3 at 7pm on Saturday for 90 minutes", "Europe/London")
    assert parsed.court_name == "Court 3"
    assert parsed.duration_minutes == 90
    assert parsed.start_time.hour == 19
    assert parsed.start_time.minute == 0
    assert parsed.start_time.strftime("%A") == "Saturday"


def test_parse_booking_message_defaults_duration() -> None:
    parsed = parse_booking_message("Book Court 5 at 18:30 on Monday", "Europe/London")
    assert parsed.duration_minutes == 60
    assert parsed.court_name == "Court 5"
    assert parsed.start_time.hour == 18
    assert parsed.start_time.minute == 30


class SchedulerDouble:
    def __init__(self) -> None:
        self.scheduled_request: BookingRequest | None = None
        self.run_at = None

    def start(self) -> None:
        return None

    def schedule_booking(self, request: BookingRequest, run_at):
        self.scheduled_request = request
        self.run_at = run_at
        return "job-123"

    def list_bookings(self, _chat_id: int) -> list[str]:
        return []

    def cancel_booking(self, _job_id: str, _chat_id: int) -> bool:
        return False


def test_telegram_handler_schedules_booking_for_target_slot(tmp_path: Path) -> None:
    scheduler = SchedulerDouble()
    settings = Settings(
        telegram_bot_token="dummy-token",
        telegram_poll_interval=1.0,
        booking_target_url="https://example.com",
        booking_headless=True,
        booking_timezone="Europe/London",
        screenshot_dir=tmp_path,
        max_retries=2,
        retry_step_minutes=30,
        booking_user_name="User",
        booking_user_email="user@example.com",
        booking_user_phone="+44000000000",
        bookings_db_path=tmp_path / "bookings.db",
    )
    handler = TelegramBotHandler(settings=settings, scheduler=scheduler, logger=setup_logger())
    messages: list[str] = []
    handler.send_message = lambda _chat_id, text: messages.append(text)

    update = {
        "update_id": 1,
        "message": {
            "chat": {"id": 99},
            "text": "Book Court 3 at 7pm on Saturday for 60 minutes",
        },
    }
    handler._handle_update(update)

    assert scheduler.scheduled_request is not None
    assert scheduler.run_at == scheduler.scheduled_request.start_time
    assert any("Job ID: job-123" in message for message in messages)
