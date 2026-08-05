# University SQL Agent

A minimal, high-quality question-answering system using LangGraph and LangSmith to translate natural language questions into SQL queries, execute them against a database, and return a human-readable answer.

## Database Schema

The agent operates over an in-memory SQLite university database (defined in [`app/db.py`](file:///Users/anmkudr/Projects/Genpact%20project/app/db.py)).

```mermaid
erDiagram
    courses {
        INTEGER id PK
        TEXT code
        TEXT title
        INTEGER credits
    }
    teachers {
        INTEGER id PK
        TEXT name
        TEXT department
    }
    offerings {
        INTEGER id PK
        INTEGER course_id FK
        INTEGER teacher_id FK
        TEXT semester
        INTEGER year
    }
    students {
        INTEGER id PK
        TEXT name
        TEXT email
    }
    enrollments {
        INTEGER id PK
        INTEGER student_id FK
        INTEGER offering_id FK
        TEXT grade
    }

    courses ||--o{ offerings : "scheduled as"
    teachers ||--o{ offerings : "teaches"
    offerings ||--o{ enrollments : "includes"
    students ||--o{ enrollments : "enrolled in"
```
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
flowchart TB
    User(["User\nQuestion"]):::io

    subgraph Pipeline ["LangGraph Pipeline — app.graph"]
        direction LR
        N1["Step 1\nparse_question"]:::node -->
        N2["Step 2\ngenerate_sql"]:::node -->
        N3{"Step 3\nvalidate_sql"}:::decision
        N3 -->|"Valid"| N4["Step 4\nexecute_sql"]:::node -->
        N5["Step 5\nformat_answer"]:::node
        N3 -->|"Invalid"| N2
    end

    Answer(["Final\nAnswer"]):::io
    LLM[("LLM\napp.services")]:::external
    DB[("SQL DB\napp.db")]:::external
    Tracing["app.tracing\nLangSmith"]:::tracing

    User --> N1
    N5 --> Answer
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

| Step | Node             | Description                                                                                                                      |
| ---- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 1    | `parse_question` | Parses the user's natural language question to extract intent, entities (students, courses, teachers), filters, and constraints. |
| 2    | `generate_sql`   | Uses the LLM to translate the structured intent into a SQL query tailored to the university database schema.                     |
| 3    | `validate_sql`   | Checks the generated SQL for syntax correctness and schema compatibility. If invalid, loops back to Step 2 for a retry.          |
| 4    | `execute_sql`    | Runs the validated SQL query against the database and retrieves the raw result set.                                              |
| 5    | `format_answer`  | Uses the LLM to convert the raw DB results into a clear, human-readable natural language answer.                                 |
| —    | `app.tracing`    | LangSmith observer that traces the full execution path: User Input → Nodes → SQL → DB Results → Final Answer.                    |

## Project Structure

- **`app/graph.py`**: Defines the LangGraph pipeline, nodes, state dict, and routing logic.
- **`app/services.py`**: Contains LLM service wrappers and tools for generation and formatting.
- **`app/db.py`**: Handles database connections and secure query execution.
- **`app/tracing.py`**: Initializes and configures LangSmith telemetry.
- **`main.py`** (if present): Entry point to run the agent interactively.

## Getting Started

### 1 · Install dependencies
```bash
pip install -r requirements.txt
```

### 2 · Set up your API key
```bash
# Copy the safe template
cp .env.example .env

# Open .env in a plain text editor and replace the placeholder:
#   OPENAI_API_KEY=your-openai-api-key-here
```

Your real `.env` is listed in `.gitignore` and will never be committed.  
The committed [`.env.example`](.env.example) contains only safe placeholder values.

### 3 · Run the agent
```bash
python main.py
```

### 4 · Run the test suite

**Fast Unit Tests** (No API key needed — LLM is mocked):
```bash
pytest tests/ -v
```

**End-to-End Tests** (Tests live OpenAI API with complex queries):
```bash
RUN_E2E=true pytest tests/test_e2e.py -v -s
```
