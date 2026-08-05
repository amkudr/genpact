"""
app.db — Database layer (Phase 1: dict-backed, no SQLite yet)
"""

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


def execute_readonly_sql(sql: str) -> list[dict]:
    """Validate sql is a SELECT, then return a canned result from DATA."""
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT statements are allowed")
    # TODO (Phase 2): execute real SQL against SQLite
    return DATA["enrollments"]
