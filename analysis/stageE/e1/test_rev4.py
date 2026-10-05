#!/usr/bin/env python3
"""Unit and consistency checks for calibrate_rev4.py (frozen revision 4, ../README.md §7).
Synthetic inputs only, plus read-only use of the existing clean E1 opportunity files (seeds 12-21) for the
statistic-equivalence check. No simulation, no attacker data. Exit code 0 only if every check passes.

usage: test_rev4.py [<E1 run root>]
"""
import sys, math, random
from fractions import Fraction
import numpy as np
import calibrate_rev4 as C4

FAILS = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


# 1. frozen constants
check("constants M=200, p_min=0.75, power 0.80, FA 0.05, B_cal=1000, seed 12345, LCB rank 50, B_boot=10000",
      (C4.M_BIN, C4.P_MIN, C4.POWER, C4.FA_NOMINAL, C4.B_CAL, C4.SEED, C4.LCB_RANK, C4.B_BOOT) == (200, 0.75, 0.80, 0.05, 1000, 12345, 50, 10000))

# 2. statistic: r_w with w = 1 equals (K - E)/n exactly; n_eff = n; S_w = 0 -> n_eff 0, never judged
rnd = random.Random(7)
eq = True
for _ in range(2000):
    n = rnd.randint(1, 60); ys = [rnd.randint(0, 1) for _ in range(n)]; qs = [rnd.random() for _ in range(n)]
    K_w, E_w, S_w, neff, rw = C4.weighted_pair([(y, q, 1.0) for y, q in zip(ys, qs)])
    E = 0.0
    for q in qs:
        E += q
    eq &= (rw == (sum(ys) - E) / n) and neff == n and S_w == n and K_w == sum(ys)
check("Arm A: r_w (w = 1) == (K - E)/n exactly, n_eff == n (2,000 random pairs)", eq)
K_w, E_w, S_w, neff, rw = C4.weighted_pair([(1, 0.3, 0.0), (0, 0.6, 0.0)])
check("S_w = 0 -> n_eff = 0, r_w undefined, never judged", neff == 0.0 and rw is None and not C4.judged(neff, 14))
K_w, E_w, S_w, neff, rw = C4.weighted_pair([(1, 0.5, 1.0), (0, 0.5, 0.0), (1, 0.25, 0.5)])
check("weighted example: K_w=1.5, E_w=0.625, S_w=1.5, n_eff=1.8, r_w=(1.5-0.625)/1.5",
      abs(K_w - 1.5) < 1e-15 and abs(E_w - 0.625) < 1e-15 and abs(neff - 1.8) < 1e-12 and abs(rw - 0.875 / 1.5) < 1e-15)
check("judged: n_min undefined -> never judged; n_eff >= n_min inclusive",
      not C4.judged(100, None) and C4.judged(76, 76) and not C4.judged(75.999, 76))

# 3. nearest rank
check("nearest rank 95%: N=200 -> 190th smallest; N=20 -> 19th; N=1 -> only value",
      C4.nearest_rank_95(list(range(1, 201))) == 190 and C4.nearest_rank_95(list(range(1, 21))) == 19 and C4.nearest_rank_95([3.5]) == 3.5)


# 4. PAVA vs independent min-max formula for non-increasing weighted isotonic regression
def minmax_nonincreasing(rho, w):
    K = len(rho); out = []
    av = lambda i, j: sum(w[t] * rho[t] for t in range(i, j + 1)) / sum(w[t] for t in range(i, j + 1))
    for b in range(K):          # non-increasing fit: tau_b = max_{j>=b} min_{i<=b} Av(i..j)
        out.append(max(min(av(i, j) for i in range(0, b + 1)) for j in range(b, K)))
    return out


ok = True; worst = 0.0
for _ in range(3000):
    K = rnd.randint(1, 9); rho = [rnd.choice([rnd.random(), round(rnd.random(), 1)]) for _ in range(K)]; w = [rnd.randint(200, 320) for _ in range(K)]
    a = C4.pava_nonincreasing(rho, w); b = minmax_nonincreasing(rho, w)
    d = max(abs(x - y) for x, y in zip(a, b)); worst = max(worst, d)
    ok &= d < 1e-12 and all(a[i] >= a[i + 1] for i in range(K - 1))
check("PAVA == min-max isotonic formula and non-increasing (3,000 random cases incl. ties)", ok, f"max |diff| {worst:.1e}")
check("PAVA: equal adjacent values not merged; violation pooled with weights",
      C4.pava_nonincreasing([0.5, 0.5, 0.2], [200, 300, 250]) == [0.5, 0.5, 0.2]
      and C4.pava_nonincreasing([0.1, 0.3], [100, 300]) == [0.25, 0.25])

# 5. exact attacked flag probability vs exact rational binomial tail
ok = True; worst = 0.0
for m in list(range(0, 41)) + [100, 250, 400]:
    tl = C4.tail_table(m)
    for f in range(0, m + 1):
        exact = sum(Fraction(math.comb(m, g)) * Fraction(3, 4) ** g * Fraction(1, 4) ** (m - g) for g in range(f, m + 1))
        d = abs(tl[f] - float(exact)); worst = max(worst, d / max(float(exact), 1e-300) if float(exact) > 1e-300 else d)
        ok &= (d <= 1e-12 * max(1.0, float(exact)) + 1e-300) or (float(exact) < 1e-250 and tl[f] < 1e-250)
