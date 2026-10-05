#!/usr/bin/env python3
"""Tests for oc2_evaluate.py (frozen ../OC2_SPEC.md, commit 98bfcf2; D-23).
Synthetic data and DEVELOPMENT seed-1 runs only; never seeds 12-21; no OC-2 result is produced.
Development data validate the implementation only; they never choose a parameter, bin, grid value, k, estimator,
threshold, interpretation or report. Exit code 0 only if every check passes.

usage: test_oc2_evaluate.py [--tmp DIR] [--dev-runs CLEAN_RUN,RUN_B,RUN_C]
       (seed-1 run directories holding v1_1.*, stderr.log and e1_opportunities.csv; CLEAN_RUN first)
"""
import sys, os, io, csv, json, math, random, shutil, subprocess, tempfile, contextlib
from fractions import Fraction
sys.dont_write_bytecode = True
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oc2_evaluate as E
import e2_evaluate as E2                      # already on sys.path via oc2_evaluate; reference for the E2-8 rule

FAILS = []
args = sys.argv[1:]
opt = lambda k: (args[args.index(k) + 1] if k in args else None)
TMP = tempfile.mkdtemp(prefix="oc2test_", dir=opt("--tmp"))
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc as e:
        return str(e)
    return None


# 1. frozen constants ------------------------------------------------------------------------------------------------
check("constants: grid, k = 1.5 primary / 1.0, 2.0 secondary, xi 0.3, window 10, n_ref 14, seeds 12-21",
      E.GRID == (15.0, 20.0, 24.5, 27.5, 31.1, 34.5, 37.5, 40.0, 45.0, 50.0) and E.K_PRIMARY == 1.5
      and E.K_SECONDARY == (1.0, 2.0) and E.XI == 0.3 and E.HIST_WINDOW == 10 and E.N_REF == 14
      and E.SEEDS_OC2 == tuple(range(12, 22)))
check("constants: B 10,000, PCG64 12345, percentiles 2.5/97.5; S-13a thresholds 100 / 1e-10 / 1e-12 / 1e12",
      (E.B_BOOT, E.BOOT_SEED, E.PCT, E.IRLS_MAX_IT, E.IRLS_TOL, E.SEP_EPS, E.COND_MAX)
      == (10000, 12345, (2.5, 97.5), 100, 1e-10, 1e-12, 1e12))
check("constants: E-1 f 25 kHz, m 640; E-6a dt 0.05; E-8 norm 1e-6; P-1 40 dB, k 1.5",
      (E.F_KHZ, E.M_BITS, E.DT_MIN, E.NORM_MIN, E.PARITY_EBN0, E.PARITY_K) == (25.0, 640.0, 0.05, 1e-6, 40.0, 1.5))
check("S-12 fixed bins: SS/CCQ 10 bins of 0.1 on [0, 1]; EE 20 bins of 0.05",
      len(E.SS_CCQ_EDGES) == 11 and len(E.EE_EDGES) == 21 and E.SS_CCQ_EDGES[0] == 0.0 and E.SS_CCQ_EDGES[-1] == 1.0
      and E.EE_EDGES[-1] == 1.0)
check("frozen OC2_SPEC.md revision-2 md5 f0b83d29... (D-24) is the one the evaluator requires",
      E.md5(os.path.join(E.REPO, "analysis/stageE/OC2_SPEC.md")) == E.FROZEN_MD5["analysis/stageE/OC2_SPEC.md"]
      == "f0b83d29395972982e7ce34c389b77d7")
check("S-7 draw rule is e2_evaluate.draw_replicate itself (E2-8)", E.draw_replicate is E2.draw_replicate)

# 2. E-1 p(d) ---------------------------------------------------------------------------------------------------------
sys.path.insert(0, os.path.join(E.STAGE_E, "eaqte_operating_point"))
with contextlib.redirect_stdout(io.StringIO()):
    import ee_bound


def p_ref(d_m, ebn0_db, k):                      # independent transcription of TransmissionProbability, scalar math
    d_km = d_m / 1000.0
    if d_km <= 0.0:
        return 1.0
    f2 = 25.0 * 25.0
    alpha = 0.11 * (f2 / (1.0 + f2)) + 44.0 * (f2 / (4100.0 + f2)) + 2.75e-4 * f2 + 0.003
    A = math.pow(d_km, k) * math.pow(math.pow(10.0, alpha / 10.0), d_km)
    snr = math.pow(10.0, ebn0_db / 10.0) / A
    pe = 0.5 * (1.0 - math.sqrt(snr / (1.0 + snr)))
    return min(1.0, max(0.0, math.pow(1.0 - pe, 640.0)))


worst_b = worst_r = 0.0
ds = [0.0, 0.5, 1.0, 10.0, 100.0, 250.5, 500.0, 999.999, 1000.0, 1200.0, 2000.0]
for g in E.GRID:
    for k in (1.0, 1.5, 2.0):
        mine = E.p_of_d(np.array(ds), g, k)
        for d, v in zip(ds, mine):
            worst_b = max(worst_b, abs(v - ee_bound.p(d, g, k=k)))
            worst_r = max(worst_r, abs(v - p_ref(d, g, k)))
check("E-1 p(d) equals ee_bound.py and an independent scalar transcription (all g, k; 11 distances)",
      worst_b < 1e-15 and worst_r < 1e-15, f"max |diff| {worst_b:.1e} / {worst_r:.1e}")
check("E-1: Eb/N0 40 dB gives the C++ literal 10000.0; d <= 0 gives 1; p in [0, 1]; decreasing in d",
      10.0 ** (40.0 / 10.0) == 10000.0 and E.p_of_d(0.0, 40.0, 1.5) == 1.0
      and np.all(np.diff(E.p_of_d(np.linspace(1, 3000, 500), 20.0, 1.5)) <= 0))


