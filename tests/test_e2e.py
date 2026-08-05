import os
import pytest
from dotenv import load_dotenv
from app.graph import run

# Load the .env file so OPENAI_API_KEY is available
load_dotenv()

# We only run this test if the developer explicitly sets RUN_E2E=true and has an API key.
# This prevents accidentally using up tokens during normal test runs.
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY") or os.environ.get("RUN_E2E", "false").lower() != "true",
    reason="True E2E tests require both OPENAI_API_KEY and RUN_E2E=true environment variables"
)

E2E_QUESTIONS = [
    (
        "Which students got an A in Database Systems in Spring 2024?",
        "alice",  # expected keyword in answer
        True,     # expect rows from DB
        False     # expect error
    ),
    (
        "How many total enrollments were there in Spring 2024?",
        "3",      # expecting count of 3
        True,
        False
    ),
    (
        "What is the name of the teacher who taught the student Carol White?",
        "patel",  # Dr. Patel
        True,
        False
    ),
    (
        "Who is living in Paris?",
        "university",  # polite refusal should mention 'university' database
        False,         # no rows executed
        True           # expect error handling to trigger
    )
]

@pytest.mark.parametrize("question, expected_keyword, expect_rows, expect_error", E2E_QUESTIONS)
def test_full_pipeline_e2e(question, expected_keyword, expect_rows, expect_error):
    """
    A true End-to-End test that hits the live OpenAI API.
    It verifies the entire pipeline for different complex query types:
    LLM (SQL Generation) -> DB execution -> LLM (Answer Generation).
    """
    print(f"\n--- Testing: {question} ---")
    
    # Act
    result = run(question)
    
    # Assert format
    assert "answer" in result, "The pipeline should return an answer."
    assert "sql" in result, "The pipeline should include the generated SQL."
    
    # Assert Error Handling
    if expect_error:
        assert result.get("error"), "Expected an error for out-of-domain questions."
        assert result["sql"].strip() == "OUT_OF_DOMAIN", f"LLM should output OUT_OF_DOMAIN, got {result['sql']}"
    else:
        assert not result.get("error"), f"Unexpected error: {result.get('error')}"
        
    # Assert DB Rows
    rows = result.get("rows", [])
    if expect_rows:
        assert len(rows) > 0, f"The query should return at least one DB row. SQL was: {result['sql']}"
    else:
        assert len(rows) == 0, "The query should not return any rows."
        
    # Assert LLM Final Answer Quality
    answer = result["answer"].lower()
    assert expected_keyword.lower() in answer, f"Expected '{expected_keyword}' in answer, got: {result['answer']}"
    print(f"✓ Success! Answer: {result['answer']}")
