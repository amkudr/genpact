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