# 3. E-4/E-5 CCQ against a line-by-line mirror of ComputeChannelQuality --------------------------------------------
def ccq_ref(history, p_now):                     # mutates history exactly as the C++ vector
    history.append(p_now)
    if len(history) > 10:
        history.pop(0)
    if len(history) < 2:
        return p_now
    mean = 0.0
    for v in history:
        mean += v
    mean /= len(history)
    var = 0.0
    for v in history:
        diff = v - mean
        var += diff * diff
    var /= len(history)
    c = p_now * (1.0 - math.tanh(var))
    return min(1.0, max(0.0, c))


rnd = random.Random(3)
n = 4000
seed = np.array([rnd.choice([12, 13]) for _ in range(n)]); o = np.array([rnd.randint(1, 6) for _ in range(n)])
x = np.array([rnd.randint(1, 6) for _ in range(n)])
p = np.array([rnd.choice([0.5, 0.9, rnd.random(), 1.0]) for _ in range(n)])
lags = E.history_lags(seed, o, x)
mine = E.ccq_from_history(p, lags)
hist, ref = {}, []
for i in range(n):
    ref.append(ccq_ref(hist.setdefault((seed[i], o[i], x[i]), []), p[i]))
check("E-4/E-5 CCQ bit-identical to a mirror of ComputeChannelQuality (4,000 interleaved events; outcome-blind order)",
      all(a == b for a, b in zip(mine.tolist(), ref)))
g15 = np.array([0.1 * (i % 7) + 0.05 for i in range(15)])
l15 = E.history_lags(np.zeros(15, int), np.zeros(15, int), np.zeros(15, int))
check("E-4 window 10 and append-then-compute: event 15 uses events 6..15; first event CCQ = p",
      sorted(int(l15[L][14]) for L in range(10)) == list(range(5, 15)) and np.all(l15[:, 14] >= 0)
      and E.ccq_from_history(g15, l15)[0] == g15[0])


# 4. E-6/E-6a/E-8 SS against a mirror of EstimateNeighborVelocity + ComputeStabilityScore --------------------------
def ss_ref(vi, lt, lf, pt, pf):
    if pt is None or (lt - pt) < 0.05:
        vj = (0.0, 0.0)
    else:
        dt = lt - pt
        vj = ((lf[0] - pf[0]) / dt, (lf[1] - pf[1]) / dt)
    ni = math.sqrt(vi[0] * vi[0] + vi[1] * vi[1]); nj = math.sqrt(vj[0] * vj[0] + vj[1] * vj[1])
    if ni < 1e-6 or nj < 1e-6:
        return 0.5
    vs = (vi[0] * vj[0] + vi[1] * vj[1]) / (ni * nj)
    return 0.5 * (1.0 + min(1.0, max(-1.0, vs)))


cases = [((0.3, 0.1), 10.0, (5, 5, 0), None, None), ((0.3, 0.1), 10.0, (5, 5, 0), 9.96, (4, 4, 0)),
         ((0.3, 0.1), 10.0, (5, 5, 0), 9.95, (4, 4, 0)), ((0.0, 0.0), 10.0, (5, 5, 0), 8.0, (4, 4, 0)),
         ((1e-7, 0.0), 10.0, (5, 5, 0), 8.0, (4, 4, 0)), ((0.3, 0.1), 10.0, (5, 5, 0), 8.0, (5, 5, 9)),
         ((0.3, 0.0), 10.0, (6, 5, 0), 9.0, (5, 5, 0)), ((0.3, 0.0), 10.0, (4, 5, 0), 9.0, (5, 5, 0)),
         ((0.2, 0.2), 10.0, (5, 6, 0), 9.0, (5, 5, 0))]
for _ in range(3000):
    cases.append(((rnd.uniform(-1, 1), rnd.uniform(-1, 1)), 100.0 + rnd.random(),
                  (rnd.uniform(0, 3000), rnd.uniform(0, 3000), rnd.uniform(0, 600)),
                  rnd.choice([None, 100.0 - rnd.random(), 100.0 + rnd.random() * 0.06]),
                  (rnd.uniform(0, 3000), rnd.uniform(0, 3000), rnd.uniform(0, 600))))
vi = np.array([c[0] for c in cases]); vj = np.zeros((len(cases), 2)); hv = np.zeros(len(cases), bool)
for i, (v, lt, lf, pt, pf) in enumerate(cases):
    a, b, h = E.neighbor_velocity(lt, lf, pt, pf if pt is not None else None)
    vj[i] = (a, b); hv[i] = h
ss, dflt = E.ss_values(vi, vj, hv)
refs = [ss_ref(v, lt, lf, pt, pf) for (v, lt, lf, pt, pf) in cases]
check("E-6/E-6a/E-8 SS bit-identical to the C++ mirror (3,009 cases: no previous position, dt < 0.05, zero/tiny "
      "norms, parallel/antiparallel/orthogonal)", all(a == b for a, b in zip(ss.tolist(), refs)))
check("E-6a/E-8 defaults: no previous -> 0.5; dt 0.04 -> 0.5; zero own velocity -> 0.5; tiny norm -> 0.5; "
      "parallel -> 1; antiparallel -> 0; default flags set", ss[0] == 0.5 and ss[1] == 0.5 and ss[3] == 0.5
      and ss[4] == 0.5 and ss[6] == 1.0 and ss[7] == 0.0 and dflt[0] and dflt[1] and dflt[3] and dflt[4] and not dflt[6])

# 5. E-9 ---------------------------------------------------------------------------------------------------------------
ee, fz = E.ee_and_freeze(np.array([0.1, 0.1, 0.0999999]), np.array([0.5, 0.5, 0.5]))
check("E-9 EE = 0.5 CCQ + 0.5 SS; freeze iff EE < 0.3 (EE exactly 0.3 not frozen)",
      ee[0] == 0.3 and not fz[0] and fz[2])

