"""
tests/test_db.py — pytest tests for app.db (SQLite backend)
"""

import sqlite3

import pytest

from app.db import DATA, execute_readonly_sql


# ---------------------------------------------------------------------------
# Seeding — every table must have the same row count as DATA
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("table", ["students", "teachers", "courses", "offerings", "enrollments"])
def test_table_row_count_matches_data(table):
    rows = execute_readonly_sql(f"SELECT * FROM {table}")
    assert len(rows) == len(DATA[table])


# ---------------------------------------------------------------------------
# Return type — list of plain dicts
# ---------------------------------------------------------------------------

def test_returns_list():
    result = execute_readonly_sql("SELECT * FROM students")
    assert isinstance(result, list)


def test_rows_are_plain_dicts():
    result = execute_readonly_sql("SELECT * FROM students")
    for row in result:
        assert isinstance(row, dict)


def test_student_row_has_expected_keys():
    row = execute_readonly_sql("SELECT * FROM students")[0]
    assert "id"    in row
    assert "name"  in row
    assert "email" in row


# ---------------------------------------------------------------------------
# Security — only SELECT is allowed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_sql", [
    "INSERT INTO students (id, name, email) VALUES (99, 'X', 'x@x.com')",
    "UPDATE students SET name='hacked' WHERE id=1",
    "DELETE FROM students WHERE id=1",
    "DROP TABLE students",
])
def test_non_select_raises_value_error(bad_sql):
    with pytest.raises(ValueError, match="Only SELECT"):
        execute_readonly_sql(bad_sql)


# ---------------------------------------------------------------------------
# Invalid SQL — must raise sqlite3.OperationalError
# ---------------------------------------------------------------------------

def test_unknown_table_raises():
    with pytest.raises(sqlite3.OperationalError):
        execute_readonly_sql("SELECT * FROM nonexistent_table")


def test_unknown_column_raises():
    with pytest.raises(sqlite3.OperationalError):
        execute_readonly_sql("SELECT ghost_column FROM students")


# ---------------------------------------------------------------------------
# Join query — realistic multi-table SELECT
# ---------------------------------------------------------------------------

GRADE_A_QUERY = """
    SELECT s.name AS student, c.title AS course, e.grade
    FROM   enrollments e
    JOIN   students  s ON s.id = e.student_id
    JOIN   offerings o ON o.id = e.offering_id
    JOIN   courses   c ON c.id = o.course_id
    WHERE  c.title    = 'Database Systems'
      AND  o.semester = 'Spring'
      AND  o.year     = 2024
      AND  e.grade    = 'A'
    ORDER BY s.name
"""


@pytest.fixture(scope="module")
def grade_a_rows():
    return execute_readonly_sql(GRADE_A_QUERY)


def test_join_returns_two_rows(grade_a_rows):
    assert len(grade_a_rows) == 2


def test_join_contains_alice(grade_a_rows):
    names = [r["student"] for r in grade_a_rows]
    assert "Alice Smith" in names


def test_join_contains_bob(grade_a_rows):
    names = [r["student"] for r in grade_a_rows]
    assert "Bob Jones" in names


def test_join_excludes_carol(grade_a_rows):
    names = [r["student"] for r in grade_a_rows]
    assert "Carol White" not in names  # Carol has grade B


def test_join_all_grades_are_a(grade_a_rows):
    assert all(r["grade"] == "A" for r in grade_a_rows)


# ---------------------------------------------------------------------------
# Aggregation query (Requirement: averages, counts)
# ---------------------------------------------------------------------------

AGGREGATION_QUERY = """
    SELECT COUNT(e.id) AS total_enrollments
    FROM   enrollments e
    JOIN   offerings o ON o.id = e.offering_id
    WHERE  o.semester = 'Spring'
      AND  o.year     = 2024
"""

def test_aggregation_returns_correct_count():
    rows = execute_readonly_sql(AGGREGATION_QUERY)
    assert len(rows) == 1
    # DATA dict has 3 enrollments total, all in Spring 2024
    assert rows[0]["total_enrollments"] == 3


# ---------------------------------------------------------------------------
# Multi-step reasoning (Requirement: complex joins across domains)
# "Find the teacher who taught Carol White"
# ---------------------------------------------------------------------------

MULTI_STEP_QUERY = """
    SELECT DISTINCT t.name AS teacher
    FROM   teachers t
    JOIN   offerings o   ON o.teacher_id = t.id
    JOIN   enrollments e ON e.offering_id = o.id
    JOIN   students s    ON s.id = e.student_id
    WHERE  s.name = 'Carol White'
"""

def test_multi_step_reasoning_returns_correct_teacher():
    rows = execute_readonly_sql(MULTI_STEP_QUERY)
    assert len(rows) == 1
    # Carol White is in offering 2, taught by teacher 2 (Dr. Patel)
    assert rows[0]["teacher"] == "Dr. Patel"
