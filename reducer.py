#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
import tempfile


def run_oracle(candidate_sql: str, oracle_script: str) -> bool:
    """
    Returns True if the bug still triggers.
    The project spec says:
      exit code 0 => bug still occurs
      exit code 1 => bug no longer occurs
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        candidate_path = os.path.join(tmpdir, "query.sql")

        with open(candidate_path, "w", encoding="utf-8") as f:
            f.write(candidate_sql)

        env = os.environ.copy()
        env["TEST_CASE_LOCATION"] = candidate_path

        result = subprocess.run(
            ["bash", oracle_script],
            cwd=tmpdir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )

        return result.returncode == 0


def simple_line_reduction(sql: str, oracle_script: str) -> str:
    lines = sql.splitlines(keepends=True)
    changed = True

    while changed:
        changed = False

        for i in range(len(lines)):
            candidate_lines = lines[:i] + lines[i + 1 :]
            candidate_sql = "".join(candidate_lines)

            if not candidate_sql.strip():
                continue

            if run_oracle(candidate_sql, oracle_script):
                lines = candidate_lines
                changed = True
                break

    return "".join(lines)


def simple_token_reduction(sql: str, oracle_script: str) -> str:
    tokens = sql.replace(";", " ; ").replace(",", " , ").replace("(", " ( ").replace(")", " ) ").split()

    changed = True
    while changed:
        changed = False

        for i in range(len(tokens)):
            candidate_tokens = tokens[:i] + tokens[i + 1 :]
            candidate_sql = " ".join(candidate_tokens)

            if not candidate_sql.strip():
                continue

            if run_oracle(candidate_sql, oracle_script):
                tokens = candidate_tokens
                changed = True
                break

    return " ".join(tokens)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--test", required=True)
    args = parser.parse_args()

    with open(args.query, "r", encoding="utf-8") as f:
        original_sql = f.read()

    current_sql = original_sql

    # First reduce lines
    current_sql = simple_line_reduction(current_sql, args.test)

    # Next reduce tokens
    current_sql = simple_token_reduction(current_sql, args.test)

    with open("query.sql", "w", encoding="utf-8") as f:
        f.write(current_sql)

    print(current_sql)


if __name__ == "__main__":
    main()