# 6. S-6/S-6a Mantel-Haenszel -----------------------------------------------------------------------------------------
table = {0: (10, 5, 4, 12), 1: (3, 2, 1, 6), 2: (0, 0, 0, 0)}
st_l, ex_l, si_l = [], [], []
for s, (a, b, c, d) in table.items():
    for cnt, ex, si in ((a, True, True), (b, True, False), (c, False, True), (d, False, False)):
        st_l += [s] * cnt; ex_l += [ex] * cnt; si_l += [si] * cnt
st6, ex6, si6 = np.array(st_l), np.array(ex_l), np.array(si_l)
num = sum(Fraction(a * d, a + b + c + d) for (a, b, c, d) in table.values() if a + b + c + d)
den = sum(Fraction(b * c, a + b + c + d) for (a, b, c, d) in table.values() if a + b + c + d)
cells = E.mh_cells(st6, ex6, si6, None, 3)
orr = E.mh_or(cells)
check("S-6/S-6a: OR_MH of a known stratified table equals the exact rational value (> 1); empty stratum ignored",
      abs(orr - float(num / den)) < 1e-14 * float(num / den) and orr > 1
      and cells.tolist() == [[10, 5, 4, 12], [3, 2, 1, 6], [0, 0, 0, 0]], f"OR {orr:.6f}")
check("S-6a orientation: reversing exposure gives exactly 1/OR",
      abs(E.mh_or(E.mh_cells(st6, ~ex6, si6, None, 3)) - float(den / num)) < 1e-14)
check("S-6a: exposure is EE < 0.3 (EE = 0.3 is unexposed)",
      E.mh_cells(np.array([0, 0]), np.array([0.3, 0.29]) < E.XI, np.array([True, True]), None, 1).tolist() == [[1, 0, 1, 0]])
w6 = np.array([rnd.randint(0, 3) for _ in range(len(st6))], float)
rep = np.repeat(np.arange(len(st6)), w6.astype(int))
check("weighted MH cells equal the cells of the multiplicity-expanded rows (exact)",
      np.array_equal(E.mh_cells(st6, ex6, si6, w6, 3), E.mh_cells(st6[rep], ex6[rep], si6[rep], None, 3)))


# 7. S-8/S-8b logistic model -------------------------------------------------------------------------------------------
def loglik(stratum, ee_, y, w, alpha, beta):
    eta = np.array([alpha[s] for s in stratum]) + beta * ee_
    return float(np.sum(w * (y * eta - np.log1p(np.exp(eta)))))


s1, m1, s0, m0 = 37, 23, 18, 42                   # single stratum, binary EE: beta = log(s1 m0 / (m1 s0))
st7 = np.zeros(s1 + m1 + s0 + m0, int); e7 = np.r_[np.ones(s1 + m1), np.zeros(s0 + m0)]
y7 = np.r_[np.ones(s1), np.zeros(m1), np.ones(s0), np.zeros(m0)].astype(bool)
fit7 = E.fit_logit(st7, e7, y7)
check("S-8: closed form (one stratum, binary EE) beta = log(s1 m0 / (m1 s0))",
      abs(fit7["beta"] - math.log(s1 * m0 / (m1 * s0))) < 1e-10, f"beta {fit7['beta']:.6f}")
g = np.random.Generator(np.random.PCG64(5))
N7 = 3000; st8 = g.integers(0, 4, N7); e8 = g.random(N7)
y8 = g.random(N7) < 1 / (1 + np.exp(-(-0.3 + 0.2 * st8 - 1.1 * e8)))
fit8 = E.fit_logit(st8, e8, y8)
al, be = fit8["alpha"], fit8["beta"]
mu = 1 / (1 + np.exp(-(np.array([al[s] for s in st8]) + be * e8)))
score = [float(np.sum((y8 - mu)[st8 == s])) for s in range(4)] + [float(np.sum((y8 - mu) * e8))]
ll0 = loglik(st8, e8, y8, np.ones(N7), al, be)
loc = all(ll0 >= loglik(st8, e8, y8, np.ones(N7), {k: v + dk for k, v in al.items()}, be + db)
          for dk in (-1e-3, 0, 1e-3) for db in (-1e-3, 0, 1e-3))
check("S-8: IRLS solution satisfies the score equations and is a likelihood maximum (brute-force neighbourhood)",
      max(abs(v) for v in score) < 1e-8 and loc, f"max |score| {max(abs(v) for v in score):.1e}")
w8 = g.integers(0, 3, N7).astype(float)
rep8 = np.repeat(np.arange(N7), w8.astype(int))
b_w = E.fit_logit(st8, e8, y8, w8)["beta"]; b_x = E.fit_logit(st8[rep8], e8[rep8], y8[rep8])["beta"]
check("S-8: multiplicity-weighted fit equals the fit on the expanded rows", abs(b_w - b_x) < 1e-9,
      f"|diff| {abs(b_w - b_x):.1e}")
st8b = np.r_[st8, np.full(50, 6)]; e8b = np.r_[e8, g.random(50)]; y8b = np.r_[y8, np.ones(50, bool)]
w8b = np.r_[np.ones(N7), np.zeros(50)]
check("S-8b: a zero-weight stratum has no column and leaves beta unchanged (bit-identical)",
      E.fit_logit(st8b, e8b, y8b, w8b)["beta"] == fit8["beta"] and 6 not in E.fit_logit(st8b, e8b, y8b, w8b)["alpha"])
check("S-8 direction: beta < 0 when higher EE lowers the odds of SILENT", fit8["beta"] < 0)

