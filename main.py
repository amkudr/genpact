from app.graph import run

EXAMPLE_QUESTION = "Which students got an A in Database Systems in Spring 2024?"

if __name__ == "__main__":
    result = run(EXAMPLE_QUESTION)
    print("Answer:", result["answer"])
