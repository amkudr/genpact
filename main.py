from dotenv import load_dotenv

load_dotenv()  # loads OPENAI_API_KEY (and any other vars) from .env

from app.graph import run

BANNER = """
╔══════════════════════════════════════════════╗
║        University SQL Agent — REPL           ║
║  Ask questions about students, courses, etc. ║
║  Type 'quit' or press Ctrl+D to exit.        ║
╚══════════════════════════════════════════════╝
"""


def prompt() -> str:
    return input("\n❓ Question: ").strip()


def handle(question: str) -> None:
    result = run(question)
    print(f"\n💬 Answer : {result['answer']}")
    print(f"🔍 SQL    : {result.get('sql', 'n/a')}")
    if result.get("error"):
        print(f"⚠️  Error  : {result['error']}")


def main() -> None:
    print(BANNER)
    for question in iter(prompt, "quit"):
        if question:
            handle(question)


if __name__ == "__main__":
    main()

