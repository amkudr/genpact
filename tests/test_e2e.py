import os
import pytest
from dotenv import load_dotenv
from app.graph import run

# Load the .env file so OPENAI_API_KEY is available
load_dotenv()

# We only run this test if the developer explicitly sets RUN_E2E=true and has an API key.
# This prevents accidentally using up tokens during normal test runs.
@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY") or os.environ.get("RUN_E2E", "false").lower() != "true",
    reason="True E2E tests require both OPENAI_API_KEY and RUN_E2E=true environment variables"
)
def test_full_pipeline_e2e():
    """
    A true End-to-End test that hits the live OpenAI API.
    It verifies the entire pipeline: 
    LLM (SQL Generation) -> DB execution -> LLM (Answer Generation).
    """
    # Act
    question = "Which students got an A in Database Systems in Spring 2024?"
    result = run(question)
    
    # Assert
    print("\n--- Verifying Pipeline Results ---")
    
    print("1. Checking if 'answer' key exists...")
    assert "answer" in result, "The pipeline should return an answer."
    print("   ✓ Confirmed: Answer key exists.")
    
    print("2. Checking if 'sql' key exists...")
    assert "sql" in result, "The pipeline should include the generated SQL."
    print(f"   ✓ Confirmed: Generated SQL is: {result['sql']}")
    
    print("3. Checking for pipeline errors...")
    assert not result.get("error"), f"There should be no errors, but got: {result.get('error')}"
    print("   ✓ Confirmed: No errors occurred.")
    
    print("4. Checking database rows returned...")
    rows = result.get("results", result.get("rows", []))
    assert len(rows) > 0, "The query should return at least one DB row."
    print(f"   ✓ Confirmed: Retrieved {len(rows)} row(s) from the database.")
    
    print("5. Checking if final answer mentions 'Alice'...")
    answer = result["answer"].lower()
    assert "alice" in answer, "The LLM's final answer should mention the student Alice."
    print(f"   ✓ Confirmed: Answer contains 'Alice'. Full answer: {result['answer']}\n")
