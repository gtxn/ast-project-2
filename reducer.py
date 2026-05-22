#!/usr/bin/env python3

import time
import argparse
from sqlite_reducer.utils import *
from sqlite_reducer.delta_reduce import delta_statement_reducer, delta_token_reducer
from sqlite_reducer.statement_reduce import statement_reducer
from sqlite_reducer.expression_reduce import expression_reduce

# Statement goes through these reducers in order
REDUCERS = [
  # Reduces statements by the tables that they are involved in
  statement_reducer,
  # Delta debugging on remaining statements
  delta_statement_reducer,
  # Reduction of expressions by evaluating them
  expression_reduce
  # Delta debugging on tokens
  # delta_token_reducer
]

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--query", required=True)
  parser.add_argument("--test", required=True)
  args = parser.parse_args()

  with open(args.query, "r", encoding="utf-8") as f:
    original_sql = f.read()

  current_sql = original_sql
  original_tokens = len(tokenize_sql(original_sql))
  start_time = time.time()

  for reducer in REDUCERS:
    try:
      current_sql = reducer(current_sql, args.test)
    except:
      pass

  elapsed = time.time() - start_time
  final_tokens = len(tokenize_sql(current_sql))

  with open("query.sql", "w", encoding="utf-8") as f:
    f.write(current_sql)

  # print('--- NEW SQL ---')
  # print(current_sql)
  # print('--- END ---')
  print('--- BENCHMARK ---')
  print(f'Time:   {elapsed:.2f}s')
  print(f'Tokens: {original_tokens} -> {final_tokens} ({100 * (original_tokens - final_tokens) / original_tokens:.1f}% reduced)')
  print('--- END BENCHMARK ---')

if __name__ == "__main__":
  main()