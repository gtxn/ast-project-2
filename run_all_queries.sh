#!/usr/bin/env bash

set -e
start=$SECONDS
metrics_file=$(mktemp)
trap 'rm -f "$metrics_file"; echo ""; echo "--- TOTAL TIME TO RUN 20 QUERIES: $((SECONDS - start))s ---"' EXIT

if [ -d /opt/reducer/queries ]; then
  cd /opt/reducer
else
  cd "$(dirname "$0")"
fi

for i in {1..20}; do
  query_dir="queries/query$i"
  query_start=$SECONDS

  echo "Running query$i ..."
  if (
    cd "$query_dir"
    REDUCER_METRICS_FILE="$metrics_file" \
    REDUCER_QUERY_NAME="query$i" \
      python3 ../../reducer.py --query original_test.sql --test test.sh
  ); then
    echo "--- query$i time: $((SECONDS - query_start))s ---"
  else
    echo "--- query$i time: $((SECONDS - query_start))s (failed) ---"
    exit 1
  fi
done

echo ""
echo "--- REDUCER TOTALS ---"
python3 - "$metrics_file" <<'PY'
import csv
import sys
from collections import OrderedDict

metrics_file = sys.argv[1]
totals = OrderedDict()

with open(metrics_file, encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        reducer = row["reducer"]
        totals.setdefault(reducer, {
            "calls": 0,
            "failures": 0,
            "time": 0.0,
            "reduced_tokens": 0,
        })
        totals[reducer]["calls"] += 1
        totals[reducer]["time"] += float(row["time"])
        totals[reducer]["reduced_tokens"] += int(row["reduced_tokens"])
        if row["status"] != "ok":
            totals[reducer]["failures"] += 1

print(f"{'Reducer':<28} {'Calls':>5} {'Failures':>8} {'Time':>10} {'Tokens':>10}")
print(f"{'-' * 28} {'-' * 5:>5} {'-' * 8:>8} {'-' * 10:>10} {'-' * 10:>10}")

total_time = 0.0
total_tokens = 0
total_calls = 0
total_failures = 0

for reducer, stats in totals.items():
    total_time += stats["time"]
    total_tokens += stats["reduced_tokens"]
    total_calls += stats["calls"]
    total_failures += stats["failures"]
    print(
        f"{reducer:<28} "
        f"{stats['calls']:>5} "
        f"{stats['failures']:>8} "
        f"{stats['time']:>9.2f}s "
        f"{stats['reduced_tokens']:>+10d}"
    )

print(f"{'-' * 28} {'-' * 5:>5} {'-' * 8:>8} {'-' * 10:>10} {'-' * 10:>10}")
print(
    f"{'TOTAL':<28} "
    f"{total_calls:>5} "
    f"{total_failures:>8} "
    f"{total_time:>9.2f}s "
    f"{total_tokens:>+10d}"
)
PY

echo ""
echo "--- VALIDATION ---"
for i in {1..20}; do
  dir="queries/query$i"
  tmp=$(mktemp)
  tr -d '\r' < "$dir/test.sh" > "$tmp"
  if TEST_CASE_LOCATION="$dir/query.sql" bash "$tmp" 2>/dev/null; then
    echo "query$i: OK"
  else
    echo "query$i: FAIL"
  fi
  rm -f "$tmp"
done