# 8. S-13 / S-13a observed-data failures (each must raise; nothing recovers) --------------------------------------------
F = E.FitFailure
ok = []
ok.append(raises(F, E.mh_or, E.mh_cells(np.zeros(4, int), np.array([True, True, False, False]),
                                         np.array([True, True, False, False]), None, 1)))       # b = c = 0
ok.append(raises(F, E.fit_logit, np.array([0, 0, 1, 1]), np.array([0.1, 0.9, 0.2, 0.8]),
                 np.array([True, True, True, False])))                                         # stratum 0 only SILENT
qs_e = np.r_[np.linspace(0, 0.4, 40), np.linspace(0.6, 1, 40)]
ok.append(raises(F, E.fit_logit, np.zeros(80, int), qs_e, qs_e < 0.5))                          # complete separation
qq_e = np.r_[np.linspace(0, 0.5, 40), np.full(10, 0.5), np.linspace(0.5, 1, 40)]
qq_y = np.r_[np.ones(40, bool), np.r_[np.ones(5), np.zeros(5)].astype(bool), np.zeros(40, bool)]
ok.append(raises(F, E.fit_logit, np.zeros(90, int), qq_e, qq_y))                                # quasi-complete separation
ok.append(raises(F, E.fit_logit, np.zeros(6, int), np.full(6, 0.4), np.array([1, 0, 1, 0, 1, 0], bool)))   # constant EE
ok.append(raises(F, E.fit_logit, np.zeros(6, int), 0.4 + 1e-15 * np.arange(6), np.array([1, 0, 1, 0, 1, 0], bool)))  # cond
ok.append(raises(F, E.fit_logit, np.zeros(6, int), np.array([0.1, np.nan, 0.3, 0.4, 0.5, 0.6]), np.array([1, 0, 1, 0, 1, 0], bool)))
saved = E.IRLS_MAX_IT
E.IRLS_MAX_IT = 1
ok.append(raises(F, E.fit_logit, st8, e8, y8))                                                  # iteration cap
E.IRLS_MAX_IT = saved
check("S-13/S-13a: zero-denominator OR, one-outcome stratum, complete and quasi-complete separation, constant EE, "
      "condition number > 1e12, non-finite EE and the iteration cap all raise", all(m is not None for m in ok),
      " | ".join((m or "NOT RAISED")[:38] for m in ok))
check("S-13: observed-data failure becomes ObservedFailure (hard stop)",
      raises(E.ObservedFailure, E.observed_relationship, np.zeros(4, int), np.array([0.1, 0.2, 0.5, 0.6]),
             np.array([True, True, False, False]), 1) is not None)

# 9. S-7/S-7c bootstrap and S-13b -----------------------------------------------------------------------------------------
gm = np.random.Generator(np.random.PCG64(11))
ok_m = True
for trial in range(40):
    S = list(range(12, 12 + int(gm.integers(1, 6))))
    U = {s: sorted(gm.choice(60, int(gm.integers(0, 6)), replace=False).tolist()) for s in S}
    M, idx = E.bootstrap_multiplicities(S, U, B=60, seed=12345)
    rng = np.random.Generator(np.random.PCG64(12345))
    for b in range(60):
        _, occ = E2.draw_replicate(rng, S, U)
        ref_m = E2.node_multiplicities(occ, U)
        ok_m &= all(M[b, idx[(s, xx)]] == ref_m[(s, xx)] for s in S for xx in U[s])
check("S-7: multiplicities equal e2_evaluate.node_multiplicities (occurrence-sum rule) over 40 random universes",
      ok_m)
Ma, _ = E.bootstrap_multiplicities([12, 13], {12: [3, 5], 13: [4]}, B=500)
Mb, _ = E.bootstrap_multiplicities([12, 13], {12: [3, 5], 13: [4]}, B=500)
check("S-7c: the shared draw sequence is deterministic (same PCG64(12345) draws every time)", np.array_equal(Ma, Mb))

# synthetic identifiable dataset over 2 seeds; node-level structure
gs = np.random.Generator(np.random.PCG64(21))
rows = []
for s in (12, 13):
    for xx in range(2, 9):
        for _ in range(60):
            stv = int(gs.integers(0, 3)); e = float(gs.random())
            rows.append((s, xx, stv, e, bool(gs.random() < 1 / (1 + math.exp(-(0.2 * stv - 1.0 * e))))))
sb = np.array([r[0] for r in rows]); xb = np.array([r[1] for r in rows]); stb = np.array([r[2] for r in rows])
eb = np.array([r[3] for r in rows]); yb = np.array([r[4] for r in rows])
Ub = {12: list(range(2, 9)), 13: list(range(2, 9))}
Mb2, idb = E.bootstrap_multiplicities([12, 13], Ub, B=64)
nodeb = np.array([idb[(int(s), int(xx))] for s, xx in zip(sb, xb)])
obs = E.observed_relationship(stb, eb, yb, 3)
orr_b, _ = E.bootstrap_or(stb, eb < E.XI, yb, nodeb, Mb2, Mb2.shape[1], 3)
beta1, _ = E.bootstrap_beta(stb, eb, yb, nodeb, Mb2, workers=1)
beta4, _ = E.bootstrap_beta(stb, eb, yb, nodeb, Mb2, workers=4)
check("bootstrap results do not depend on the number of worker processes (bit-identical)", np.array_equal(beta1, beta4))
okx = True
for b in (0, 7, 33):
    w = Mb2[b][nodeb]; r_ = np.repeat(np.arange(len(w)), w)
    okx &= abs(orr_b[b] - E.mh_or(E.mh_cells(stb[r_], eb[r_] < E.XI, yb[r_], None, 3))) < 1e-12 * orr_b[b]
    okx &= abs(beta1[b] - E.fit_logit(stb[r_], eb[r_], yb[r_])["beta"]) < 1e-9
