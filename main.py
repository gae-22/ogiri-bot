import threading
import time
import schedule
from src.bot import main
import src.send_topic


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    # Schedule the topic generation
    schedule.every().day.at("11:00").do(src.send_topic.main)

    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    main()
