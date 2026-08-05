import os
from unittest.mock import patch
from app.tracing import _configure_langsmith

def test_configure_langsmith():
    with patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key"}):
        # We need to clear these keys if they exist so setdefault actually sets them
        if "LANGCHAIN_TRACING_V2" in os.environ: del os.environ["LANGCHAIN_TRACING_V2"]
        if "LANGCHAIN_API_KEY" in os.environ: del os.environ["LANGCHAIN_API_KEY"]
        if "LANGCHAIN_PROJECT" in os.environ: del os.environ["LANGCHAIN_PROJECT"]
        
        _configure_langsmith()
        
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
        assert os.environ.get("LANGCHAIN_API_KEY") == "test-key"
        assert os.environ.get("LANGCHAIN_PROJECT") == "university-sql-agent"