check("weighted bootstrap OR_MH* and beta* equal the statistics of the multiplicity-expanded replicate datasets", okx)
lo, hi = E.interval(beta1)
xs = np.sort(beta1); hh = (len(xs) - 1) * 0.025
check("S-7 interval: linear percentiles 2.5 / 97.5 over all replicates",
      abs(lo - (xs[int(hh)] + (hh - int(hh)) * (xs[int(hh) + 1] - xs[int(hh)]))) < 1e-15 and lo <= hi)

# D-24 (OC2_SPEC revision 2): single-outcome strata in bootstrap replicates ------------------------------------------
# (a) a fragile but identifiable dataset: node (12, 2) carries every MATCH of stratum 0
yf = yb.copy()
yf[(stb == 0) & ~((sb == 12) & (xb == 2))] = True
obs_f = E.observed_relationship(stb, eb, yf, 3)                 # observed data identifiable (all strata informative)
Momit = np.ones_like(Mb2[:3]); Momit[1] = Mb2[5]; Momit[2] = Mb2[9]
Momit[0, idb[(12, 2)]] = 0                                       # replicate 1 omits that node -> stratum 0 only SILENT
beta_om, n_om = E.bootstrap_beta(stb, eb, yf, nodeb, Momit, workers=1)
w0 = Momit[0][nodeb].astype(float); keep0 = stb != 0
ref_a = E.fit_logit(stb[keep0], eb[keep0], yf[keep0], w0[keep0])["beta"]
check("D-24 (a): a single-outcome stratum in a replicate is omitted (S-8c); beta* is bit-identical to the fit on the "
      "informative strata only, and the replicate is counted", math.isfinite(obs_f["beta"]) and beta_om[0] == ref_a
      and n_om >= 1 and E.fit_logit(stb, eb, yf, w0, omit_single_outcome=True)["omitted_single_outcome_strata"] == [0],
      f"replicates with an omitted stratum {n_om}")
# (b) MH with a single-outcome stratum stays valid
orr_om, n_or_om = E.bootstrap_or(stb, eb < E.XI, yf, nodeb, Momit, Momit.shape[1], 3)
c0 = E.mh_cells(stb, eb < E.XI, yf, w0, 3).astype(int)
ex_b = sum(Fraction(int(a) * int(d), int(a + b + c + d)) for a, b, c, d in c0[1:]) / \
    sum(Fraction(int(b) * int(c), int(a + b + c + d)) for a, b, c, d in c0[1:])
check("D-24 (b): MH with a single-outcome stratum stays valid: its terms are zero and OR* equals the exact odds ratio "
      "over the remaining strata", c0[0][1] == 0 and c0[0][3] == 0 and abs(orr_om[0] - float(ex_b)) < 1e-12 * float(ex_b)
      and n_or_om >= 1)
# (c) a genuinely undefined MH replicate still stops (numerator > 0, denominator 0; and no positive weight)
m_c = np.array([[1, 0, 0, 1]])
msg_c = raises(E.ReplicateFailure, E.bootstrap_or, np.zeros(4, int), np.array([True, True, False, False]),
               np.array([True, False, True, False]), np.arange(4), m_c, 4, 1)
msg_c0 = raises(E.ReplicateFailure, E.bootstrap_or, stb, eb < E.XI, yb, nodeb, np.zeros_like(Mb2[:2]), Mb2.shape[1], 3)
check("D-24 (c): a replicate with sum_i b_i c_i / n_i = 0 still stops ('not evaluable')",
      msg_c is not None and "not evaluable" in msg_c and msg_c0 is not None and "replicate 1:" in msg_c0)
# (d) genuine separation by EE within the informative strata still stops
gd = np.random.Generator(np.random.PCG64(31))
sd_, ed_, yd_, nd_ = [], [], [], []
for nd in range(6):
    for _ in range(12):                                          # stratum 0: node 0 holds every MATCH
        sd_.append(0); ed_.append(float(gd.random())); yd_.append(nd != 0); nd_.append(nd)
    for _ in range(20):                                          # stratum 1: EE separates outcomes except at node 1
        e = float(gd.random()); sd_.append(1); ed_.append(e); yd_.append((e < 0.5) != (nd == 1)); nd_.append(nd)
sd_, ed_, yd_, nd_ = np.array(sd_), np.array(ed_), np.array(yd_), np.array(nd_)
obs_d = E.observed_relationship(sd_, ed_, yd_, 2)
m_d = np.ones((1, 6), dtype=np.int64); m_d[0, [0, 1]] = 0        # stratum 0 single-outcome (omitted), stratum 1 separated
msg_d = raises(E.ReplicateFailure, E.bootstrap_beta, sd_, ed_, yd_, nd_, m_d, 1)
check("D-24 (d): genuine separation by EE within the informative strata still stops", math.isfinite(obs_d["beta"])
      and msg_d is not None and "not evaluable" in msg_d, (msg_d or "NOT RAISED")[:110])
# (e) no informative stratum stops
m_e = np.zeros((1, 6), dtype=np.int64); m_e[0, 2] = 1
keep_e = sd_ == 0
msg_e = raises(E.ReplicateFailure, E.bootstrap_beta, sd_[keep_e], ed_[keep_e], yd_[keep_e], nd_[keep_e], m_e, 1)
check("D-24 (e): a replicate with no informative stratum stops (beta not identifiable)",
      msg_e is not None and "no informative stratum" in msg_e and "not evaluable" in msg_e)
# (f) no fallback, redraw or substitution
M_before = Mb2.copy()
beta_f, n_f = E.bootstrap_beta(stb, eb, yf, nodeb, Mb2, workers=2)
direct = all(beta_f[b] == E.fit_logit(stb, eb, yf, Mb2[b][nodeb].astype(float), omit_single_outcome=True)["beta"]
             for b in range(len(Mb2)))
