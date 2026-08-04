"""
app.graph — LangGraph pipeline

Responsibilities:
  - Define the shared agent state (a TypedDict that flows through every node).
  - Declare each graph node as a plain Python function that accepts and returns
    the state dict.
  - Wire nodes and edges into a compiled LangGraph StateGraph.
  - Expose a single `run(question: str) -> dict` entry-point used by callers.

Nodes (planned, in execution order):
  1. parse_question   — attach the raw question to state; detect obvious errors.
  2. generate_sql     — call the LLM (via services.py) to produce a SQL query.
  3. validate_sql     — check the SQL is a safe SELECT before touching the DB.
  4. execute_sql      — run the validated query via db.py; store rows in state.
  5. format_answer    — call the LLM again to turn raw rows into a human answer.

Routing:
  - After validate_sql: if validation fails → loop back to generate_sql (up to N
    retries), then surface an error to the user.
  - After execute_sql: if DB returns no rows → short-circuit to format_answer
    with an "empty result" signal so the LLM can say "no results found".

This module must NOT import app.services directly; the LLM callable is injected
via the graph's config dict so that tests can swap in a stub.
"""
