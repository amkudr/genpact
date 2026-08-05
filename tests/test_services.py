import os
from unittest.mock import patch, MagicMock
import pytest
from app.services import LLM, get_llm

def test_real_llm_missing_api_key():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(EnvironmentError, match="OPENAI_API_KEY is not set"):
            LLM()

@patch("app.services.ChatOpenAI")
def test_real_llm_methods(mock_chat):
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        llm = LLM()

    # Mock invoke on chains to prevent actual LLM usage
    llm._sql_chain = MagicMock()
    llm._sql_chain.invoke.return_value = "SELECT * FROM test"
    
    llm._answer_chain = MagicMock()
    llm._answer_chain.invoke.return_value = "Answer"
    
    # Test generate_sql
    sql = llm.generate_sql("query", "error")
    assert sql == "SELECT * FROM test"
    llm._sql_chain.invoke.assert_called_once()
    
    # Test format_answer
    ans = llm.format_answer("query", [{"a": 1}])
    assert ans == "Answer"
    llm._answer_chain.invoke.assert_called_once()

def test_get_llm():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        llm = get_llm()
        assert isinstance(llm, LLM)
