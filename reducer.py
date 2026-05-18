#!/usr/bin/env python3

import argparse
from sqlite_reducer.delta_reduce import delta_statement_reducer, delta_token_reducer

# Statement goes through these reducers in order
REDUCERS = [
  delta_statement_reducer,
  delta_token_reducer
]

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--query", required=True)
  parser.add_argument("--test", required=True)
  args = parser.parse_args()

  with open(args.query, "r", encoding="utf-8") as f:
    original_sql = f.read()

  current_sql = original_sql
  
  for reducer in REDUCERS:
    current_sql = reducer(current_sql, args.test)
  
  with open("query.sql", "w", encoding="utf-8") as f:
    f.write(current_sql)

  print(current_sql)

if __name__ == "__main__":
  main()