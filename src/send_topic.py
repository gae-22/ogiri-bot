import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from src.gemini_client import GeminiClient

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

    print("Generating Ogiri topic...")
    try:
        # Generate topic
        topic = gemini.generate_ogiri_topic()
        print(f"Generated topic: {topic}")

        # Send to Slack
        client.chat_postMessage(
            channel=channel_id,
            username="大喜利お題投下Bot",
            icon_emoji=":ogiri-bot:",
            text=f"【大喜利お題】\n{topic}",
        )
        print("Successfully sent topic to Slack!")

    except SlackApiError as e:
        print(f"Error sending message to Slack: {e.response['error']}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