check("D-24 (f): no fallback or redraw: one beta* per replicate, each equal to a direct fit on its own replicate; the "
      "draws are unchanged; omission count = replicates lacking node (12, 2); failures name their replicate and stop",
      len(beta_f) == len(Mb2) and direct and np.array_equal(Mb2, M_before) and n_f == int((Mb2[:, idb[(12, 2)]] == 0).sum())
      and "replicate 1:" in msg_d and "replicate 1:" in msg_e, f"{n_f} of {len(Mb2)} replicates with an omitted stratum")
msg_obs = raises(E.ObservedFailure, E.observed_relationship, np.array([0, 0, 1, 1, 1, 1, 1, 1]),
                 np.array([0.1, 0.9, 0.2, 0.8, 0.25, 0.7, 0.1, 0.9]),
                 np.array([True, True, True, True, False, False, True, False]), 2)   # MH defined; stratum 0 only SILENT
check("observed data keep S-13: a single-outcome stratum in the observed data is still a hard stop",
      msg_obs is not None and "only SILENT or only MATCH" in msg_obs, (msg_obs or "NOT RAISED")[:90])

# 10. S-1..S-4, S-12 characterization --------------------------------------------------------------------------------------
nd = 200
data = {"seed": np.full(nd, 12), "o": np.repeat([1, 2, 3, 4, 5], 40), "x": np.full(nd, 9),
        "out": np.array([0, 1, 2, 0] * 50)}
ssd = np.full(nd, 0.5); ccqd = np.full(nd, 0.9); eed = 0.5 * ccqd + 0.5 * ssd
frz = np.zeros(nd, bool); frz[:10] = True
pt = E.characterize(data, eed, ccqd, ssd, frz, np.zeros(nd, bool))
ms_n = int((data["out"] != 2).sum()); fr_ms = int(frz[data["out"] != 2].sum())
check("S-1: primary freeze fraction over MATCH+SILENT; all-opportunity fraction descriptive",
      pt["freeze_fraction_primary"] == fr_ms / ms_n and pt["freeze_fraction_all_descriptive"] == 10 / nd
      and pt["n_match_silent"] == ms_n)
check("S-2/S-3/S-4: 5 pairs with n = 30 judged in A and B; not inert, not saturated, active",
      pt["arm_a_judged_pairs"] == 5 and pt["arm_b_judged_pairs"] == 5 and not pt["inert"] and not pt["saturated"] and pt["active"])
pt0 = E.characterize(data, eed, ccqd, ssd, np.zeros(nd, bool), np.zeros(nd, bool))
check("S-2: zero freezes among MATCH+SILENT -> inert, not active", pt0["inert"] and not pt0["active"])
frz2 = np.zeros(nd, bool); frz2[np.flatnonzero(data["o"] <= 3)] = True            # pairs 1-3 lose all evidence
ptb = E.characterize(data, eed, ccqd, ssd, frz2, np.zeros(nd, bool))
frz3 = np.zeros(nd, bool); frz3[np.flatnonzero(np.isin(data["o"], [1, 2]) & (data["out"] != 2))] = True
frz3[np.flatnonzero(data["o"] == 3)[:12]] = True                                   # pair 3 keeps 21 >= 14 unfrozen
ptc = E.characterize(data, eed, ccqd, ssd, frz3, np.zeros(nd, bool))
check("S-3: saturated iff B judged < 0.5 x A judged (2 of 5 -> saturated; 3 of 5 -> not)",
      ptb["arm_b_judged_pairs"] == 2 and ptb["saturated"] and ptc["arm_b_judged_pairs"] == 3 and not ptc["saturated"])
check("S-4: activity finding uses the primary-k points only",
      E.activity_finding({g: (pt if g == 20.0 else pt0) for g in E.GRID}) is True
      and E.activity_finding({g: pt0 for g in E.GRID}) is False)
vals = np.array([0.0, 0.05, 0.1, 0.3, 0.999, 1.0])
h = np.histogram(vals, E.SS_CCQ_EDGES)[0]
check("S-12: fixed bins; 1.0 falls in the last bin; counts preserved", h[-1] == 2 and h.sum() == len(vals))
hd = pt["histograms"]
check("S-12: SS/CCQ/joint/EE histograms and default-SS counts for MATCH+SILENT and all opportunities",
      set(hd) == {"match_silent", "all_opportunities"} and len(hd["match_silent"]["SS"]) == 10
      and len(hd["match_silent"]["EE"]) == 20 and np.array(hd["match_silent"]["SS_CCQ_joint"]).shape == (10, 10)
      and sum(hd["all_opportunities"]["EE"]) == nd and sum(hd["match_silent"]["SS"]) == ms_n)
check("S-9: statement only if every active primary point has OR lower > 1 and beta upper < 0",
      E.s9_statement({15.0: {"OR_MH_interval": [1.1, 2], "beta_interval": [-2, -0.1]}}) is True
      and E.s9_statement({15.0: {"OR_MH_interval": [1.1, 2], "beta_interval": [-2, -0.1]},
                          20.0: {"OR_MH_interval": [0.9, 2], "beta_interval": [-2, -0.1]}}) is False
      and E.s9_statement({}) is None)

# 11. P-1 parity logic on a synthetic run ----------------------------------------------------------------------------------
pr = os.path.join(TMP, "parity", "run_7"); os.makedirs(pr)
open(os.path.join(pr, "v1_7.tr"), "w").close()
with open(os.path.join(pr, "v1_7_mobility.csv"), "w") as fh:
    fh.write("time,node_id,x,y,z,vx,vy,vz\n")
    for t in range(0, 30):
        fh.write(f"{t + 0.5},4,100,200,10,0.3,0.1,0\n")
