"""
tests/test_flow.py — pytest integration tests for the LangGraph pipeline

All tests mock app.services.get_llm so the test suite never makes real
OpenAI API calls and remains fast + deterministic.
"""

import io
import json
from unittest.mock import patch, MagicMock

import pytest

from app.graph import run
from app import tracing
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

    def format_answer(self, question: str, rows: list[dict], error: str | None = None) -> str:  # noqa: ARG002
        return f"Found {len(rows)} result(s) for: '{question}'."


# ---------------------------------------------------------------------------
# Helper — a mock LLM that always returns invalid SQL (for retry-cap tests)
# ---------------------------------------------------------------------------

class _AlwaysInvalidLLM:
    def generate_sql(self, question: str, error=None) -> str:  # noqa: ARG002
        return "NOT VALID SQL AT ALL"

    def format_answer(self, question: str, rows: list, error: str | None = None) -> str:  # noqa: ARG002
        return f"Could not retrieve results for: '{question}'."


# ---------------------------------------------------------------------------
# Shared fixture — run the pipeline once per module (LLM is mocked)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pipeline_result():
    with patch("app.services.get_llm", return_value=_MockLLM()):
        return run("Which students got an A in Database Systems in Spring 2024?")


# ---------------------------------------------------------------------------
# Return shape
# ---------------------------------------------------------------------------

def test_run_returns_dict(pipeline_result):
    assert isinstance(pipeline_result, dict)


def test_result_has_answer_key(pipeline_result):
    assert "answer" in pipeline_result


def test_result_has_sql_key(pipeline_result):
    assert "sql" in pipeline_result


def test_result_has_rows_key(pipeline_result):
    assert "rows" in pipeline_result


def test_answer_is_non_empty_string(pipeline_result):
    assert isinstance(pipeline_result["answer"], str)
    assert len(pipeline_result["answer"]) > 0


def test_rows_is_list(pipeline_result):
    assert isinstance(pipeline_result["rows"], list)


def test_no_error_in_state(pipeline_result):
    assert pipeline_result.get("error") is None


# ---------------------------------------------------------------------------
# Answer content
# ---------------------------------------------------------------------------

def test_answer_mentions_result_count(pipeline_result):
    # _MockLLM.format_answer returns "Found N result(s) for: '...'."
    assert "result" in pipeline_result["answer"].lower()


def test_rows_non_empty(pipeline_result):
    assert len(pipeline_result["rows"]) > 0


# ---------------------------------------------------------------------------
# Tracing — all expected events must be emitted to stderr
# ---------------------------------------------------------------------------

EXPECTED_EVENTS = [
    tracing.EVT_QUESTION,
    tracing.EVT_SQL_GENERATED,
    tracing.EVT_SQL_VALIDATED,
    tracing.EVT_ROWS_RETURNED,
    tracing.EVT_ANSWER_EMITTED,
]


@pytest.fixture(scope="module")
def captured_log_records():
    """Run the pipeline with stderr captured; return parsed JSON records."""
    buf = io.StringIO()
    with patch("app.services.get_llm", return_value=_MockLLM()):
        with patch("sys.stderr", buf):
            run("Which students got an A in Database Systems in Spring 2024?")
    buf.seek(0)
    records = []
    for line in buf:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass  # skip non-JSON lines (e.g. deprecation warnings)
    return records


@pytest.mark.parametrize("event", EXPECTED_EVENTS)
def test_event_is_emitted(event, captured_log_records):
    emitted = {r.get("event") for r in captured_log_records}
    assert event in emitted, f"Event '{event}' was not emitted"


def test_all_log_records_have_run_id(captured_log_records):
    for record in captured_log_records:
        assert "run_id" in record
        assert record["run_id"] != "unset"


# ---------------------------------------------------------------------------
# Robustness — pipeline must not raise on unusual input
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "",
    "a" * 1000,
    "SELECT * FROM students",   # SQL-like input
    "🤔 what is the answer?",   # unicode
])
def test_run_does_not_raise(question):
    with patch("app.services.get_llm", return_value=_MockLLM()):
        try:
            run(question)
        except Exception as exc:
            pytest.fail(f"run({question!r:.40}) raised unexpectedly: {exc}")


# ---------------------------------------------------------------------------
# Retry-cap — pipeline must not raise and must return an answer even when
# the LLM always produces invalid SQL (graceful degradation path)
# ---------------------------------------------------------------------------

def test_sql_retry_cap_does_not_raise():
    """When the LLM always returns invalid SQL the pipeline degrades gracefully."""
    with patch("app.services.get_llm", return_value=_AlwaysInvalidLLM()):
        result = run("Which students got an A?")
    assert isinstance(result, dict)
    assert "answer" in result
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 0


def test_sql_retry_cap_returns_empty_rows():
    """After exhausting retries, rows should be empty (not None)."""
    with patch("app.services.get_llm", return_value=_AlwaysInvalidLLM()):
        result = run("Which students got an A?")
    assert result.get("rows") == []
