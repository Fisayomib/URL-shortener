import os
import sqlite3
from pathlib import Path

import psycopg
from dotenv import load_dotenv


project_folder = Path(__file__).parent
load_dotenv(project_folder / ".env")

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL is missing from .env")

sqlite_path = project_folder / "shortlinks.db"

with sqlite3.connect(sqlite_path) as local_db:
    columns = {
        row[1] for row in local_db.execute("PRAGMA table_info(links)")
    }
    required_columns = {"code", "long_url", "owner_id"}

    if not required_columns.issubset(columns):
        raise RuntimeError(
            "The local links table is missing a required column."
        )

    links = local_db.execute(
        "SELECT code, long_url, owner_id FROM links ORDER BY rowid"
    ).fetchall()

migrated_count = 0

with psycopg.connect(database_url) as postgres_db:
    postgres_db.execute("""
        CREATE TABLE IF NOT EXISTS links (
            code TEXT PRIMARY KEY,
            long_url TEXT NOT NULL,
            owner_id TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for code, long_url, owner_id in links:
        cursor = postgres_db.execute(
            """
            INSERT INTO links (code, long_url, owner_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            (code, long_url, owner_id),
        )
        migrated_count += cursor.rowcount

print(f"Copied {migrated_count} link(s) to Neon.")