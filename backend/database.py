import json
import sqlite3
from contextlib import closing
from pathlib import Path

from backend.schemas import TicketAnalysis, TicketRequest


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "tickets.db"


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    with closing(get_connection()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                category_hint TEXT,
                status TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def save_ticket(
    ticket_id: str,
    ticket: TicketRequest,
    status: str,
    analysis: TicketAnalysis,
):
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO tickets (
                ticket_id,
                subject,
                message,
                category_hint,
                status,
                analysis_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                ticket.subject,
                ticket.message,
                ticket.category_hint,
                status,
                json.dumps(
                    analysis.model_dump(mode="json"),
                    ensure_ascii=False,
                ),
            ),
        )
        conn.commit()


def list_tickets(limit: int = 50):
    limit = max(1, min(limit, 100))

    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM tickets
            ORDER BY created_at DESC, rowid DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "ticket_id": row["ticket_id"],
            "subject": row["subject"],
            "message": row["message"],
            "category_hint": row["category_hint"],
            "status": row["status"],
            "analysis": json.loads(row["analysis_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
def update_ticket_status(ticket_id: str, status: str) -> bool:
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE tickets
            SET status = ?
            WHERE ticket_id = ?
            """,
            (status, ticket_id),
        )
        conn.commit()

        return cursor.rowcount > 0