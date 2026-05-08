from dataclasses import replace
from datetime import datetime, timedelta
from typing import Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

from bot.booking_engine import BookingEngine, BookingRequest, BookingResult
from bot.request_store import BookingRequestStore
from config.settings import Settings


NotifyCallback = Callable[[int, str], None]


class BookingScheduler:
    def __init__(
        self,
        engine: BookingEngine,
        settings: Settings,
        logger,
        notify_callback: NotifyCallback,
        request_store: BookingRequestStore,
    ) -> None:
        self.engine = engine
        self.settings = settings
        self.logger = logger
        self.notify_callback = notify_callback
        self.request_store = request_store
        self.scheduler = BackgroundScheduler(timezone=settings.booking_timezone)

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("Booking scheduler started")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.logger.info("Booking scheduler stopped")

    def schedule_booking(self, request: BookingRequest, run_at: datetime) -> str:
        job_id = str(uuid4())
        job = self.scheduler.add_job(
            self._run_with_retries,
            trigger=DateTrigger(run_date=run_at, timezone=self.settings.booking_timezone),
            id=job_id,
            args=[request, job_id],
            misfire_grace_time=10,
            coalesce=True,
        )
        self.request_store.upsert(
            job_id=job_id,
            chat_id=request.chat_id,
            court_name=request.court_name,
            start_time=request.start_time,
            status="scheduled",
        )
        self.logger.info(
            "Scheduled booking chat_id=%s court=%s run_at=%s",
            request.chat_id,
            request.court_name,
            run_at.isoformat(),
        )
        return str(job.id)

    def cancel_booking(self, job_id: str, chat_id: int) -> bool:
        job = self.scheduler.get_job(job_id)
        if not job:
            return False
        request = job.args[0]
        if request.chat_id != chat_id:
            return False
        self.scheduler.remove_job(job_id)
        self.request_store.update_status(job_id, "cancelled")
        return True

    def list_bookings(self, chat_id: int) -> list[str]:
        bookings = self.request_store.list_for_chat(chat_id=chat_id)
        if not bookings:
            return ["No booking jobs found."]
        lines: list[str] = []
        now = datetime.now(ZoneInfo(self.settings.booking_timezone))
        for booking in bookings:
            start_time = datetime.fromisoformat(booking.start_time_iso)
            eta_seconds = int((start_time - now).total_seconds())
            eta = "started/past" if eta_seconds <= 0 else f"in {eta_seconds // 60}m"
            lines.append(
                (
                    f"{booking.job_id} | {booking.court_name} | "
                    f"{start_time.strftime('%Y-%m-%d %H:%M')} | "
                    f"{booking.status} | {eta}"
                )
            )
        return lines

    def _run_with_retries(self, request: BookingRequest, job_id: str | None = None) -> None:
        if job_id:
            self.request_store.update_status(job_id, "running")
        current_request = request
        for attempt in range(self.settings.max_retries + 1):
            self.logger.info(
                "Executing booking attempt %s for chat_id=%s at %s",
                attempt + 1,
                current_request.chat_id,
                current_request.start_time.isoformat(),
            )
            result = self.engine.attempt_booking(current_request)
            self._notify_result(current_request, result, attempt)
            if result.success:
                if job_id:
                    self.request_store.update_status(job_id, "confirmed")
                return

            next_time = current_request.start_time + timedelta(minutes=self.settings.retry_step_minutes)
            current_request = replace(current_request, start_time=next_time)

        self.notify_callback(
            request.chat_id,
            "All retry attempts failed. I can watch for the next opening if you want.",
        )
        if job_id:
            self.request_store.update_status(job_id, "failed")

    def _notify_result(self, request: BookingRequest, result: BookingResult, attempt: int) -> None:
        if result.success:
            text = (
                f"Booking confirmed for {request.court_name} at "
                f"{result.booked_time.strftime('%H:%M on %A')}."
            )
        else:
            text = (
                f"Attempt {attempt + 1} failed: slot unavailable. "
                f"Screenshot: {result.screenshot_path.name}"
            )
        self.notify_callback(request.chat_id, text)
