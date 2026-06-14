"""Single place to configure application logging.

Call `setup_logging()` once at process start (the FastAPI app and the eval CLI
both do). Modules then use `logging.getLogger(__name__)` as usual.
"""
import logging
import os


def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    # Uvicorn access logs are noisy at INFO; keep them at WARNING.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
