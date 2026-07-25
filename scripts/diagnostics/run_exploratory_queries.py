"""Runs exploratory_queries.sql against nifty100.db and prints each
query's results — use this since the sqlite3 CLI tool may not be on PATH."""
import re
import sqlite3
from pathlib import Path

DB_PATH = "data/nifty100.db"
SQL_PATH = "exploratory_queries.sql"


def split_numbered_queries(sql_text: str) -> list[tuple[str, str]]:
    """Splits the file into (title, statement) pairs using the '-- N. ' markers."""
    parts = re.split(r"\n-- (\d+)\.\s*", sql_text)
    # parts[0] is the file header before query 1; ignore it
    results = []
    for i in range(1, len(parts), 2):
        num = parts[i]
        body = parts[i + 1]
        title_line, _, rest = body.partition("\n")
        # Statement is everything up to the first top-level semicolon
        stmt_end = rest.find(";")
        statement = rest[: stmt_end + 1] if stmt_end != -1 else rest
        # Strip any remaining comment lines from the statement
        statement = "\n".join(
            line for line in statement.splitlines() if not line.strip().startswith("--")
        )
        results.append((f"{num}. {title_line.strip()}", statement.strip()))
    return results


def main():
    conn = sqlite3.connect(DB_PATH)
    sql_text = Path(SQL_PATH).read_text(encoding="utf-8")
    queries = split_numbered_queries(sql_text)

    for title, stmt in queries:
        print("=" * 90)
        print(title)
        print("=" * 90)
        try:
            cur = conn.execute(stmt)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            print(" | ".join(cols))
            print("-" * 90)
            if not rows:
                print("(no rows returned)")
            for r in rows[:30]:
                print(" | ".join(str(v) for v in r))
            if len(rows) > 30:
                print(f"... ({len(rows) - 30} more rows not shown)")
        except Exception as e:
            print(f"ERROR running this query: {e}")
        print()

    conn.close()


if __name__ == "__main__":
    main()