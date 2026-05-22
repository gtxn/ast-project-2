#!/usr/bin/env bash

set -e
start=$SECONDS
trap 'echo ""; echo "--- TOTAL TIME TO RUN 20 QUERIES: $((SECONDS - start))s ---"' EXIT

if [ -d /opt/reducer/queries ]; then
  cd /opt/reducer
else
  cd "$(dirname "$0")"
fi

for i in {1..20}; do
  query_dir="queries/query$i"

  echo "Running query$i ..."
  (
    cd "$query_dir"
    python3 ../../reducer.py --query original_test.sql --test test.sh
  )
done
