from datetime import datetime, timedelta
from pathlib import Path
from time import sleep
from zoneinfo import ZoneInfo

from bot.booking_engine import BookingRequest, BookingResult
from bot.request_store import BookingRequestStore
from bot.scheduler import BookingScheduler
from config.settings import Settings
from utils.logger import setup_logger


class EngineDouble:
    def __init__(self, outcomes: list[bool], tmp_path: Path) -> None:
        self.outcomes = outcomes
        self.calls: list[datetime] = []
        self.tmp_path = tmp_path

    def attempt_booking(self, request: BookingRequest) -> BookingResult:
        self.calls.append(request.start_time)
        success = self.outcomes[min(len(self.calls) - 1, len(self.outcomes) - 1)]
        screenshot = self.tmp_path / f"attempt_{len(self.calls)}.png"
        screenshot.write_bytes(b"fake")
        return BookingResult(
            success=success,
            message="ok" if success else "failed",
            screenshot_path=screenshot,
            booked_time=request.start_time if success else None,
        )


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        telegram_bot_token="dummy",
        telegram_poll_interval=1.0,
        booking_target_url="https://example.com",
        booking_headless=True,
        booking_timezone="Europe/London",
        screenshot_dir=tmp_path,
        max_retries=2,
        retry_step_minutes=30,
        booking_user_name="Test User",
        booking_user_email="test@example.com",
        booking_user_phone="+44000111222",
        bookings_db_path=tmp_path / "bookings.db",
    )


def test_scheduler_retries_next_available_slot(tmp_path: Path) -> None:
    logger = setup_logger()
    engine = EngineDouble(outcomes=[False, True], tmp_path=tmp_path)
    messages: list[str] = []
    scheduler = BookingScheduler(
        engine=engine,
        settings=_settings(tmp_path),
        logger=logger,
        notify_callback=lambda _chat_id, text: messages.append(text),
        request_store=BookingRequestStore(tmp_path / "bookings.db"),
    )

    request = BookingRequest(
        chat_id=5,
        court_name="Court 3",
        start_time=datetime(2026, 5, 9, 19, 0, tzinfo=ZoneInfo("Europe/London")),
        duration_minutes=60,
    )
    scheduler._run_with_retries(request)

    assert len(engine.calls) == 2
    assert (engine.calls[1] - engine.calls[0]) == timedelta(minutes=30)
    assert any("Booking confirmed" in text for text in messages)


def test_scheduler_runs_job_close_to_target_time(tmp_path: Path) -> None:
    logger = setup_logger()
    engine = EngineDouble(outcomes=[True], tmp_path=tmp_path)
    executions: list[datetime] = []

    scheduler = BookingScheduler(
        engine=engine,
        settings=_settings(tmp_path),
        logger=logger,
        notify_callback=lambda _chat_id, _text: executions.append(
            datetime.now(ZoneInfo("Europe/London"))
        ),
        request_store=BookingRequestStore(tmp_path / "bookings.db"),
    )

    scheduler.start()
    try:
        request = BookingRequest(
            chat_id=8,
            court_name="Court 1",
            start_time=datetime.now(ZoneInfo("Europe/London")) + timedelta(hours=1),
            duration_minutes=60,
        )
        target = datetime.now(ZoneInfo("Europe/London")) + timedelta(seconds=1)
        scheduler.schedule_booking(request, run_at=target)
        sleep(2)
    finally:
        scheduler.shutdown()

    assert executions, "Expected scheduled job to execute"
    delta = abs((executions[0] - target).total_seconds())
    assert delta < 1.5
