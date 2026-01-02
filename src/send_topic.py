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
    channel_id = os.environ.get("SLACK_CHANNEL_ID")

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
        # 1. Check for unsent answer from previous run
        print("Checking for unsent answers...")
        unsent = db.get_unsent_answer()
        if unsent:
            topic_id, _, answer = unsent
            print(f"Found unsent answer for topic ID: {topic_id}")

            client.chat_postMessage(
                channel=channel_id,
                username="大喜利お題投下Bot",
                icon_emoji=":ogiri-bot:",
                text=f"【前回のお題の回答例】\n{answer}",
            )
            db.mark_answer_sent(topic_id)
            print("Successfully sent previous answer to Slack!")
        else:
            print("No unsent answers found.")

        # 2. Generate and send new topic
        print("Generating new Ogiri topic...")
        topic, prompt_file = gemini.generate_topic()
        print(f"Generated topic: {topic}")

        # Save topic to DB
        topic_id = db.save_topic(topic, prompt_file)
        print(f"Saved topic with ID: {topic_id}")

        # Send topic to Slack
        client.chat_postMessage(
            channel=channel_id,
            username="大喜利お題投下Bot",
            icon_emoji=":ogiri-bot:",
            text=f"【本日のお題】\n{topic}",
        )
        print("Successfully sent topic to Slack!")

        # 3. Generate and save answer for the new topic (do not send yet)
        print("Generating answer for the new topic...")
        answer = gemini.generate_answer(topic)
        db.save_answer(topic_id, answer)
        print("Successfully saved answer to DB!")

    except SlackApiError as e:
        print(f"Error sending message to Slack: {e.response['error']}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
