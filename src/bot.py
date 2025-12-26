import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from src.gemini_client import GeminiClient

# Load environment variables
load_dotenv()

# Initialize Slack App
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Initialize Gemini Client
gemini_client = GeminiClient()


@app.event("app_mention")
def handle_app_mention_events(body, logger, say):
    logger.info(body)
    say("大喜利のお題を考えています...少々お待ちください！")
    try:
        topic = gemini_client.generate_ogiri_topic()
        say(f"【大喜利お題】\n{topic}")
    except Exception as e:
        logger.error(f"Error handling app_mention: {e}")
        say("申し訳ありません。エラーが発生しました。")


# Also listen for a specific command if configured in Slack Manifest
# @app.command("/ogiri")
# def handle_ogiri_command(ack, say):
#     ack()
#     say("大喜利のお題を考えています...少々お待ちください！")
#     try:
#         topic = gemini_client.generate_ogiri_topic()
#         say(f"【大喜利お題】\n{topic}")
#     except Exception as e:
#         say("申し訳ありません。エラーが発生しました。")


def main():
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        print("Error: SLACK_APP_TOKEN is not set.")
        return

    handler = SocketModeHandler(app, app_token)
    print("⚡️ Ogiri Bot started!")
    handler.start()


if __name__ == "__main__":
    main()
