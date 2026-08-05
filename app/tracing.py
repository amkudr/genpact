"""
app.tracing — Observability layer

Responsibilities:
  - Emit a structured JSON log line to stderr for every significant agent event
    (question received, SQL generated, SQL validated, rows returned, answer
    emitted, errors).  This is the always-on, zero-dependency fallback.
  - Optionally configure LangSmith tracing when `LANGSMITH_API_KEY` is present
    in the environment.  LangSmith integration must be entirely opt-in: if the
    env var is missing the app must work identically without it.
  - Expose a single `log_event(event_name, payload)` function that the graph
    nodes call.  Callers must never import `langsmith` directly.

Structured log format (one JSON object per line):
  {
    "ts":    "<ISO-8601 timestamp>",
    "event": "<event_name>",
    "run_id": "<UUID shared across one user question>",
    ...payload fields...
  }
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Event name constants
# ---------------------------------------------------------------------------

EVT_QUESTION       = "question_received"
EVT_SQL_GENERATED  = "sql_generated"
EVT_SQL_VALIDATED  = "sql_validated"
EVT_SQL_INVALID    = "sql_invalid"
EVT_ROWS_RETURNED  = "rows_returned"
EVT_ANSWER_EMITTED = "answer_emitted"
EVT_ERROR          = "error"


# ---------------------------------------------------------------------------
# run_id — module-level, shared across all nodes for one question
#
# TODO (thread-safety): This module-level variable is fine for single-threaded
#   CLI use. For concurrent requests (e.g., a web server), replace with a
#   contextvars.ContextVar so each request gets its own isolated run_id:
#
#     import contextvars
#     _run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="unset")
#
#     def new_run() -> str:
#         rid = str(uuid.uuid4())
#         _run_id_var.set(rid)
#         return rid
#
#     def _current_run_id() -> str:
#         return _run_id_var.get()
# ---------------------------------------------------------------------------

_run_id: str = "unset"


def new_run() -> str:
    """Generate and store a new run_id. Call once at the start of each question."""
    global _run_id
    _run_id = str(uuid.uuid4())
    return _run_id


def _current_run_id() -> str:
    return _run_id


# ---------------------------------------------------------------------------
# LangSmith opt-in (configured at import time, before the graph is built)
# ---------------------------------------------------------------------------

def _configure_langsmith() -> None:
    """Enable LangSmith tracing if LANGSMITH_API_KEY is present in the environment.

    Sets the env vars that LangGraph/LangChain reads automatically so that the
    rest of the codebase never needs to import `langsmith` directly.
    """
    api_key = os.environ.get("LANGSMITH_API_KEY")
    if not api_key:
        return  # opt-in not triggered — app works identically without it

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", "university-sql-agent")


_configure_langsmith()


# ---------------------------------------------------------------------------
# Public logging API
# ---------------------------------------------------------------------------

def log_event(event_name: str, **payload) -> None:
    """Emit a single structured JSON log line to stderr.

    Args:
        event_name: One of the EVT_* constants defined in this module.
        **payload:  Arbitrary key-value pairs to include in the log record.

    Example output:
        {"ts": "2026-08-05T10:32:00Z", "event": "sql_generated",
         "run_id": "abc-123", "sql": "SELECT * FROM enrollments"}
    """
    record = {
        "ts":     datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event":  event_name,
        "run_id": _current_run_id(),
        **payload,
    }
    print(json.dumps(record, default=str), file=sys.stderr)
