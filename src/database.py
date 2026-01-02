import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

DB_PATH = Path(__file__).parent.parent / "data" / "ogiri.db"


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        """Ensure the data directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                answer TEXT,
                prompt_file TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                answer_sent BOOLEAN DEFAULT FALSE
            )
            """
        )
        conn.commit()
        conn.close()

    def save_topic(self, topic: str, prompt_file: str) -> int:
        """
        Save a new topic and return its ID.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO topics (topic, prompt_file) VALUES (?, ?)",
            (topic, prompt_file),
        )
        topic_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return topic_id

    def save_answer(self, topic_id: int, answer: str):
        """
        Save generated answer for a specific topic.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE topics SET answer = ? WHERE id = ?",
            (answer, topic_id),
        )
        conn.commit()
        conn.close()

    def get_unsent_answer(self) -> Optional[Tuple[int, str, str]]:
        """
        Get the oldest unsent answer.
        Returns (id, topic, answer) or None.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, topic, answer
            FROM topics
            WHERE answer_sent = FALSE
            AND answer IS NOT NULL
            ORDER BY created_at ASC
            LIMIT 1
            """
        )
        result = cursor.fetchone()
        conn.close()
        return result

    def mark_answer_sent(self, topic_id: int):
        """
        Mark a topic's answer as sent.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE topics SET answer_sent = TRUE WHERE id = ?",
            (topic_id,),
        )
        conn.commit()
        conn.close()

    def get_all_topics(self) -> List[Tuple]:
        """
        Get all topics history.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM topics ORDER BY created_at DESC")
        results = cursor.fetchall()
        conn.close()
        return results
