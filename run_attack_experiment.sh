#!/usr/bin/env bash
#
# run_attack_experiment.sh -- paired no-attack vs malicious-attacker
# comparison across N independent seeds, using uwsn-trustq-attack.
#
# Both arms use the SAME run numbers (1..N), so RngSeedManager gives them
# the SAME topology/mobility per seed -- only attackerFraction/
# dropProbability differ. This is the same paired-seed discipline used
# for the earlier baseline-vs-trustq comparison.
#
# Run from your ns-3 root directory (the one containing ./ns3).
#
#   chmod +x run_attack_experiment.sh
#   ./run_attack_experiment.sh 20
#
set -u
NRUNS="${1:-20}"
ATTACKER_FRACTION="${2:-0.2}"
DROP_PROBABILITY="${3:-1.0}"
PRIORITY_SCALE="${4:-0.15}"
OUT="results_attack_experiment.csv"
ANALYZER="analyze_trace.py"
PROG="uwsn-trustq-attack"

if [ ! -x "./ns3" ]; then
  echo "ERROR: ./ns3 not found. Run this from your ns-3 root directory."
  exit 1
fi
if [ ! -f "$ANALYZER" ]; then
  echo "ERROR: $ANALYZER not found. Put it in the ns-3 root directory."
  exit 1
fi

rm -f "$OUT"
echo "=== $NRUNS paired runs: noattack vs attack (fraction=$ATTACKER_FRACTION, drop=$DROP_PROBABILITY, priorityScale=$PRIORITY_SCALE) ==="
echo "=== -> $OUT ==="
START=$(date +%s)

run_arm () {
  local arm="$1" extra="$2"
  for i in $(seq 1 "$NRUNS"); do
    echo "[$arm] run $i / $NRUNS"
    ./ns3 run "$PROG --run=$i --tag=$arm $extra" > /dev/null 2>&1
    if [ ! -f "${arm}_${i}.tr" ]; then
      echo "  !! ${arm}_${i}.tr missing -- simulation failed. Re-run without" \
           "redirecting stderr to see the error."
      continue
    fi
    python3 "$ANALYZER" \
      --trace "${arm}_${i}.tr" \
      --meta  "${arm}_${i}_meta.csv" \
      --arm   "$arm" --run "$i" --out "$OUT" > /dev/null
    rm -f "${arm}_${i}.tr"
  done
}

run_arm "noattack" "--priorityScale=$PRIORITY_SCALE --attackerFraction=0.0 --dropProbability=0.0"
run_arm "attack"   "--priorityScale=$PRIORITY_SCALE --attackerFraction=$ATTACKER_FRACTION --dropProbability=$DROP_PROBABILITY"

END=$(date +%s)
echo ""
echo "=== done in $(( (END-START)/60 )) min ==="
echo "Now run:  python3 analyze_results.py $OUT"
