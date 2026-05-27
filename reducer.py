#!/usr/bin/env python3

import time
import argparse
import csv
import os
from sqlite_reducer.utils import *
from sqlite_reducer.delta_reduce import delta_statement_reducer, delta_token_reducer
from sqlite_reducer.statement_reduce import statement_reducer
from sqlite_reducer.expression_reduce import expression_reduce
from sqlite_reducer.where_reduce import where_condition_reduce
from sqlite_reducer.select_reduce import select_reduce
from sqlite_reducer.with_reduce import with_reduce
from sqlite_reducer.join_reduce import join_reduce
from sqlite_reducer.case_reduce import case_reduce
from sqlite_reducer.insert_row_reduce import insert_row_reduce
from sqlite_reducer.table_column_reduce import table_column_reduce

# Statement goes through these reducers in order
REDUCERS = [
  # Reduces statements by the tables that they are involved in
  statement_reducer,
  # Delta debugging on remaining statements
  delta_statement_reducer,
  # Reduce in WITH clauses
  with_reduce,
  # Removal of individual JOIN legs
  join_reduce,
  # Reduction of WHERE conditions
  where_condition_reduce,
  # Reduction of SELECT column lists
  select_reduce,
  # Removal of CASE WHEN branches
  case_reduce,
  # Removal of unnecessary INSERT rows
  insert_row_reduce,
  # Removal of table columns and matching INSERT values
  table_column_reduce,
  # Reduction of expressions by evaluating them
  expression_reduce,
  # Delta debugging on tokens
  # delta_token_reducer
]

def write_reducer_metric(metric):
  metrics_file = os.environ.get("REDUCER_METRICS_FILE")
  if not metrics_file:
    return

  fieldnames = [
    "query",
    "reducer",
    "status",
    "time",
    "before_tokens",
    "after_tokens",
    "reduced_tokens",
  ]
  needs_header = not os.path.exists(metrics_file) or os.path.getsize(metrics_file) == 0

  with open(metrics_file, "a", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    if needs_header:
      writer.writeheader()
    writer.writerow(metric)


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
    reducer_start = time.time()
    before_tokens = len(tokenize_sql(current_sql))
    try:
      next_sql = reducer(current_sql, args.test)
      reducer_elapsed = time.time() - reducer_start
      after_tokens = len(tokenize_sql(next_sql))
      reduced_tokens = before_tokens - after_tokens
      write_reducer_metric({
        "query": os.environ.get("REDUCER_QUERY_NAME", ""),
        "reducer": reducer.__name__,
        "status": "ok",
        "time": f"{reducer_elapsed:.6f}",
        "before_tokens": before_tokens,
        "after_tokens": after_tokens,
        "reduced_tokens": reduced_tokens,
      })
      current_sql = next_sql
    except Exception as exc:
      reducer_elapsed = time.time() - reducer_start
      write_reducer_metric({
        "query": os.environ.get("REDUCER_QUERY_NAME", ""),
        "reducer": reducer.__name__,
        "status": type(exc).__name__,
        "time": f"{reducer_elapsed:.6f}",
        "before_tokens": before_tokens,
        "after_tokens": before_tokens,
        "reduced_tokens": 0,
      })

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
