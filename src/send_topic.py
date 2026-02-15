import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from src.gemini_client import GeminiClient
from src.database import Database

# Load environment variables
load_dotenv()


def main():
    # Initialize clients
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    channel_id = os.environ.get("SLACK_CHANNEL_ID", "C0A6CNHTXQR")
    test_channel_id = os.environ.get("SLACK_TEST_CHANNEL_ID", "C0A6CNHTXQR")

    if not slack_token:
        print("Error: SLACK_BOT_TOKEN is not set.")
        return
    if not channel_id:
        print("Error: SLACK_CHANNEL_ID is not set.")
        return

    client = WebClient(token=slack_token)
    gemini = GeminiClient()
    db = Database()

    try:
        test = os.environ.get("TEST") == "True"

        # 1. Check for unsent answer from previous run
        print("Checking for unsent answers...")
        unsent = db.get_unsent_answer()
        if unsent:
            topic_id, _, answer = unsent
            print(f"Found unsent answer for topic ID: {topic_id}")

            if not test:
                client.chat_postMessage(
                    channel=channel_id,
                    username="大喜利お題投下Bot",
                    icon_emoji=":ogiri-bot:",
                    text=f"【前回のお題の回答例】\n{answer}",
                )
                db.mark_answer_sent(topic_id)
                print("Successfully sent previous answer to Slack!")
            else:
                print("POST_TEST: Skipping sending previous answer.")
        else:
            print("No unsent answers found.")

        # 2. Generate and send new topic
        print("Generating new Ogiri topic...")
        topic = None
        topic_id = None

        if not test:
            # 最近のお題を取得して重複回避に使用
            recent_topics = db.get_recent_topics(limit=20)
            topic, prompt_file = gemini.generate_topic(recent_topics=recent_topics)
            print(f"Generated topic: {topic}")
            # Save topic to DB
            topic_id = db.save_topic(topic, prompt_file)
            print(f"Saved topic with ID: {topic_id}")
        else:
            topic = "【テスト】これはテスト用のダミーお題です。"
            print(
                f"GEN_TEST: Skipping topic generation and DB save. Using dummy topic: {topic}"
            )

        # Send topic to Slack
        response = None
        response = client.chat_postMessage(
            channel=channel_id if not test else test_channel_id,
            username="大喜利お題投下Bot",
            icon_emoji=":ogiri-bot:",
            text=f"【本日のお題】\n{topic}\n\n回答はこのスレッドにお願いします！ :thread:",
        )
        print("Successfully sent topic to Slack!")

        # Create a thread for answers
        client.chat_postMessage(
            channel=channel_id if not test else test_channel_id,
            thread_ts=response["ts"],
            username="大喜利お題投下Bot",
            icon_emoji=":ogiri-bot:",
            text="回答はこちらのスレッドへ :writing_hand:",
        )
        print("Successfully created thread!")

        # 3. Generate and save answer for the new topic (do not send yet)
        time.slpeep(10)  # Short delay to ensure topic is posted before generating answer
        print("Generating answer for the new topic...")
        if not test:
            answer = gemini.generate_answer(topic)
            if topic_id:
                db.save_answer(topic_id, answer)
                print("Successfully saved answer to DB!")
            else:
                print("Error: Topic ID missing, cannot save answer.")
        else:
            print("GEN_TEST: Skipping answer generation and DB save.")

    except SlackApiError as e:
        print(f"Error sending message to Slack: {e.response['error']}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
