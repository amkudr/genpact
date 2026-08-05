"""
app.graph — LangGraph pipeline (Phase 1: skeleton nodes)
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from app import db, services, tracing


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    question: str
    sql:      Optional[str]
    rows:     Optional[list]
    answer:   Optional[str]
    error:    Optional[str]


# ---------------------------------------------------------------------------
# Nodes (skeletons — bodies to be filled one-by-one)
# ---------------------------------------------------------------------------

def parse_question(state: AgentState) -> AgentState:
    # TODO: parse intent, extract entities, detect obvious errors
    tracing.log_event(tracing.EVT_QUESTION, question=state["question"])
    return state


def generate_sql(state: AgentState) -> AgentState:
    # TODO: build real prompt and call llm.generate_sql(question)
    llm = services.get_llm()
    state["sql"] = llm.generate_sql(state["question"])
    tracing.log_event(tracing.EVT_SQL_GENERATED, sql=state["sql"])
    return state


def validate_sql(state: AgentState) -> AgentState:
    # TODO: real SQL validation (syntax + schema check)
    state["error"] = None  # assume valid for now
    if state.get("error"):
        tracing.log_event(tracing.EVT_SQL_INVALID, sql=state["sql"], error=state["error"])
    else:
        tracing.log_event(tracing.EVT_SQL_VALIDATED, sql=state["sql"])
    return state


def execute_sql(state: AgentState) -> AgentState:
    # TODO: pass real SQL once generate_sql is implemented
    state["rows"] = db.execute_readonly_sql(state["sql"])
    tracing.log_event(tracing.EVT_ROWS_RETURNED, row_count=len(state["rows"] or []))
    return state


def format_answer(state: AgentState) -> AgentState:
    # TODO: build real prompt and call llm.format_answer(question, rows)
    llm = services.get_llm()
    state["answer"] = llm.format_answer(state["question"], state["rows"] or [])
    tracing.log_event(tracing.EVT_ANSWER_EMITTED, answer=state["answer"])
    return state


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def route_after_validate(state: AgentState) -> str:
    # TODO: return "generate_sql" on invalid SQL (with retry cap)
    if state.get("error"):
        return "generate_sql"
    return "execute_sql"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("parse_question", parse_question)
    g.add_node("generate_sql",   generate_sql)
    g.add_node("validate_sql",   validate_sql)
    g.add_node("execute_sql",    execute_sql)
    g.add_node("format_answer",  format_answer)

    g.set_entry_point("parse_question")
    g.add_edge("parse_question", "generate_sql")
    g.add_edge("generate_sql",   "validate_sql")
    g.add_conditional_edges("validate_sql", route_after_validate)
    g.add_edge("execute_sql",    "format_answer")
    g.add_edge("format_answer",  END)

    return g.compile()


_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def run(question: str) -> dict:
    tracing.new_run()
    initial_state: AgentState = {
        "question": question,
        "sql":      None,
        "rows":     None,
        "answer":   None,
        "error":    None,
    }
    return _graph.invoke(initial_state)
