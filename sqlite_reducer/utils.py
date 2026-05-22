import os
import sqlite3
import subprocess
import tempfile
from sqlglot.tokens import Tokenizer
from sqlglot import parse, exp

def run_oracle(candidate_sql: str, oracle_script: str) -> bool:
  oracle_script = os.path.abspath(oracle_script)

  with tempfile.TemporaryDirectory() as tmpdir:
    candidate_path = os.path.join(tmpdir, "query.sql")

    with open(candidate_path, "w", encoding="utf-8") as f:
      f.write(candidate_sql)

    with open(oracle_script, "rb") as f:
      oracle_bytes = f.read().replace(b"\r\n", b"\n")

    oracle_copy = os.path.join(tmpdir, "test.sh")
    with open(oracle_copy, "wb") as f:
      f.write(oracle_bytes)
    os.chmod(oracle_copy, 0o755)

    env = os.environ.copy()
    env["TEST_CASE_LOCATION"] = candidate_path

    result = subprocess.run(
      ["bash", oracle_copy],
      cwd=tmpdir,
      env=env,
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
      timeout=10,
    )

    return result.returncode == 0

# General pattern for delta debugging
def delta_debug(parts: list[str], oracle_script: str, delimitter:str=' ') -> list[str]:
  n = 2
  
  prev_parts_len = len(parts)

  while len(parts) >= 2:
    chunk_size = len(parts) // n
    reduction_worked = False

    for i in range(0, len(parts), chunk_size):
      candidate_arr = parts[:i] + parts[i + chunk_size:]
      candidate_sql = delimitter.join(candidate_arr)

      if run_oracle(candidate_sql, oracle_script):
        parts = candidate_arr
        n = 2
        reduction_worked = True
        break

    if not reduction_worked:
      if n >= len(parts):
        break
      n = min(len(parts), n * 2)

  return parts

# Parse SQL
def parse_sql(sql_stmt: str) -> list:
  statements = parse(sql_stmt)
  return statements
  
# Get tables involved in the statement
def get_tables(stmt: str) -> list[str]:
  tables = []

  for parsed_stmt in parse_sql(stmt):
    cte_names = {cte.alias for cte in parsed_stmt.find_all(exp.CTE)}

    for table in parsed_stmt.find_all(exp.Table):
      if table.name and table.name not in cte_names:
        tables.append(table.name)

  return list(dict.fromkeys(tables))
  
# Splitting and Unsplitting
def split_stmts(sql: str) -> list[str]:
  stmts = []
  current = []

  for char in sql:
    current.append(char)
    stmt = "".join(current)

    if sqlite3.complete_statement(stmt):
      stmt = stmt.strip()

      if stmt.endswith(";"):
        stmt = stmt[:-1].rstrip()

      if stmt:
        stmts.append(stmt)

      current = []

  tail = "".join(current).strip()

  if tail:
    stmts.append(tail)

  return stmts

def unsplit_stmts(tokens: list[str]) -> str:
  return ";\n".join(tokens)

def tokenize_sql(sql: str) -> list[str]:
  return [token.text for token in Tokenizer().tokenize(sql)]

def untokenize_sql(tokens: list[str]) -> str:
  return " ".join(tokens)
