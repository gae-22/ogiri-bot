import logging
import os
from pathlib import Path
import sys
import time

# Ensure the project root is on sys.path when this file is run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.database import Database
from src.gemini_client import GeminiClient

load_dotenv()

logger = logging.getLogger(__name__)

_BOT_USERNAME = "大喜利お題投下Bot"
_BOT_ICON = ":ogiri-bot:"


def main() -> None:
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    channel_id = os.environ.get("SLACK_CHANNEL_ID")
    is_test = os.environ.get("TEST") == "True"

    if not slack_token:
        logger.error("SLACK_BOT_TOKEN is not set.")
        return
    if not channel_id:
        logger.error("SLACK_CHANNEL_ID is not set.")
        return

    slack = WebClient(token=slack_token)
    gemini = GeminiClient()
    db = Database()

    try:
        # ----------------------------------------------------------------
        # 1. Send previous answer if one is waiting
        # ----------------------------------------------------------------
        logger.info("Checking for unsent answers...")
        unsent = db.get_unsent_answer()
        if unsent:
            logger.info("Found unsent answer for topic ID %d.", unsent.id)
            if not is_test:
                slack.chat_postMessage(
                    channel=channel_id,
                    username=_BOT_USERNAME,
                    icon_emoji=_BOT_ICON,
                    text=f"【前回のお題の回答例】\n{unsent.answer}",
                )
                db.mark_answer_sent(unsent.id)
                logger.info("Sent previous answer to Slack.")
            else:
                logger.info("[TEST] Skipping previous answer post.")
        else:
            logger.info("No unsent answers found.")

        # ----------------------------------------------------------------
        # 2. Generate and save a new topic
        # ----------------------------------------------------------------
        logger.info("Generating new Ogiri topic...")
        recent_topics = db.get_recent_topics(limit=20)

        try:
            result = gemini.generate_topic(recent_topics=recent_topics)
        except Exception:
            logger.exception("Failed to generate topic.")
            if not is_test:
                try:
                    slack.chat_postMessage(
                        channel=channel_id,
                        username=_BOT_USERNAME,
                        icon_emoji=_BOT_ICON,
                        text="申し訳ありません。お題の生成に失敗しました。しばらくしてから再度お試しください。",
                    )
                except SlackApiError:
                    logger.exception("Failed to post error message to Slack.")
            return

        logger.info("Generated topic: %s", result.text)
        topic_id = db.save_topic(
            result.text,
            result.prompt_file,
            model_used=result.model_used,
            format_hint=result.format_hint,
            creative_angle=result.creative_angle,
        )
        logger.info("Saved topic with ID %d.", topic_id)

        # ----------------------------------------------------------------
        # 3. Post topic to Slack and record message metadata
        # ----------------------------------------------------------------
        if not is_test:
            response = slack.chat_postMessage(
                channel=channel_id,
                username=_BOT_USERNAME,
                icon_emoji=_BOT_ICON,
                text=f"【本日のお題】\n{result.text}\n\n回答はこのスレッドにお願いします！ :thread:",
            )
            logger.info("Sent topic to Slack.")

            slack_ts: str = response["ts"]
            db.save_slack_info(topic_id, channel_id, slack_ts)

            # Open a reply thread to collect answers
            slack.chat_postMessage(
                channel=channel_id,
                thread_ts=slack_ts,
                username=_BOT_USERNAME,
                icon_emoji=_BOT_ICON,
                text="回答はこちらのスレッドへ :writing_hand:",
            )
            logger.info("Created reply thread.")
        else:
            logger.info("[TEST] Skipping Slack posts.")

        # ----------------------------------------------------------------
        # 4. Generate a model answer (stored, not sent until next run)
        # ----------------------------------------------------------------
        if not is_test:
            time.sleep(10)  # brief delay so the topic post settles

        logger.info("Generating answer for the new topic...")
        try:
            answer_result = gemini.generate_answer(result.text)
            db.save_answer(topic_id, answer_result.text, answer_model=answer_result.model_used)
            logger.info("Saved answer to DB.")
        except Exception:
            logger.exception("Failed to generate answer.")

    except SlackApiError:
        logger.exception("Slack API error.")
    except Exception:
        logger.exception("Unexpected error in send_topic.main().")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
