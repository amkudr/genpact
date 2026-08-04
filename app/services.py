"""
app.services — LLM and prompt configuration

Responsibilities:
  - Build and return the LangChain LLM client (model name, temperature, API key
    are read from environment variables — never hard-coded here).
  - Own all prompt templates used by the graph nodes.  Templates are plain
    Python strings with named `{placeholders}` — no framework magic.
  - Expose a `get_llm()` factory that returns a configured LangChain BaseLLM so
    that swapping providers requires changing only this file.

Prompt templates planned:
  - SQL_GENERATION_PROMPT  — instructs the LLM to produce a single SELECT
    statement given the schema and the user question.
  - ANSWER_FORMAT_PROMPT   — instructs the LLM to turn raw SQL result rows into
    a concise, human-readable sentence.

This module must not import app.graph or app.db; it is a pure configuration
and factory layer.
"""
