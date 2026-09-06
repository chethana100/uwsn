#!/usr/bin/env python3
"""
analyze_results.py -- paired statistics over results.csv.

Runs are PAIRED: run i uses the same topology and the same source set in both
arms, so the paired test is the correct one and it removes topology variance
from the comparison.

Reports mean +/- 95% CI, the paired t-test, the Wilcoxon signed-rank test as a
non-parametric check, and Cohen's d. Prints a slide-ready summary line.

    python3 analyze_results.py results.csv

Only needs the standard library. If scipy is installed it is used for exact
p-values; otherwise a t-table lookup is used and Wilcoxon is skipped.
"""

import csv
import math
import statistics as st
import sys

# two-tailed t critical values at alpha = 0.05, by degrees of freedom
T_CRIT = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
          7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
          13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101,
          19: 2.093, 20: 2.086, 24: 2.064, 29: 2.045, 39: 2.023, 49: 2.010}


def tcrit(df):
    if df in T_CRIT:
        return T_CRIT[df]
    for k in sorted(T_CRIT):
        if k >= df:
            return T_CRIT[k]
    return 1.96


def load(path):
    data = {}
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            data.setdefault(r['arm'], {})[int(r['run'])] = r
    return data


def paired(a_rows, b_rows, field):
    runs = sorted(set(a_rows) & set(b_rows))
    a = [float(a_rows[r][field]) for r in runs]
    b = [float(b_rows[r][field]) for r in runs]
    return runs, a, b


def report(name, runs, a, b, unit, higher_is_better=True):
    d = [y - x for x, y in zip(a, b)]
    n = len(d)
    if n < 2:
        print(f"{name}: need >= 2 paired runs, have {n}")
        return

    m, sd = st.mean(d), st.stdev(d)
    se = sd / math.sqrt(n)
    t = m / se if se > 0 else float('inf')
    lo, hi = m - tcrit(n - 1) * se, m + tcrit(n - 1) * se
    dz = m / sd if sd > 0 else float('inf')

    p = None
    try:
        from scipy import stats
        p = stats.ttest_rel(b, a).pvalue
        w = stats.wilcoxon(b, a).pvalue if n >= 6 else None
    except Exception:
        w = None

    print(f"\n### {name}")
    print(f"  arm A (baseline) : {st.mean(a):8.3f} +/- {1.96*st.stdev(a)/math.sqrt(n):.3f} {unit}")
    print(f"  arm B (trust+Q)  : {st.mean(b):8.3f} +/- {1.96*st.stdev(b)/math.sqrt(n):.3f} {unit}")
    print(f"  difference       : {m:+8.3f} {unit}   (sd {sd:.3f})")
    print(f"  95% CI           : [{lo:+.3f}, {hi:+.3f}] {unit}")
    print(f"  paired t         : t = {t:.3f}, df = {n-1}"
          + (f", p = {p:.4f}" if p is not None else " (install scipy for p)"))
    if w is not None:
        print(f"  Wilcoxon         : p = {w:.4f}")
    print(f"  Cohen's dz       : {dz:.3f}")

    better = sum(1 for x in d if (x > 0) == higher_is_better and x != 0)
    print(f"  arm B better in  : {better}/{n} runs")

    crosses_zero = lo <= 0 <= hi
    if crosses_zero:
        print("  VERDICT: NOT SIGNIFICANT -- the CI contains zero.")
        print("           Report this as a null result. Do not claim an improvement.")
    else:
        print("  VERDICT: significant at alpha = 0.05.")

    return m, lo, hi, p, crosses_zero


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'results.csv'
    data = load(path)

    if 'noattack' not in data or 'heavyattack' not in data:
        print(f"Need both 'noattack' and 'underattack' arms in {path}. Found: {list(data)}")
        sys.exit(1)

    A, B = data['noattack'], data['heavyattack']
    runs = sorted(set(A) & set(B))
    print(f"Paired runs: {len(runs)}  ->  {runs}")

    if len(runs) < 20:
        print(f"\nWARNING: only {len(runs)} paired runs. Aim for 20+.")

    pdr = report("PDR", *paired(A, B, 'pdr'), unit='pts', higher_is_better=True)
    report("End-to-end delay", *paired(A, B, 'avg_delay_s'), unit='s', higher_is_better=False)
    report("Energy consumed", *paired(A, B, 'energy_consumed_J'), unit='J', higher_is_better=False)

    # Did the old parser inflate PDR?
    _, old, new = paired(A, A, 'pdr')  # placeholder to keep shape
    olds = [float(A[r]['pdr_old_method']) for r in runs]
    news = [float(A[r]['pdr']) for r in runs]
    infl = st.mean([o - n for o, n in zip(olds, news)])
    print(f"\n### Denominator check (baseline arm)")
    print(f"  Old parser inflated PDR by {infl:+.2f} pts on average.")

    if pdr:
        m, lo, hi, p, ns = pdr
        print("\n" + "=" * 62)
        print("SLIDE LINE:")
        if ns:
            print(f"  PDR difference {m:+.2f} pts, 95% CI [{lo:+.2f}, {hi:+.2f}], "
                  f"n={len(runs)} paired runs -- not statistically significant.")
        else:
            print(f"  PDR improved by {m:+.2f} pts, 95% CI [{lo:+.2f}, {hi:+.2f}], "
                  f"n={len(runs)} paired runs.")
        print("=" * 62)


if __name__ == '__main__':
    main()
