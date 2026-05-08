from pathlib import Path

from bot.booking_engine import BookingEngine
from bot.request_store import BookingRequestStore
from bot.scheduler import BookingScheduler
from bot.telegram_handler import TelegramBotHandler
from config.settings import BASE_DIR, load_settings
from utils.logger import setup_logger


def main() -> None:
    settings = load_settings()
    logger = setup_logger(log_file=Path(BASE_DIR / "artifacts" / "courtbooker.log"))
    engine = BookingEngine(settings=settings, logger=logger)

    telegram_handler: TelegramBotHandler | None = None

    def notify(chat_id: int, text: str) -> None:
        if telegram_handler:
            telegram_handler.send_message(chat_id, text)
        logger.info("Notify chat_id=%s: %s", chat_id, text)

    scheduler = BookingScheduler(
        engine=engine,
        settings=settings,
        logger=logger,
        notify_callback=notify,
        request_store=BookingRequestStore(settings.bookings_db_path),
    )
    telegram_handler = TelegramBotHandler(
        settings=settings,
        scheduler=scheduler,
        logger=logger,
    )
    telegram_handler.run_polling()


if __name__ == "__main__":
    main()
