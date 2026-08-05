"""
app.services — LLM configuration (Phase 2: real ChatOpenAI backend)

Responsibilities:
  - Define SQL_GENERATION_PROMPT — instructs the model to emit a single,
    valid SQLite SELECT statement for the university schema, with no markdown.
  - Define ANSWER_FORMAT_PROMPT — instructs the model to convert raw DB rows
    into a concise natural-language answer.
  - Expose RealLLM, which wraps ChatOpenAI and calls these prompts.
  - Expose _MockLLM (private) so tests can patch get_llm() without hitting
    the real API.
  - Expose get_llm() as the single factory that the graph nodes call.
"""

from __future__ import annotations

import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


# ---------------------------------------------------------------------------
# Section 1 — Schema description embedded in the SQL generation prompt
# ---------------------------------------------------------------------------

_SCHEMA_DESCRIPTION = """
Tables and columns (SQLite):

  students    (id INTEGER PK, name TEXT, email TEXT)
  teachers    (id INTEGER PK, name TEXT, department TEXT)
  courses     (id INTEGER PK, code TEXT, title TEXT, credits INTEGER)
  offerings   (id INTEGER PK, course_id → courses.id,
                teacher_id → teachers.id, semester TEXT, year INTEGER)
  enrollments (id INTEGER PK, student_id → students.id,
                offering_id → offerings.id, grade TEXT)

Sample values:
  - semesters: 'Spring', 'Fall'
  - grades:    'A', 'B', 'C', …
  - year:      integer, e.g. 2024
""".strip()


# ---------------------------------------------------------------------------
# Section 2 — Prompts
# ---------------------------------------------------------------------------

SQL_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are an expert SQLite query writer for a university database.\n"
            "Given a natural-language question, produce exactly ONE valid SQLite "
            "SELECT statement — no markdown, no code fences, no explanation.\n\n"
            "Schema:\n{schema}"
        ),
    ),
    (
        "human",
        "Question: {question}\n\nPrevious error (if any): {error}\n\nSQL:",
    ),
])

ANSWER_FORMAT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are a helpful assistant that turns database query results into "
            "clear, concise natural-language answers. "
            "Use the raw rows provided and the original question to write a "
            "short, direct answer. Do not mention SQL."
        ),
    ),
    (
        "human",
        "Question: {question}\n\nQuery results (list of dicts): {rows}\n\nAnswer:",
    ),
])


# ---------------------------------------------------------------------------
# Section 3 — LLM implementations
# ---------------------------------------------------------------------------

class RealLLM:
    """Wraps ChatOpenAI and calls the two prompts via LangChain chains."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Copy .env.example → .env and add your key there."
            )
        # Pass the key directly to ChatOpenAI — never store it on self or log it.
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,   # consumed internally by the SDK; not stored as plain attr
        )
        self._sql_chain    = SQL_GENERATION_PROMPT | self._llm | StrOutputParser()
        self._answer_chain = ANSWER_FORMAT_PROMPT  | self._llm | StrOutputParser()


    def generate_sql(self, question: str, error: str | None = None) -> str:
        """Translate a natural-language question into a SQLite SELECT statement."""
        return self._sql_chain.invoke({
            "schema":   _SCHEMA_DESCRIPTION,
            "question": question,
            "error":    error or "none",
        }).strip()

    def format_answer(self, question: str, rows: list[dict]) -> str:
        """Convert raw DB rows into a natural-language answer."""
        return self._answer_chain.invoke({
            "question": question,
            "rows":     rows,
        }).strip()


class _MockLLM:
    """Deterministic stub — used by tests that patch get_llm().

    Returns a valid SELECT that the real in-memory SQLite DB can execute,
    producing ≥ 1 rows for the standard 'grade A' question so all assertions
    in test_flow.py pass without touching the OpenAI API.
    """

    _SQL = (
        "SELECT s.name AS student, c.title AS course, e.grade "
        "FROM enrollments e "
        "JOIN students  s ON s.id = e.student_id "
        "JOIN offerings o ON o.id = e.offering_id "
        "JOIN courses   c ON c.id = o.course_id "
        "WHERE e.grade = 'A'"
    )

    def generate_sql(self, question: str, error: str | None = None) -> str:  # noqa: ARG002
        return self._SQL

    def format_answer(self, question: str, rows: list[dict]) -> str:  # noqa: ARG002
        return f"Found {len(rows)} result(s) for: '{question}'."


# ---------------------------------------------------------------------------
# Section 4 — Public factory
# ---------------------------------------------------------------------------

def get_llm() -> RealLLM:
    """Return the production LLM client.

    Tests should patch this function:
        with patch("app.services.get_llm", return_value=_MockLLM()):
            ...
    """
    return RealLLM()
