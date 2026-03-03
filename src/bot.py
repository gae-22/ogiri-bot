import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from src.database import Database
from src.gemini_client import GeminiClient

load_dotenv()

logger = logging.getLogger(__name__)

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
gemini_client = GeminiClient()
db = Database()


@app.event("app_mention")
def handle_app_mention(body: dict, say, logger=logger) -> None:
    logger.info("app_mention received: %s", body)
    say("大喜利のお題を考えています...少々お待ちください！")
    try:
        recent_topics = db.get_recent_topics(limit=20)
        result = gemini_client.generate_topic(recent_topics=recent_topics)
        db.save_topic(
            result.text,
            result.prompt_file,
            model_used=result.model_used,
            format_hint=result.format_hint,
            creative_angle=result.creative_angle,
        )
        say(f"【大喜利お題】\n{result.text}")
    except Exception:
        logger.exception("Error handling app_mention.")
        say("申し訳ありません。エラーが発生しました。")


def main() -> None:
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        logger.error("SLACK_APP_TOKEN is not set.")
        return
    logger.info("Starting Ogiri Bot...")
    SocketModeHandler(app, app_token).start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
