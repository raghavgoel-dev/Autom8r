"""Raw-SQLite data layer for the MCP server.

WHY stdlib sqlite3 instead of SQLAlchemy here?
  WHAT: parameterized SQL written by hand.
  WHY: the backend demonstrates the ORM style; this side demonstrates the
       raw-SQL style against the SAME schema. Two data-access idioms, one
       database — a deliberate teaching contrast (docs explain it).
  TRADEOFF: the DDL below must stay in sync with the ORM model. The MCP test
       suite pins the column list so drift fails loudly.

CRITICAL FORMAT CONTRACT: the backend writes datetimes through SQLAlchemy's
SQLite DATETIME type, whose storage format is 'YYYY-MM-DD HH:MM:SS.ffffff'
(space-separated, UTC). We write the exact same format so rows created by
EITHER side read correctly on the other.
"""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "autom8r.db"

# Mirrors backend/app/models/lead.py exactly (drift is caught by tests).
_DDL = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(120) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    city VARCHAR(120),
    business_type VARCHAR(120),
    budget VARCHAR(120),
    requirement TEXT,
    timeline VARCHAR(120),
    monthly_queries INTEGER,
    lead_score INTEGER NOT NULL DEFAULT 0,
    priority VARCHAR(10) NOT NULL DEFAULT 'low',
    status VARCHAR(20) NOT NULL DEFAULT 'new',
    source VARCHAR(50) NOT NULL DEFAULT 'api',
    created_at DATETIME,
    updated_at DATETIME
)
"""
_INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_leads_phone ON leads (phone)",
    "CREATE INDEX IF NOT EXISTS ix_leads_email ON leads (email)",
    "CREATE INDEX IF NOT EXISTS ix_leads_status ON leads (status)",
    "CREATE INDEX IF NOT EXISTS ix_leads_priority ON leads (priority)",
)

COLUMNS = (
    "id", "name", "phone", "email", "city", "business_type", "budget",
    "requirement", "timeline", "monthly_queries", "lead_score", "priority",
    "status", "source", "created_at", "updated_at",
)


def _now() -> str:
    """UTC now in SQLAlchemy's SQLite DATETIME storage format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


class LeadStore:
    """Minimal, explicit lead persistence used by the MCP tools."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self.ensure_table()

    @classmethod
    def from_env(cls) -> "LeadStore":
        """Resolve the DB path: AUTOM8R_DB_PATH env, else the repo default."""
        override = os.environ.get("AUTOM8R_DB_PATH", "")
        return cls(Path(override) if override else DEFAULT_DB_PATH)

    def _connect(self) -> sqlite3.Connection:
        """Open a WAL-mode connection with a busy timeout.

        WAL + busy_timeout let this process share the file with the FastAPI
        backend without 'database is locked' errors.
        """
        conn = sqlite3.connect(self._db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=15000")
        return conn

    def ensure_table(self) -> None:
        """Create the leads table + indexes if they do not exist."""
        with self._connect() as conn:
            conn.execute(_DDL)
            for index in _INDEXES:
                conn.execute(index)

    def create_lead(self, fields: dict[str, object], score: int, priority: str) -> dict[str, object]:
        """Insert one lead and return the full row as a dict."""
        now = _now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO leads (
                    name, phone, email, city, business_type, budget,
                    requirement, timeline, monthly_queries, lead_score,
                    priority, status, source, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?)
                """,
                (
                    fields.get("name"), fields.get("phone"), fields.get("email"),
                    fields.get("city"), fields.get("business_type"),
                    fields.get("budget"), fields.get("requirement"),
                    fields.get("timeline"), fields.get("monthly_queries"),
                    score, priority, fields.get("source", "chat"), now, now,
                ),
            )
            row = conn.execute(
                f"SELECT {', '.join(COLUMNS)} FROM leads WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return dict(row)

    def search_leads(self, query: str, limit: int = 20) -> list[dict[str, object]]:
        """Substring search over phone and name, newest first."""
        pattern = f"%{query.strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT {', '.join(COLUMNS)} FROM leads
                WHERE phone LIKE ? OR name LIKE ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (pattern, pattern, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_lead(
        self, phone: str, fields: dict[str, object], score: int, priority: str
    ) -> dict[str, object] | None:
        """Update the newest lead with this phone; None when not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM leads WHERE phone = ? ORDER BY created_at DESC LIMIT 1",
                (phone,),
            ).fetchone()
            if row is None:
                return None
            assignments = ", ".join(f"{column} = ?" for column in fields)
            values = [*fields.values(), score, priority, _now(), row["id"]]
            conn.execute(
                f"UPDATE leads SET {assignments}, lead_score = ?, "
                f"priority = ?, updated_at = ? WHERE id = ?",
                values,
            )
            updated = conn.execute(
                f"SELECT {', '.join(COLUMNS)} FROM leads WHERE id = ?",
                (row["id"],),
            ).fetchone()
        return dict(updated)