f1, f2_ = (400.0, 600.0, 10.0), (401.0, 600.5, 10.0)
p1 = float(E.p_of_d(math.dist((100, 200, 10), f1), 40.0, 1.5))
ssv = ss_ref((0.3, 0.1), 12.25, f2_, 10.5, f1)
lines = [f"[RXHDR] node=5 tx=9 src=9 pk=0 f={f1[0]}:{f1[1]}:{f1[2]} d=0:0:0 tgt=1500:1500:0 t=10.5",
         "[EAQTE-SS] neighbor=09 SS=0.5", f"[EAQTE-CCQ] neighbor=09 CCQ={p1:.6g}",
         f"[RXHDR] node=5 tx=9 src=9 pk=1 f={f2_[0]}:{f2_[1]}:{f2_[2]} d=0:0:0 tgt=1500:1500:0 t=12.25",
         f"[EAQTE-SS] neighbor=09 SS={ssv:.6g}", "[EAQTE] TX src=5 pk=3 d=10 t=13.0", "[EAQTE-SS] neighbor=05 SS=0.5"]
with open(os.path.join(pr, "stderr.log"), "w") as fh:
    fh.write("\n".join(lines) + "\n")
# node 5's own velocity row: write rows for node index 4 (address 5)
st_par = E.parity_run(pr, 7)
check("P-1: matching CCQ and SS (C++ convention, including the current decode) pass; origination context not compared",
      st_par["ccq_compared"] == 1 and st_par["ss_compared"] == 2 and st_par["not_comparable"] == 1
      and not st_par["unexplained"], str({k: v for k, v in st_par.items() if k != "unexplained"}))
with open(os.path.join(pr, "stderr.log"), "w") as fh:
    fh.write("\n".join(lines[:2] + [f"[EAQTE-CCQ] neighbor=09 CCQ={p1 * 0.99:.6g}"]) + "\n")
check("P-1: an unexplained mismatch stops OC-2", raises(E.Stop, E.parity, [(7, pr)]) is not None)
with open(os.path.join(pr, "stderr.log"), "w") as fh:
    fh.write("\n".join([lines[0].replace("t=10.5", "t=10"), "[EAQTE-CCQ] neighbor=09 CCQ=0.123"]) + "\n")
st_ws = E.parity_run(pr, 7)
check("P-1: a mismatch at an exact whole second is counted separately, not as unexplained",
      st_ws["whole_second_mismatch"] == 1 and not st_ws["unexplained"])

