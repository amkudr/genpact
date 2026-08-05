"""
app.db — Database layer (Phase 2: real SQLite in-memory backend)

Responsibilities:
  - Define the university schema as CREATE TABLE statements.
  - Seed the in-memory SQLite database from the DATA dict on first access
    (lazy singleton — import stays instant, DB is built only when needed).
  - Expose execute_readonly_sql(sql) that runs any SELECT and returns
    a list of plain dicts, identical contract to the Phase-1 stub.

No new dependencies: sqlite3 ships with Python's standard library.
"""

from __future__ import annotations  # enables X | None syntax on Python 3.9

import sqlite3

# ---------------------------------------------------------------------------
# Section 1 — Seed data (single source of truth)
# ---------------------------------------------------------------------------

DATA: dict[str, list[dict]] = {
    "students": [
        {"id": 1, "name": "Alice Smith",  "email": "alice@uni.edu"},
        {"id": 2, "name": "Bob Jones",    "email": "bob@uni.edu"},
        {"id": 3, "name": "Carol White",  "email": "carol@uni.edu"},
    ],
    "teachers": [
        {"id": 1, "name": "Dr. Evans",  "department": "Computer Science"},
        {"id": 2, "name": "Dr. Patel",  "department": "Mathematics"},
    ],
    "courses": [
        {"id": 1, "code": "CS101", "title": "Database Systems", "credits": 3},
        {"id": 2, "code": "MA201", "title": "Linear Algebra",   "credits": 4},
    ],
    "offerings": [
        {"id": 1, "course_id": 1, "teacher_id": 1, "semester": "Spring", "year": 2024},
        {"id": 2, "course_id": 2, "teacher_id": 2, "semester": "Spring", "year": 2024},
    ],
    "enrollments": [
        {"id": 1, "student_id": 1, "offering_id": 1, "grade": "A"},
        {"id": 2, "student_id": 2, "offering_id": 1, "grade": "A"},
        {"id": 3, "student_id": 3, "offering_id": 2, "grade": "B"},
    ],
}

# ---------------------------------------------------------------------------
# Section 1b — Schema DDL (mirrors the DATA dict structure)
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id      INTEGER PRIMARY KEY,
    name    TEXT    NOT NULL,
    email   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS teachers (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL,
    department TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    id      INTEGER PRIMARY KEY,
    code    TEXT    NOT NULL,
    title   TEXT    NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS offerings (
    id         INTEGER PRIMARY KEY,
    course_id  INTEGER NOT NULL REFERENCES courses(id),
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    semester   TEXT    NOT NULL,
    year       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    id          INTEGER PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES students(id),
    offering_id INTEGER NOT NULL REFERENCES offerings(id),
    grade       TEXT    NOT NULL
);
"""

# ---------------------------------------------------------------------------
# Section 2 — Lazy singleton connection
# ---------------------------------------------------------------------------

_conn: sqlite3.Connection | None = None


def _get_connection() -> sqlite3.Connection:
    """Return the shared in-memory SQLite connection, creating it on first call.

    Thread-safety note: for a single-threaded CLI this module-level singleton
    is fine. For concurrent web-server use, switch to a thread-local or
    connection-pool strategy.
    """
    global _conn
    if _conn is not None:
        return _conn

    # Open an in-memory database — zero filesystem side-effects.
    _conn = sqlite3.connect(":memory:", check_same_thread=False)
    # Rows returned as sqlite3.Row objects (subscriptable by column name).
    _conn.row_factory = sqlite3.Row
    # Enforce foreign-key constraints so bad seed data surfaces immediately.
    _conn.execute("PRAGMA foreign_keys = ON")
    # Create all tables.
    _conn.executescript(SCHEMA_SQL)

    # Seed every table from the DATA dict.
    for table, rows in DATA.items():
        if not rows:  # pragma: no cover
            continue
        cols = ", ".join(rows[0].keys())
        placeholders = ", ".join("?" * len(rows[0]))
        _conn.executemany(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
            [list(row.values()) for row in rows],
        )

    _conn.commit()
    return _conn


# ---------------------------------------------------------------------------
# Section 3 — Public API
# ---------------------------------------------------------------------------

def execute_readonly_sql(sql: str) -> list[dict]:
    """Execute a SELECT statement against the in-memory SQLite DB.

    Args:
        sql: A SQL SELECT statement to execute.

    Returns:
        A list of row dicts (column-name → value).

    Raises:
        ValueError: If the statement is not a SELECT.
        sqlite3.Error: If the SQL is syntactically invalid or references
                       unknown tables/columns.
    """
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT statements are allowed")

    conn = _get_connection()
    cursor = conn.execute(sql)
    # Convert sqlite3.Row objects to plain dicts so callers have no
    # dependency on the sqlite3 module.
    return [dict(row) for row in cursor.fetchall()]


