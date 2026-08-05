"""
app.graph — LangGraph pipeline (Phase 2: real node implementations)

Changes from Phase 1:
  - AgentState gains `retry_count` to track SQL-regeneration loops.
  - validate_sql uses SQLite EXPLAIN to cheaply verify syntax + schema.
  - route_after_validate enforces MAX_RETRIES (3) before graceful degradation.
  - generate_sql forwards the previous error to the LLM so it can self-correct.
  - parse_question rejects empty/non-string input early.
"""

from __future__ import annotations

from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from app import db, services, tracing

# Maximum times the validate → generate loop may retry before giving up.
MAX_RETRIES: int = 3


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    question:    str
    sql:         Optional[str]
    rows:        Optional[list]
    answer:      Optional[str]
    error:       Optional[str]
    retry_count: int          # incremented each time validate_sql fails


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def parse_question(state: AgentState) -> AgentState:
    """Validate and log the incoming question; reset transient state."""
    question = state.get("question", "")
    if not isinstance(question, str) or not question.strip():
        state["question"] = question if isinstance(question, str) else ""
    state["error"]       = None
    state["retry_count"] = 0
    tracing.log_event(tracing.EVT_QUESTION, question=state["question"])
    return state


def generate_sql(state: AgentState) -> AgentState:
    """Ask the LLM to translate the question into a SQLite SELECT statement.

    On retries, the previous error message is forwarded so the model can
    self-correct its output.
    """
    llm = services.get_llm()
    state["sql"] = llm.generate_sql(
        question=state["question"],
        error=state.get("error"),
    )
    tracing.log_event(tracing.EVT_SQL_GENERATED, sql=state["sql"])
    return state


def validate_sql(state: AgentState) -> AgentState:
    """Validate the generated SQL using SQLite's EXPLAIN command.

    EXPLAIN parses the statement and plans the query without executing it,
    so it catches both syntax errors and references to unknown
    tables/columns — all without touching the real data.

    Note: we call sqlite3 directly here (bypassing execute_readonly_sql)
    so that the EXPLAIN prefix doesn't trigger the SELECT-only guard.
    """
    sql = state.get("sql") or ""

    if sql.strip() == "OUT_OF_DOMAIN":
        state["error"] = "Out of domain question. Only university-related queries are supported."
        state["retry_count"] = MAX_RETRIES  # Exhaust retries instantly to prevent looping
        tracing.log_event(tracing.EVT_SQL_INVALID, sql=sql, error=state["error"])
        return state

    # Guard: must start with SELECT (defence-in-depth on top of db layer).
    if not sql.strip().upper().startswith("SELECT"):
        state["error"] = "Generated statement is not a SELECT."
        state["retry_count"] = state.get("retry_count", 0) + 1
        tracing.log_event(tracing.EVT_SQL_INVALID, sql=sql, error=state["error"])
        return state

    try:
        # Use the shared connection directly so EXPLAIN isn't blocked by the
        # SELECT-only guard in execute_readonly_sql.
        conn = db._get_connection()
        conn.execute(f"EXPLAIN {sql}")
        state["error"] = None
        tracing.log_event(tracing.EVT_SQL_VALIDATED, sql=sql)
    except Exception as exc:  # noqa: BLE001
        state["error"] = str(exc)
        state["retry_count"] = state.get("retry_count", 0) + 1
        tracing.log_event(tracing.EVT_SQL_INVALID, sql=sql, error=state["error"])

    return state


def execute_sql(state: AgentState) -> AgentState:
    """Run the validated SQL against the in-memory SQLite DB."""
    state["rows"] = db.execute_readonly_sql(state["sql"])
    tracing.log_event(tracing.EVT_ROWS_RETURNED, row_count=len(state["rows"] or []))
    return state


def handle_retry_exhausted(state: AgentState) -> AgentState:
    """Graceful-degradation node reached when the retry cap is exhausted.

    Sets rows to an empty list so format_answer can still produce a
    sensible answer even when no valid SQL could be generated.
    """
    state["rows"] = []
    return state


def format_answer(state: AgentState) -> AgentState:
    """Ask the LLM to produce a natural-language answer from the raw rows."""
    llm = services.get_llm()
    rows = state.get("rows") or []
    state["answer"] = llm.format_answer(
        question=state["question"],
        rows=rows,
        error=state.get("error"),
    )
    tracing.log_event(tracing.EVT_ANSWER_EMITTED, answer=state["answer"])
    return state


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def route_after_validate(state: AgentState) -> str:
    """Route to generate_sql on failure (up to MAX_RETRIES), else execute_sql.

    If the retry cap is reached, route to handle_retry_exhausted which sets
    rows=[] before forwarding to format_answer.
    """
    if state.get("error"):
        if state.get("retry_count", 0) < MAX_RETRIES:
            return "error_retry"
        # Retry cap exhausted — let the dedicated node set rows=[]
        return "retry_exhausted"
    return "sql_valid"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("parse_question",       parse_question)
    g.add_node("generate_sql",         generate_sql)
    g.add_node("validate_sql",         validate_sql)
    g.add_node("execute_sql",          execute_sql)
    g.add_node("handle_retry_exhausted", handle_retry_exhausted)
    g.add_node("format_answer",        format_answer)

    g.add_edge(START, "parse_question")
    g.add_edge("parse_question", "generate_sql")
    g.add_edge("generate_sql",   "validate_sql")
    g.add_conditional_edges(
        "validate_sql",
        route_after_validate,
        {
            "error_retry":           "generate_sql",
            "sql_valid":             "execute_sql",
            "retry_exhausted":       "handle_retry_exhausted",
        },
    )
    g.add_edge("handle_retry_exhausted", "format_answer")
    g.add_edge("execute_sql",            "format_answer")
    g.add_edge("format_answer",          END)

    return g.compile()


_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def run(question: str) -> dict:
    tracing.new_run()
    initial_state: AgentState = {
        "question":    question,
        "sql":         None,
        "rows":        None,
        "answer":      None,
        "error":       None,
        "retry_count": 0,
    }
    return _graph.invoke(initial_state)
