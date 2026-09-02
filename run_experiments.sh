#!/usr/bin/env bash
#
# run_experiments.sh -- batch both arms across N independent runs.
#
# Run from your ns-3 root directory (the one containing ./ns3).
#
#   chmod +x run_experiments.sh
#   ./run_experiments.sh 20
#
# Deletes each .tr immediately after parsing. At 3000 s these are large
# (tens of MB each); 40 of them would fill a lot of disk for no reason.
# Set KEEP_TRACES=1 if you want to keep them for debugging.

set -u

NRUNS="${1:-20}"
KEEP_TRACES="${KEEP_TRACES:-0}"
OUT="results.csv"
ANALYZER="analyze_trace.py"

if [ ! -x "./ns3" ]; then
  echo "ERROR: ./ns3 not found. Run this from your ns-3 root directory."
  exit 1
fi
if [ ! -f "$ANALYZER" ]; then
  echo "ERROR: $ANALYZER not found. Put it in the ns-3 root directory."
  exit 1
fi

rm -f "$OUT"
echo "=== $NRUNS runs per arm -> $OUT ==="
START=$(date +%s)

run_arm () {
  local prog="$1" arm="$2" extra="${3:-}"
  for i in $(seq 1 "$NRUNS"); do
    echo "[$arm] run $i / $NRUNS"
    ./ns3 run "$prog --run=$i --tag=$arm $extra" > /dev/null 2>&1
    if [ ! -f "${arm}_${i}.tr" ]; then
      echo "  !! ${arm}_${i}.tr missing -- simulation failed. Re-run without" \
           "redirecting stderr to see the error."
      continue
    fi
    python3 "$ANALYZER" \
      --trace "${arm}_${i}.tr" \
      --meta  "${arm}_${i}_meta.csv" \
      --arm   "$arm" --run "$i" --out "$OUT" > /dev/null
    if [ "$KEEP_TRACES" != "1" ]; then
      rm -f "${arm}_${i}.tr"
    fi
  done
}

run_arm "uwsn-phase1-baseline" "baseline"
run_arm "uwsn-trustq-baseline"          "trustq"   "--priorityScale=0.15"

END=$(date +%s)
echo
echo "=== done in $(( (END-START)/60 )) min ==="
echo "Now run:  python3 analyze_results.py $OUT"
