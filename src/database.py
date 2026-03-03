from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "ogiri.db"

# Columns to add when migrating an existing database
_MIGRATION_COLUMNS: dict[str, str] = {
    "model_used":     "TEXT",
    "format_hint":    "TEXT",
    "creative_angle": "TEXT",
    "answer_model":   "TEXT",
    "channel_id":     "TEXT",
    "slack_ts":       "TEXT",
    "sent_at":        "DATETIME",
}


@dataclass
class TopicRecord:
    id: int
    topic: str
    answer: str | None
    created_at: str
    sent_at: str | None


class Database:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._migrate_db()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a connection that auto-commits on success and rolls back on error."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create the topics table if it does not exist."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS topics (
                    id             INTEGER  PRIMARY KEY AUTOINCREMENT,
                    topic          TEXT     NOT NULL,
                    prompt_file    TEXT     NOT NULL,
                    model_used     TEXT,
                    format_hint    TEXT,
                    creative_angle TEXT,
                    answer         TEXT,
                    answer_model   TEXT,
                    channel_id     TEXT,
                    slack_ts       TEXT,
                    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sent_at        DATETIME,
                    answer_sent    BOOLEAN  DEFAULT FALSE
                )
                """
            )

    def _migrate_db(self) -> None:
        """Add columns introduced after the initial schema (idempotent)."""
        with self._connect() as conn:
            existing = {row["name"] for row in conn.execute("PRAGMA table_info(topics)")}
            for col, col_type in _MIGRATION_COLUMNS.items():
                if col not in existing:
                    conn.execute(f"ALTER TABLE topics ADD COLUMN {col} {col_type}")
                    logger.info("DB migration: added column '%s %s'", col, col_type)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def save_topic(
        self,
        topic: str,
        prompt_file: str,
        *,
        model_used: str | None = None,
        format_hint: str | None = None,
        creative_angle: str | None = None,
    ) -> int:
        """Insert a new topic row and return its auto-generated ID."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO topics (topic, prompt_file, model_used, format_hint, creative_angle)
                VALUES (?, ?, ?, ?, ?)
                """,
                (topic, prompt_file, model_used, format_hint, creative_angle),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def save_slack_info(self, topic_id: int, channel_id: str, slack_ts: str) -> None:
        """Persist the Slack channel and message timestamp for a topic."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE topics SET channel_id = ?, slack_ts = ? WHERE id = ?",
                (channel_id, slack_ts, topic_id),
            )

    def save_answer(
        self,
        topic_id: int,
        answer: str,
        answer_model: str | None = None,
    ) -> None:
        """Persist the generated model answer for a topic."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE topics SET answer = ?, answer_model = ? WHERE id = ?",
                (answer, answer_model, topic_id),
            )

    def mark_answer_sent(self, topic_id: int) -> None:
        """Mark a topic's answer as sent and record the UTC timestamp."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE topics SET answer_sent = TRUE, sent_at = ? WHERE id = ?",
                (now, topic_id),
            )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_unsent_answer(self) -> TopicRecord | None:
        """Return the oldest topic whose answer is ready but not yet sent."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, topic, answer, created_at, sent_at
                FROM topics
                WHERE answer_sent = FALSE AND answer IS NOT NULL
                ORDER BY created_at ASC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return TopicRecord(
            id=row["id"],
            topic=row["topic"],
            answer=row["answer"],
            created_at=row["created_at"],
            sent_at=row["sent_at"],
        )

    def get_recent_topics(self, limit: int = 20) -> list[str]:
        """Return the *limit* most recent topic texts (newest first)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT topic FROM topics ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [row["topic"] for row in rows]

    def get_all_topics(self) -> list[sqlite3.Row]:
        """Return every topic row ordered newest-first."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM topics ORDER BY created_at DESC"
            ).fetchall()
