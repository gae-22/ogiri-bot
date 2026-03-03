import logging
import threading
import time

import schedule

from src.bot import main as run_bot
from src.send_topic import main as send_topic


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _run_scheduler() -> None:
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    _configure_logging()

    schedule.every().day.at("11:00").do(send_topic)

    scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True)
    scheduler_thread.start()

    run_bot()