# 12. development seed-1 checks: E-2/E-3/E-7 reconstruction, parity, end-to-end R-1/R-2/R-3, S-7c, S-13b ------------------
dev = opt("--dev-runs")
if dev:
    clean, *others = [os.path.abspath(os.path.expanduser(d)) for d in dev.split(",")]
    cal, lab, labels = E.frozen_calibration()
    run = E.load_run(clean, 1, lab)
    check("E-2/E-3: O1 table rebuild matches every xpos and age of the development opportunity file", run["n_rows"] > 0)
    mobrows = {}
    for r in csv.DictReader(open(os.path.join(clean, "v1_1_mobility.csv"))):
        mobrows[(int(r["node_id"]) + 1, float(r["time"]))] = r
    half = all(abs(t - math.floor(t) - 0.5) < 1e-12 for (_, t) in list(mobrows)[:5000])
    opp = list(csv.DictReader(open(os.path.join(clean, "e1_opportunities.csv"))))
    ok_e7, ok_e2 = True, True
    for i in random.Random(9).sample(range(len(opp)), 400):
        r = opp[i]; t0 = float(r["t0"]); row = mobrows[(int(r["o"]), math.floor(t0) + 0.5)]
        po = (float(row["x"]), float(row["y"]), float(row["z"])); xp = tuple(float(v) for v in r["xpos"].split(":"))
        ok_e2 &= run["d"][i] == math.sqrt(sum((a - b) ** 2 for a, b in zip(po, xp)))
        ok_e7 &= tuple(run["vi"][i]) == (float(row["vx"]), float(row["vy"]))
    check("E-3/E-7: own position and velocity come from the mobility row sampled at floor(t0) + 0.5 (400 rows)",
          half and ok_e7)
    check("E-2: d is the 3D distance from that row's position to xpos (400 rows, bit-identical)", ok_e2)
    dec, own, _ = E.load_inputs(clean, 1)
    rows_ = E.read_opportunities(os.path.join(clean, "e1_opportunities.csv"))
    tabs = E.rebuild_tables(rows_, dec, own)
    ok_prev = True
    for i in random.Random(4).sample(range(len(rows_)), 400):
        r = rows_[i]; key = r["t0"] if r["own"] == 0 else r["t0"] - E.res6(r["t0"])
        hx = sorted((t, s, p, f) for (t, tx, s, p, f, d, tgt) in dec.get(r["o"], []) if tx == r["x"] and t < key)
        last2 = hx[-2:]
        exp = (last2[-1][0], last2[-1][3], last2[0][0] if len(last2) == 2 else None, last2[0][3] if len(last2) == 2 else None)
        ok_prev &= tabs[i] == exp
    check("E-6: X's last and previous decoded positions equal an independent strictly-before lookup (400 rows)", ok_prev)
    par = E.parity_run(clean, 1)
    check("P-1 on development seed 1: CCQ and SS parity with the C++ logs, no unexplained mismatch",
          par["ccq_compared"] > 1000 and par["ss_compared"] > 1000 and not par["unexplained"],
          f"CCQ {par['ccq_compared']}, SS {par['ss_compared']}, whole-second {par['whole_second_mismatch']}")

    def make_root(path, n_runs):
        srcs = [clean] + others
        for i in range(1, n_runs + 1):
            rd = os.path.join(path, f"run_{i}"); os.makedirs(rd)
            src = srcs[(i - 1) % len(srcs)]
            for f in ("stderr.log", "e1_opportunities.csv"):
                os.symlink(os.path.join(src, f), os.path.join(rd, f))
            for suf in (".tr", "_mobility.csv", "_meta.csv"):
                os.symlink(os.path.join(src, f"v1_1{suf}"), os.path.join(rd, f"v1_{i}{suf}"))
        return path

    r1 = make_root(os.path.join(TMP, "dev1"), 1)
    r9 = make_root(os.path.join(TMP, "dev9"), 9)
    seeds9 = ",".join(str(i) for i in range(1, 10))
    run_ = lambda *a: subprocess.run([sys.executable, os.path.join(HERE, "oc2_evaluate.py"), *a], capture_output=True, text=True, env=ENV)
    o1, o2 = os.path.join(TMP, "out1"), os.path.join(TMP, "out2")
    a1 = run_("--dev", "--seeds", seeds9, "--e1-root", r9, "--out", o1, "--B", "20", "--workers", "4")
    a2 = run_("--dev", "--seeds", seeds9, "--e1-root", r9, "--out", o2, "--B", "20", "--workers", "2")
    check("development end-to-end (9 symlinked seed-1 runs, B = 20) completes twice", a1.returncode == 0 and a2.returncode == 0,
          (a1.stderr + a2.stderr)[-300:])
    if a1.returncode == 0 and a2.returncode == 0:
        j1, j2 = json.load(open(os.path.join(o1, E.OUT_JSON))), json.load(open(os.path.join(o2, E.OUT_JSON)))
        c1, c2 = dict(j1), dict(j2); c1.pop("created_utc"); c2.pop("created_utc")
        check("R-2: two evaluations (different worker counts) identical apart from created_utc", c1 == c2)
        check("development results labelled DEVELOPMENT ONLY", j1["status"].startswith("DEVELOPMENT ONLY"))
        prim = j1["primary (k = 1.5)"]
        check("R-3: every grid value reported for the primary and both secondary k; activity finding = any active at k = 1.5",
              all(len(j1[k]["points"]) == 10 for k in ("primary (k = 1.5)", "secondary (k = 1)", "secondary (k = 2)"))
              and prim["activity_finding"] == any(v["active"] for v in prim["points"].values()))
        rels = [v["relationship"] for key in ("primary (k = 1.5)", "secondary (k = 1)", "secondary (k = 2)")
                for v in j1[key]["points"].values() if v["relationship"]]
        check("D-24 transparency: replicates_with_single_outcome_strata recorded per active point for OR_MH and beta",
              rels and all(set(r["replicates_with_single_outcome_strata"]) == {"OR_MH", "beta"}
                           and all(0 <= v <= 20 for v in r["replicates_with_single_outcome_strata"].values()) for r in rels))
        check("R-1c: md5s of every input file per run, frozen files and code recorded",
              all(set(v) == {"stderr.log", f"v1_{k[4:]}.tr", f"v1_{k[4:]}_mobility.csv", "e1_opportunities.csv"}
                  for k, v in j1["provenance"]["inputs_md5"].items()) and len(j1["provenance"]["inputs_md5"]) == 9
              and set(E.FROZEN_MD5) == set(j1["provenance"]["frozen_md5"]))
        before = E.md5(os.path.join(o1, E.OUT_JSON))
        a3 = run_("--dev", "--seeds", seeds9, "--e1-root", r9, "--out", o1, "--B", "20")
        check("R-1: refuses to overwrite existing outputs", a3.returncode != 0 and E.md5(os.path.join(o1, E.OUT_JSON)) == before)
    a4 = run_("--e1-root", r9, "--out", os.path.join(TMP, "prod"), "--seeds", "1")
    a5 = run_("--e1-root", r9, "--out", os.path.join(TMP, "prod"))
    check("OC-2 mode rejects --seeds; on non-OC-2 inputs it stops (R-1b guard or inputs) without writing",
          a4.returncode != 0 and a5.returncode == 2 and not os.path.exists(os.path.join(TMP, "prod")), a5.stderr.strip()[-160:])
    a6 = run_("--dev", "--seeds", "1", "--e1-root", r1, "--out", os.path.join(HERE, "devx"), "--B", "20")
    check("development output inside analysis/stageE/oc2 refused", a6.returncode != 0 and not os.path.exists(os.path.join(HERE, "devx")))
    a7 = run_("--dev", "--seeds", "1", "--e1-root", r1, "--out", os.path.join(TMP, "one"), "--B", "20")
    check("D-24 end-to-end (single development seed): no stop caused by a single-outcome stratum in a replicate",
          a7.returncode == 0 or (a7.returncode == 2 and "only SILENT or only MATCH" not in a7.stderr),
          f"exit {a7.returncode} " + a7.stderr.strip()[-120:])
    calls = []
    orig = E.bootstrap_multiplicities
    E.bootstrap_multiplicities = lambda *a, **k: (calls.append(1), orig(*a, **k))[1]
    resd = E.evaluate(r9, tuple(range(1, 10)), True, B=20, workers=4)
    E.bootstrap_multiplicities = orig
    n_active = sum(v["active"] for key in ("primary (k = 1.5)", "secondary (k = 1)", "secondary (k = 2)")
                   for v in resd[key]["points"].values())
    check("S-7c: one shared draw sequence for every (g, k) point and both statistics", calls == [1] and n_active > 1,
          f"draws generated {len(calls)} time(s) for {n_active} active points")
else:
    print("  (development seed-1 checks skipped: --dev-runs not given)")

check("no bytecode caches written next to e1/, e2/ or oc2/",
      not any(os.path.exists(os.path.join(E.STAGE_E, d, "__pycache__")) for d in ("e1", "e2", "oc2", "eaqte_operating_point")))
shutil.rmtree(TMP)
print(f"\n{'ALL CHECKS PASSED' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
sys.exit(1 if FAILS else 0)
