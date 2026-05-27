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
    cp original_test.sql query.sql
    REDUCER_METRICS_FILE="$metrics_file" \
    REDUCER_QUERY_NAME="query$i" \
      python3 ../../reducer.py --query query.sql --test test.sh
  ); then
    echo "--- query$i time: $((SECONDS - query_start))s ---"
  else
    echo "--- query$i time: $((SECONDS - query_start))s (failed) ---"
    exit 1
  fi
done

echo ""
echo "--- QUERY SUMMARY ---"
python3 - "$metrics_file" <<'PY'
import csv
import sys
from collections import OrderedDict
from sqlglot.tokens import Tokenizer

def count_tokens(path):
    try:
        with open(path, encoding="utf-8") as f:
            return len(Tokenizer().tokenize(f.read()))
    except FileNotFoundError:
        return 0

metrics_file = sys.argv[1]
queries = OrderedDict()

with open(metrics_file, encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        q = row["query"]
        queries.setdefault(q, {"time": 0.0})
        queries[q]["time"] += float(row["time"])

print(f"{'Query':<10} {'Time (s)':>10} {'Original Tokens':>16} {'Tokens After':>14} {'Reduction':>12}")
print(f"{'-'*10} {'-'*10} {'-'*16} {'-'*14} {'-'*12}")

total_time = 0.0
total_before = 0
total_after = 0

for q, s in queries.items():
    base = f"queries/{q}"
    before = count_tokens(f"{base}/original_test.sql")
    after = count_tokens(f"{base}/query.sql")
    pct = (before - after) / before * 100 if before else 0.0
    total_time += s["time"]
    total_before += before
    total_after += after
    print(
        f"{q:<10} "
        f"{s['time']:>9.2f}s "
        f"{before:>16} "
        f"{after:>14} "
        f"{pct:>11.1f}%"
    )

total_pct = (total_before - total_after) / total_before * 100 if total_before else 0.0
print(f"{'-'*10} {'-'*10} {'-'*16} {'-'*14} {'-'*12}")
print(
    f"{'Total':<10} "
    f"{total_time:>9.2f}s "
    f"{total_before:>16} "
    f"{total_after:>14} "
    f"{total_pct:>11.1f}%"
)
PY

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
