"""Reading and writing data.

If the environment variable DATABASE_URL is set, this module talks to that
PostgreSQL database. If it is not set, everything falls back to a list held in
memory that resets when the app restarts.

You do not have to choose. The app works either way, so you can build and run
locally with no database at all.
"""

import os
import threading
from datetime import datetime, timezone

DATABASE_URL = os.environ.get("DATABASE_URL")

_pool = None
_pool_lock = threading.Lock()

_memory = []
_memory_lock = threading.Lock()


def has_database():
    """True when a database is configured for this environment."""
    return bool(DATABASE_URL)


def _get_pool():
    global _pool
    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        # Imported here, not at the top of the file, so the app starts fine on a
        # machine where psycopg isn't installed and no database is in use.
        from psycopg_pool import ConnectionPool

        # Keep the pool small. The container has 0.25 vCPU; a big pool just
        # means more idle connections competing for it.
        pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=4, timeout=5.0)
        pool.wait(timeout=10.0)

        with pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id         SERIAL PRIMARY KEY,
                    body       TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

        _pool = pool
        return _pool


def init():
    """Called once at startup. Safe to call when there is no database."""
    if has_database():
        _get_pool()


def list_notes(limit=20):
    """Newest notes first."""
    if not has_database():
        with _memory_lock:
            return list(reversed(_memory[-limit:]))

    with _get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT id, body, created_at FROM notes ORDER BY id DESC LIMIT %s",
            (limit,),
        ).fetchall()

    return [{"id": r[0], "body": r[1], "created_at": r[2]} for r in rows]


def add_note(body):
    text = str(body or "").strip()[:500]
    if not text:
        raise ValueError("Note cannot be empty")

    if not has_database():
        with _memory_lock:
            note = {
                "id": len(_memory) + 1,
                "body": text,
                "created_at": datetime.now(timezone.utc),
            }
            _memory.append(note)
            return note

    with _get_pool().connection() as conn:
        row = conn.execute(
            "INSERT INTO notes (body) VALUES (%s) RETURNING id, body, created_at",
            (text,),
        ).fetchone()

    return {"id": row[0], "body": row[1], "created_at": row[2]}


def close():
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def _reset_for_tests():
    with _memory_lock:
        _memory.clear()
