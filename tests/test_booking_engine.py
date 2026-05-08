from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bot.booking_engine import BookingEngine, BookingRequest
from config.settings import Settings
from utils.logger import setup_logger


def test_booking_engine_attempt_booking_uses_route_interception(tmp_path: Path) -> None:
    settings = Settings(
        telegram_bot_token="dummy",
        telegram_poll_interval=1.0,
        booking_target_url="https://booking.test/form",
        booking_headless=True,
        booking_timezone="Europe/London",
        screenshot_dir=tmp_path,
        max_retries=1,
        retry_step_minutes=30,
        booking_user_name="Test User",
        booking_user_email="test@example.com",
        booking_user_phone="+44000111222",
        bookings_db_path=tmp_path / "bookings.db",
    )
    logger = setup_logger()
    html = """
    <html>
      <body>
        <form>
          <select name='court'><option>Court 3</option></select>
          <input name='date' />
          <select name='start_time'><option>19:00</option></select>
          <select name='end_time'><option>20:00</option></select>
          <input name='name' />
          <input name='email' />
          <input name='phone' />
          <button type='submit'>Book</button>
        </form>
      </body>
    </html>
    """
    engine = BookingEngine(
        settings=settings,
        logger=logger,
        page_setup_hook=lambda page: page.route(
            "**/*",
            lambda route: route.fulfill(status=200, body=html),
        ),
    )
    request = BookingRequest(
        chat_id=123,
        court_name="Court 3",
        start_time=datetime(2026, 5, 9, 19, 0, tzinfo=ZoneInfo("Europe/London")),
        duration_minutes=60,
    )

    result = engine.attempt_booking(request)
    assert result.success is True
    assert result.screenshot_path.exists()
