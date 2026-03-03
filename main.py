import logging

from src.bot import main as run_bot
from src.send_topic import main as send_topic


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


if __name__ == "__main__":
    _configure_logging()

    send_topic()

    run_bot()
