import os
import subprocess
import tempfile
from sqlglot.tokens import Tokenizer
from sqlglot import parse

def run_oracle(candidate_sql: str, oracle_script: str) -> bool:
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

  print('delta debug stats\n')
  print(f'prev part len: {prev_parts_len} | curr part len: {len(parts)}')
  return parts

# Parse SQL
def parse_sql(sql_stmt: str) -> list:
  statements = parse(sql_stmt)
  return statements
  
# Splitting and Unsplitting
def split_stmts(sql: str) -> list[str]:
  stmt_arr =  sql.split(';')
  stmt_arr = [s.strip() for s in stmt_arr]
  
  return stmt_arr

def unsplit_stmts(tokens: list[str]) -> str:
  return ";\n".join(tokens)

def tokenize_sql(sql: str) -> list[str]:
  return [token.text for token in Tokenizer().tokenize(sql)]

def untokenize_sql(tokens: list[str]) -> str:
  return " ".join(tokens)