"""
tests/test_flow.py — pytest integration tests for the LangGraph pipeline
"""

import io
import json
from unittest.mock import patch

import pytest

from app.graph import run
from app import tracing


# ---------------------------------------------------------------------------
# Shared fixture — run the pipeline once per module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pipeline_result():
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
    try:
        run(question)
    except Exception as exc:
        pytest.fail(f"run({question!r:.40}) raised unexpectedly: {exc}")
