import logging
from pathlib import Path

from rich.logging import RichHandler


def setup_logger(log_level: str = "INFO", log_file: Path | None = None) -> logging.Logger:
    logger = logging.getLogger("courtbooker")
    if logger.handlers:
        return logger

    logger.setLevel(log_level.upper())
    logger.propagate = False

    console_handler = RichHandler(rich_tracebacks=True)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    return logger