check("tail table (lnGamma terms, ascending sum) == exact rational Binomial(m, 0.75) tail", ok, f"max rel err {worst:.1e}")
check("pi edge cases: f* <= 0 -> 1; f* > m -> 0",
      C4.pi_attacked(n=10, K=10, m=0, E=3.0, tau=0.1) == 1.0 and C4.pi_attacked(n=10, K=0, m=10, E=0.0, tau=1.5) == 0.0)
# exact value for a hand case: n=10, K=2, m=8, E=3.0, tau=0.2 -> x = 2 + 3 - 2 = 3 -> f* = 4 -> P(F >= 4), F ~ Bin(8, .75)
exact = float(sum(Fraction(math.comb(8, g)) * Fraction(3, 4) ** g * Fraction(1, 4) ** (8 - g) for g in range(4, 9)))
check("pi hand case n=10,K=2,m=8,E=3,tau=0.2 -> P(Bin(8,.75) >= 4)", abs(C4.pi_attacked(10, 2, 8, 3.0, 0.2) - exact) < 1e-14)
# flag condition equivalence: F >= f*  <=>  (K + F - E)/n > tau  (checked for all F, random cases)
ok = True
for _ in range(5000):
    n = rnd.randint(1, 80); K = rnd.randint(0, n); m = n - K; E = rnd.random() * n; tau = rnd.uniform(-0.5, 1.0)
    fstar = math.floor(n * tau + E - K) + 1
    for F in range(0, m + 1):
        ok &= ((K + F - E) / n > tau) == (F >= fstar)
check("f* = floor(n*tau + E - K) + 1 matches the flag condition (K + F - E)/n > tau (5,000 cases, all F)", ok)

# 6. Monte Carlo thinning agrees with the exact expectation (sanity of the attacker model)
g = np.random.Generator(np.random.PCG64(99))
n, K, E, tau = 60, 20, 22.5, 0.5; m = n - K                 # flag iff F >= 33 with F ~ Bin(40, 0.75): mid-range pi
ex = C4.pi_attacked(n, K, m, E, tau)
mc = float(np.mean((K + g.binomial(m, 0.75, 200000) - E) / n > tau))
check("Monte Carlo thinning (200k) vs exact pi, non-degenerate case", 0.05 < ex < 0.95 and abs(mc - ex) < 0.005,
      f"MC {mc:.4f} vs exact {ex:.4f}")

# 7. vectorised BinArrays.pi == scalar pi_attacked
P = {}
for i in range(300):
    nn = rnd.randint(14, 300); KK = rnd.randint(0, nn); EE = rnd.random() * nn
    P[(12, i, i)] = {"n": nn, "K": KK, "m": nn - KK, "E": EE, "r": (KK - EE) / nn, "Z": 0.0}
ba = C4.BinArrays(P, sorted(P))
ok = True
for tau in (-0.2, 0.0, 0.05, 0.13, 0.3, 0.7):
    v = ba.pi(tau); s = [C4.pi_attacked(P[k]["n"], P[k]["K"], P[k]["m"], P[k]["E"], tau) for k in sorted(P)]
    ok &= all(a == b for a, b in zip(v.tolist(), s))
check("vectorised pi == scalar pi (bit-identical, 300 pairs x 6 thresholds)", ok)

# 8. P-suffix rule
def psuffix(lcb, L):
    for b in range(len(lcb)):
        if all(x >= 0.80 for x in lcb[b:]):
            return L[b]
    return None
check("P-suffix: [0.9,0.7,0.85] -> L3; [0.85,0.9] -> L1; [0.9,0.79] -> undefined; [0.80] -> L1",
      psuffix([0.9, 0.7, 0.85], [14, 30, 60]) == 60 and psuffix([0.85, 0.9], [14, 30]) == 14
      and psuffix([0.9, 0.79], [14, 30]) is None and psuffix([0.80], [14]) == 14)

# 9. on the real clean E1 data (read-only): r == (K - E)/n via the weighted path; bootstrap reproducibility
if len(sys.argv) > 1:
    root = sys.argv[1]
    rows = C4.load(root, list(range(12, 22)))
    res, lab, q, qbar, n_ref = C4.step12(rows)
    PA = C4.arm_a_pairs(rows, lab, q)
    grp = {}
    for run, o, x, cell, y in rows:
        grp.setdefault((run, o, x), []).append((y, q[lab[cell]], 1.0))
    same = all(C4.weighted_pair(grp[k])[4] == PA[k]["r"] and C4.weighted_pair(grp[k])[3] == PA[k]["n"] for k in PA)
    check(f"E1 data: weighted path (w = 1) reproduces r and n for all {len(PA)} pairs", same)
    sub = [r for r in rows if r[0] in (12, 13, 14)]
    a, _ = C4.calibrate_rev4(sub); b, _ = C4.calibrate_rev4(sub)
    check("determinism: two independent calibrations (seeds 12-14 subset, full bootstrap) identical",
          a["lcb_b"] == b["lcb_b"] and a["tau_A_b"] == b["tau_A_b"] and a["power_b"] == b["power_b"] and a["n_min"] == b["n_min"])

print(f"\n{'ALL CHECKS PASSED' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
sys.exit(1 if FAILS else 0)
