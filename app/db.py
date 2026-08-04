"""
app.db — Database layer

Responsibilities:
  - Create and expose the SQLAlchemy engine (SQLite by default).
  - Define schema constants (table names, column names) so that the rest of
    the application never hard-codes raw strings.
  - Provide a single `execute_readonly_sql(sql, params)` helper that:
      * Validates the statement is a SELECT before running it.
      * Returns results as a list of dicts.
      * Raises a descriptive error on any database failure.

Nothing above this module should know which database engine is in use.
"""
