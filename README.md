# University SQL Agent

A minimal, high-quality question-answering system using LangGraph and LangSmith to translate natural language questions into SQL queries, execute them against a database, and return a human-readable answer.

## Module Flow Diagram

The application uses LangGraph to manage state and route execution through several nodes. The following diagram shows the high-level architecture and how data flows between the modules.

```mermaid
%%{init: {
  "theme": "base",
  "themeVariables": {
    "primaryColor": "#1e1e2e",
    "primaryTextColor": "#cdd6f4",
    "primaryBorderColor": "#89b4fa",
    "lineColor": "#89dceb",
    "secondaryColor": "#181825",
    "tertiaryColor": "#313244",
    "edgeLabelBackground": "#313244",
    "clusterBkg": "#181825",
    "clusterBorder": "#45475a",
    "titleColor": "#cba6f7",
    "fontFamily": "Inter, ui-sans-serif, system-ui"
  }
}}%%
flowchart LR
    User(["User\nQuestion"]):::io --> N1

    subgraph Pipeline ["LangGraph Pipeline — app.graph"]
        direction LR
        N1["Step 1\nparse_question"]:::node -->
        N2["Step 2\ngenerate_sql"]:::node -->
        N3{"Step 3\nvalidate_sql"}:::decision
        N3 -->|"Valid"| N4["Step 4\nexecute_sql"]:::node -->
        N5["Step 5\nformat_answer"]:::node
        N3 -->|"Invalid"| N2
    end

    N5 --> Answer(["Final\nAnswer"]):::io

    LLM[("LLM\napp.services")]:::external
    DB[("SQL DB\napp.db")]:::external
    Tracing["app.tracing\nLangSmith"]:::tracing

    N2 -. "NL→SQL" .-> LLM
    N5 -. "results→answer" .-> LLM
    N4 -. "query" .-> DB
    Tracing -. "monitors" .-> Pipeline

    classDef io        fill:#cba6f7,stroke:#b4befe,color:#1e1e2e,font-weight:bold
    classDef node      fill:#313244,stroke:#89b4fa,color:#cdd6f4
    classDef decision  fill:#f38ba8,stroke:#eba0ac,color:#1e1e2e,font-weight:bold
    classDef external  fill:#1e1e2e,stroke:#a6e3a1,color:#a6e3a1
    classDef tracing   fill:#45475a,stroke:#fab387,color:#fab387,stroke-dasharray:4
```

### Pipeline Step Descriptions

| Step | Node | Description |
|------|------|-------------|
| 1 | `parse_question` | Parses the user's natural language question to extract intent, entities (students, courses, teachers), filters, and constraints. |
| 2 | `generate_sql` | Uses the LLM to translate the structured intent into a SQL query tailored to the university database schema. |
| 3 | `validate_sql` | Checks the generated SQL for syntax correctness and schema compatibility. If invalid, loops back to Step 2 for a retry. |
| 4 | `execute_sql` | Runs the validated SQL query against the database and retrieves the raw result set. |
| 5 | `format_answer` | Uses the LLM to convert the raw DB results into a clear, human-readable natural language answer. |
| — | `app.tracing` | LangSmith observer that traces the full execution path: User Input → Nodes → SQL → DB Results → Final Answer. |

## Project Structure

- **`app/graph.py`**: Defines the LangGraph pipeline, nodes, state dict, and routing logic.
- **`app/services.py`**: Contains LLM service wrappers and tools for generation and formatting.
- **`app/db.py`**: Handles database connections and secure query execution.
- **`app/tracing.py`**: Initializes and configures LangSmith telemetry.
- **`main.py`** (if present): Entry point to run the agent interactively.

## Getting Started

*(Add instructions on how to install dependencies and run the project here)*
