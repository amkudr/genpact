"""
app.services — LLM configuration (Phase 1: mock)
"""


class MockLLM:
    def generate_sql(self, question: str) -> str:
        # TODO (Phase 2): call real LLM with SQL_GENERATION_PROMPT
        return "SELECT * FROM enrollments"

    def format_answer(self, question: str, rows: list[dict]) -> str:
        # TODO (Phase 2): call real LLM with ANSWER_FORMAT_PROMPT
        return f"Found {len(rows)} result(s) for: '{question}'."


def get_llm() -> MockLLM:
    # TODO (Phase 2): return ChatOpenAI(model=..., temperature=0)
    return MockLLM()
