import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Callable

from playwright.sync_api import Error, TimeoutError, sync_playwright

from config.settings import Settings


@dataclass
class BookingRequest:
    chat_id: int
    court_name: str
    start_time: datetime
    duration_minutes: int


@dataclass
class BookingResult:
    success: bool
    message: str
    screenshot_path: Path
    booked_time: datetime | None = None


class BookingEngine:
    def __init__(
        self,
        settings: Settings,
        logger,
        page_setup_hook: Callable | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.page_setup_hook = page_setup_hook

    def _human_delay(self, min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
        sleep(random.uniform(min_seconds, max_seconds))

    def _take_screenshot(self, page, prefix: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = self.settings.screenshot_dir / f"{prefix}_{stamp}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        return screenshot_path

    def attempt_booking(self, request: BookingRequest) -> BookingResult:
        self.logger.info(
            "Booking attempt started for %s at %s",
            request.court_name,
            request.start_time.isoformat(),
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.settings.booking_headless)
            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="en-GB",
                timezone_id=self.settings.booking_timezone,
                extra_http_headers={
                    "Accept-Language": "en-GB,en;q=0.9",
                    "DNT": "1",
                    "Upgrade-Insecure-Requests": "1",
                },
            )
            page = context.new_page()
            if self.page_setup_hook:
                self.page_setup_hook(page)

            try:
                page.goto(self.settings.booking_target_url, wait_until="domcontentloaded", timeout=45_000)
                self._human_delay()
                self._fill_booking_form(page, request)
                self._human_delay()
                self._submit_booking(page)
                page.wait_for_load_state("networkidle", timeout=10_000)
                screenshot = self._take_screenshot(page, "booking_success")
                self.logger.info("Booking confirmed for chat_id=%s", request.chat_id)
                return BookingResult(
                    success=True,
                    message="Booking confirmed!",
                    screenshot_path=screenshot,
                    booked_time=request.start_time,
                )
            except (TimeoutError, Error, ValueError) as exc:
                screenshot = self._take_screenshot(page, "booking_failure")
                self.logger.error("Booking failed: %s", exc)
                return BookingResult(
                    success=False,
                    message=f"Slot unavailable or booking failed: {exc}",
                    screenshot_path=screenshot,
                    booked_time=None,
                )
            finally:
                context.close()
                browser.close()

    def _fill_booking_form(self, page, request: BookingRequest) -> None:
        date_value = request.start_time.strftime("%Y-%m-%d")
        time_value = request.start_time.strftime("%H:%M")
        end_time = (request.start_time.timestamp() + request.duration_minutes * 60)
        end_time_value = datetime.fromtimestamp(end_time).strftime("%H:%M")

        court_selectors = [
            "select[name='court']",
            "#court",
            "[data-testid='court-select']",
        ]
        date_selectors = [
            "input[name='date']",
            "#date",
            "[data-testid='date-input']",
        ]
        start_selectors = [
            "select[name='start_time']",
            "#start-time",
            "[data-testid='start-time']",
        ]
        end_selectors = [
            "select[name='end_time']",
            "#end-time",
            "[data-testid='end-time']",
        ]

        self._select_first_existing(page, court_selectors, request.court_name)
        self._human_delay()
        self._fill_first_existing(page, date_selectors, date_value)
        self._human_delay()
        self._select_first_existing(page, start_selectors, time_value)
        self._human_delay()
        self._select_first_existing(page, end_selectors, end_time_value)
        self._human_delay()

        self._fill_first_existing(page, ["input[name='name']", "#name"], self.settings.booking_user_name)
        self._fill_first_existing(page, ["input[name='email']", "#email"], self.settings.booking_user_email)
        self._fill_first_existing(page, ["input[name='phone']", "#phone"], self.settings.booking_user_phone)

    def _submit_booking(self, page) -> None:
        submit_selectors = [
            "button[type='submit']",
            "#book-now",
            "[data-testid='book-button']",
        ]
        self._click_first_existing(page, submit_selectors)

    def _first_visible_locator(self, page, selectors: list[str]):
        for selector in selectors:
            locator = page.locator(selector)
            if locator.count() > 0:
                return locator.first
        raise ValueError(f"No selectors matched from {selectors}")

    def _fill_first_existing(self, page, selectors: list[str], value: str) -> None:
        locator = self._first_visible_locator(page, selectors)
        locator.fill(value)

    def _select_first_existing(self, page, selectors: list[str], value: str) -> None:
        locator = self._first_visible_locator(page, selectors)
        tag_name = locator.evaluate("node => node.tagName.toLowerCase()")
        if tag_name == "select":
            try:
                locator.select_option(label=value)
            except Error:
                try:
                    locator.select_option(value=value)
                except Error:
                    # Some booking widgets inject labels dynamically; fall back to typing/selecting first.
                    options = locator.locator("option")
                    if options.count() == 0:
                        raise
                    locator.select_option(index=0)
        else:
            locator.fill(value)

    def _click_first_existing(self, page, selectors: list[str]) -> None:
        locator = self._first_visible_locator(page, selectors)
        locator.click()
