#!/usr/bin/env python3
"""Tests for e2_evaluate.py (frozen ../E2_SPEC.md, commit a87ffbc; D-20).
Synthetic inputs only, plus (optional) read-only use of DEVELOPMENT seed-1 attacker runs for an end-to-end check.
No E2 data, no seed 2-11 data, no simulation. Exit code 0 only if every check passes.

usage: test_e2_evaluate.py [--tmp DIR] [--dev-p075 RUNDIR --dev-p100 RUNDIR]
       (dev RUNDIRs hold v1_1.* and e1_opportunities.csv of development seed 1)
"""
import sys, os, csv, json, math, random, shutil, subprocess, tempfile, hashlib
from fractions import Fraction
sys.dont_write_bytecode = True
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import e2_evaluate as E

FAILS = []
args = sys.argv[1:]
opt = lambda k: (args[args.index(k) + 1] if k in args else None)
TMP = tempfile.mkdtemp(prefix="e2test_", dir=opt("--tmp"))


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def raises_stop(fn, *a):
    try:
        fn(*a)
    except E.Stop:
        return True
    return False


# 1. frozen constants ----------------------------------------------------------------------------------------
check("constants: seeds 2-11, n_ref 14, FA 0.05, AUC 0.70/0.5, G2 43/10, B 10,000, PCG64 seed 12345",
      (E.SEEDS_E2, E.N_REF, E.FA_BAR, E.AUC_BAR, E.AUC_NULL, E.G2_MIN_PAIRS, E.G2_MIN_NODES, E.B_BOOT, E.BOOT_SEED)
      == (tuple(range(2, 12)), 14, 0.05, 0.70, 0.5, 43, 10, 10000, 12345))
check("percentiles: FA 5th (one-sided LB), FA 97.5th (two-sided UB), TDR 2.5th, AUC 2.5th (two-sided LBs)",
      E.PCT == {"fa_lb": 5.0, "fa_ub": 97.5, "tdr_lb": 2.5, "auc_lb": 2.5})
check("p sets: p075 = 0.75 (gates), p100 = 1.0 (ceiling only)", E.P_SETS == (("p075", 0.75), ("p100", 1.0)))

# 2. frozen calibration ----------------------------------------------------------------------------------------
calp = os.path.join(E.REPO, "analysis/stageE/e1/e1_calibration_rev4.json")
check("calibration JSON md5 0ca88a0e...", E.md5(calp) == "0ca88a0e4c8fc56f63e6b44b496b65fd")
cal = E.frozen_calibration(calp)
TAU = [0.6667795212943134, 0.6667795212943134, 0.4969825078271633, 0.4969825078271633, 0.43575356720447084,
       0.43575356720447084, 0.43575356720447084, 0.43575356720447084, 0.4239204803487851]
check("tau_A,b bit-identical to the frozen values", [x.hex() for x in cal["tau"]] == [x.hex() for x in TAU])
check("edges L = [14, 23, 34, 46, 61, 76, 89, 95, 139]; n_ref 14; n_max 554",
      cal["L"] == [14, 23, 34, 46, 61, 76, 89, 95, 139] and cal["n_ref"] == 14 and cal["n_max"] == 554)
raw = json.load(open(calp))
check("all 18 cells map to a frozen merged stratum; q identical to the JSON strata",
      len(cal["lab"]) == 18 and all(cal["q"][l].hex() == raw["strata"][l]["q"].hex() for l in cal["lab"].values()))
check("bin_of boundaries: 13 none, 14 b1, 22 b1, 23 b2, 138 b8, 139 b9, 554 b9, 10^6 b9",
      [E.bin_of(n, cal["L"]) for n in (13, 14, 22, 23, 138, 139, 554, 10**6)] == [None, 0, 0, 1, 7, 8, 8, 8])

# 3. pair statistic, judging, strict flag, OTHER-UP excluded (synthetic opportunity file) ----------------------
root = os.path.join(TMP, "synth")
os.makedirs(os.path.join(root, "run_99"))
rows, expect = [], {}
rnd = random.Random(11)
for (o, x, n) in ((5, 7, 14), (6, 7, 13), (5, 8, 40)):
    for i in range(n):
        cell = (rnd.randint(0, 1), rnd.randint(0, 2), rnd.randint(0, 2))
        out = "SILENT" if rnd.random() < 0.4 else "MATCH"
        rows.append([99, o, x, 3, 2, i, *cell, out])
    for i in range(3):
        rows.append([99, o, x, 3, 2, 1000 + i, 0, 0, 0, "OTHER-UP"])
with open(os.path.join(root, "run_99", "e1_opportunities.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["run", "o", "x", "u", "s", "p", "k1", "k2", "k3", "out"]); w.writerows(rows)
for o, x in ((5, 7), (6, 7), (5, 8)):                      # independent recomputation, same summation order
    sel = [r for r in rows if r[1] == o and r[2] == x and r[9] != "OTHER-UP"]
    n, K, Ev = len(sel), sum(r[9] == "SILENT" for r in sel), 0.0
    for r in sel:
        Ev += cal["q"][cal["lab"][(r[6], r[7], r[8])]]
    expect[(99, o, x)] = (n, (K - Ev) / n)
P = E.judge_pairs(root, 99, cal)
check("pairs: n excludes OTHER-UP; r = (K - E)/n bit-identical to an independent recomputation",
      all(P[k]["n"] == v[0] and P[k]["r"] == v[1] for k, v in expect.items()))
check("judged iff n >= 14 (n = 13 not judged, n = 14 judged)", not P[(99, 6, 7)]["judged"] and P[(99, 5, 7)]["judged"])
r0 = P[(99, 5, 7)]["r"]
c_eq = dict(cal, tau=[r0] * 9); c_lo = dict(cal, tau=[float(np.nextafter(r0, -1.0))] * 9)
check("flag is strict: r == tau not flagged; tau one ulp below r flagged",
      not E.judge_pairs(root, 99, c_eq)[(99, 5, 7)]["flag"] and E.judge_pairs(root, 99, c_lo)[(99, 5, 7)]["flag"])
opp = E.opportunity_rows(os.path.join(root, "run_99"))
check("ceiling opportunity rows exclude OTHER-UP", len(opp) == 14 + 13 + 40)

# 4. corrected bootstrap multiplicity: the E2_SPEC worked example ------------------------------------------------
U = {2: [5, 9], 3: [7], 4: [3]}
occ = [(2, np.array([0, 0])), (2, np.array([0, 1])), (3, np.array([0]))]
m = E.node_multiplicities(occ, U)
check("toy example: m(2,5) = 3, m(2,9) = 1, m(3,7) = 1, m(4,3) = 0",
      dict(m) == {(2, 5): 3, (2, 9): 1, (3, 7): 1} and m[(4, 3)] == 0)
toyH = [((2, 1, 5), 1), ((2, 4, 5), 0), ((2, 1, 9), 0), ((3, 2, 7), 1)]
faw = lambda mm: Fraction(sum(mm.get((s, x), 0) * f for (s, o, x), f in toyH), sum(mm.get((s, x), 0) for (s, o, x), f in toyH))
check("toy example: corrected FA* = 4/8 = 0.500", faw(m) == Fraction(1, 2))
check("toy example: rejected product readings give 5/9, 3/7, 7/15 (none equals 0.500)",
      [faw(mm) for mm in ({(2, 5): 4, (2, 9): 0, (3, 7): 1}, {(2, 5): 2, (2, 9): 2, (3, 7): 1}, {(2, 5): 6, (2, 9): 2, (3, 7): 1})]
      == [Fraction(5, 9), Fraction(3, 7), Fraction(7, 15)])


# 5. draw order: one sigma call, then one node call per occurrence with a non-empty universe ----------------------
class Rec:
    def __init__(self, seed):
        self.g, self.calls = np.random.Generator(np.random.PCG64(seed)), []

    def integers(self, lo, hi, size):
        self.calls.append((lo, hi, size)); return self.g.integers(lo, hi, size)


S3, U3 = [2, 3, 4], {2: [5, 9], 3: [], 4: [3]}
ok = True
for sd in range(200):
    rec = Rec(sd); sigma, occ3 = E.draw_replicate(rec, S3, U3)
    want = [(0, 3, 3)] + [(0, len(U3[S3[i]]), len(U3[S3[i]])) for i in sigma if U3[S3[i]]]
    ok &= rec.calls == want and all((nu is None) == (not U3[s]) for s, nu in occ3)
check("draw order: integers(0,|S|,|S|), then integers(0,|U_s|,|U_s|) per occurrence; no call for empty U_s", ok)
ok = True
g = np.random.Generator(np.random.PCG64(3))
for _ in range(2000):
    S = list(range(2, 2 + g.integers(1, 8)))
    Ur = {s: sorted(g.choice(100, g.integers(0, 6), replace=False).tolist()) for s in S}
    sigma, oc = E.draw_replicate(g, S, Ur)
    mm = E.node_multiplicities(oc, Ur); c = {s: int(sum(S[i] == s for i in sigma)) for s in S}
    ok &= all(sum(mm[(s, x)] for x in Ur[s]) == c[s] * len(Ur[s]) for s in S)
check("identity sum_X m(s, X) = c(s)|U_s| (2,000 random replicates, repeated and empty seeds)", ok)

# 6. AUC: fast weighted index == exact double sum (ties 1/2) ------------------------------------------------------
def auc_exact(rD, mD, rH, mH):
    num = sum(Fraction(int(a)) * Fraction(int(b)) * (1 if x > y else Fraction(1, 2) if x == y else 0)
              for x, a in zip(rD, mD) for y, b in zip(rH, mH))
    den = Fraction(int(sum(mD))) * Fraction(int(sum(mH)))
    return None if den == 0 else num / den


ok = True; rng = random.Random(5)
for _ in range(400):
    vals = [rng.choice([0.1, 0.2, 0.25, 0.3]) if rng.random() < 0.5 else rng.random() for _ in range(40)]
    rD, rH = vals[:rng.randint(0, 12)], vals[12:12 + rng.randint(0, 28)]
    mD = [rng.randint(0, 5) for _ in rD]; mH = [rng.randint(0, 5) for _ in rH]
    got = E.AUCIndex(rD, rH)(np.array(mD, float), np.array(mH, float)) if rD and rH else None
    ex = auc_exact(rD, mD, rH, mH) if rD and rH else None
    ok &= (got is None and ex is None) or (got is not None and ex is not None and got == float(ex))
check("weighted AUC equals the exact double sum, ties 1/2 (400 random cases incl. zero weights; bit-identical)", ok)
check("AUC: all scores tied -> 0.5; zero total weight -> undefined",
      E.AUCIndex([0.3, 0.3], [0.3])(np.ones(2), np.ones(1)) == 0.5 and E.AUCIndex([0.3], [0.2])(np.zeros(1), np.ones(1)) is None)

# 7. bootstrap == literal reference (occurrence-specific draws, summed multiplicities, zero denominators) -----------
def pop(rnd, seeds):
    H, D = [], []
    for s in seeds:
        for x in rnd.sample(range(2, 40), rnd.randint(0, 5)):
            for o in rnd.sample(range(2, 40), rnd.randint(1, 3)):
                (D if x % 7 == 0 else H).append({"seed": s, "o": o, "x": x, "r": rnd.choice([0.1, 0.4, rnd.random()]),
                                                 "flag": rnd.random() < 0.3})
    return H, D


def reference(S, H, D, B, seed):
    U = {s: sorted({p["x"] for p in H + D if p["seed"] == s}) for s in S}
    g = np.random.Generator(np.random.PCG64(seed)); out = []
    for _ in range(B):
        sigma = g.integers(0, len(S), len(S)); m = {}
        for t in range(len(S)):                                  # each occurrence draws its own nodes
            s = S[sigma[t]]
            if U[s]:
                for j in g.integers(0, len(U[s]), len(U[s])):
                    m[(s, U[s][j])] = m.get((s, U[s][j]), 0) + 1
        w = lambda p: m.get((p["seed"], p["x"]), 0)
        sH, sD = sum(w(p) for p in H), sum(w(p) for p in D)
        fa = 1.0 if sH == 0 else float(Fraction(sum(w(p) * p["flag"] for p in H), sH))
        td = 0.0 if sD == 0 else float(Fraction(sum(w(p) * p["flag"] for p in D), sD))
        a = auc_exact([p["r"] for p in D], [w(p) for p in D], [p["r"] for p in H], [w(p) for p in H]) if H and D else None
        out.append((fa, td, 0.0 if a is None else float(a)))
    return out


ok = True; zero_seen = 0; rnd = random.Random(21)
for trial in range(6):
    S = list(range(2, 2 + rnd.randint(1, 5)))
    H, D = pop(rnd, S)
    bs = E.bootstrap(S, H, D, B=150, seed=12345)
    ref = reference(S, H, D, 150, 12345)
    ok &= all((bs["fa"][i], bs["tdr"][i], bs["auc"][i]) == ref[i] for i in range(150))
    zero_seen += sum(bs["zero"].values())
check("bootstrap replicates bit-identical to a literal reference (6 synthetic populations x 150 replicates)", ok)
H0 = [{"seed": 2, "o": 3, "x": 4, "r": 0.1, "flag": False}]
D0 = [{"seed": 3, "o": 3, "x": 7, "r": 0.5, "flag": True}]
bs0 = E.bootstrap([2, 3], H0, D0, B=400, seed=12345)
nodraw3 = sum(1 for i in range(400) if bs0["tdr"][i] == 0.0)
check("zero denominators: TDR* = 0 and AUC* = 0 when D undrawn, FA* = 1 when H undrawn; counted, never discarded",
      len(bs0["fa"]) == 400 and bs0["zero"]["tdr"] == nodraw3 > 0 and bs0["zero"]["fa"] > 0
      and bs0["zero"]["auc"] == sum(1 for i in range(400) if bs0["fa"][i] == 1.0 or bs0["tdr"][i] == 0.0)
      and all(bs0["auc"][i] == 0.0 for i in range(400) if bs0["tdr"][i] == 0.0), f"{bs0['zero']}")
b1 = E.bootstrap([2, 3, 4], *pop(random.Random(8), [2, 3, 4]), B=200); b2 = E.bootstrap([2, 3, 4], *pop(random.Random(8), [2, 3, 4]), B=200)
check("bootstrap deterministic (two runs identical)", all(np.array_equal(b1[k], b2[k]) for k in ("fa", "tdr", "auc")))

# 8. percentiles: linear interpolation over all values ---------------------------------------------------------------
ok = True; g = np.random.Generator(np.random.PCG64(1))
for _ in range(300):
    v = g.random(g.integers(1, 60)); x = np.sort(v)
    for qq in (2.5, 5.0, 97.5):
        h = (len(x) - 1) * qq / 100; lo = math.floor(h); hi = min(lo + 1, len(x) - 1)
        ok &= abs(E.pct(v, qq) - (x[lo] + (h - lo) * (x[hi] - x[lo]))) < 1e-15
check("pct = linear interpolation (h = (N-1)q/100) at 2.5, 5, 97.5", ok)

# 9. decision rule (E2-7, E2-9, E2-14) ---------------------------------------------------------------------------------
d = E.decide(43, 10, 500, 0.05, 0.08, 0.70, 0.51, 0.081)
check("all pass at the boundaries: |D| 43, 10 nodes, FA LB = 0.05, AUC = 0.70, AUC LB 0.51, TDR LB > FA UB",
      d["G2"]["pass"] and d["G2b"] == {"item1_fa": True, "item2_auc": True, "item3_tdr_vs_fa": True, "pass": True}
      and d["conclusions"] == [] and d["outcome"].startswith("G2 PASS and G2b PASS"))
check("G2 fails at 42 pairs and at 9 nodes", not E.decide(42, 10, 5, 0, 0, 1, 1, 1)["G2"]["pass"]
      and not E.decide(43, 9, 5, 0, 0, 1, 1, 1)["G2"]["pass"])
check("item 1 fails just above 0.05", E.decide(50, 12, 5, 0.0500001, 0.06, 0.9, 0.8, 0.9)["G2b"]["item1_fa"] is False)
check("item 2 fails at AUC LB = 0.5 and at AUC 0.6999",
      not E.decide(50, 12, 5, 0.01, 0.06, 0.9, 0.5, 0.9)["G2b"]["item2_auc"] and not E.decide(50, 12, 5, 0.01, 0.06, 0.6999, 0.6, 0.9)["G2b"]["item2_auc"])
d3 = E.decide(50, 12, 5, 0.01, 0.30, 0.9, 0.8, 0.30)
check("item 3 is strict (TDR LB == FA UB fails) -> G2b FAIL, roadmap stops",
      d3["G2b"]["item3_tdr_vs_fa"] is False and d3["G2b"]["pass"] is False and d3["conclusions"] == [E.CONCLUSION_G2B]
      and "roadmap stops" in d3["outcome"])
d4 = E.decide(20, 4, 300, 0.03, 0.09, 0.8, 0.6, 0.5)
check("G2 fail + item 1 pass -> items 2-3 not interpretable, extension outcome, G2 conclusion only",
      d4["G2b"]["item2_auc"].startswith("not interpretable") and d4["G2b"]["pass"] is None
      and d4["conclusions"] == [E.CONCLUSION_G2] and "extension" in d4["outcome"])
d5 = E.decide(20, 4, 300, 0.07, 0.12, None, 0.0, 0.0)
check("G2 fail + item 1 fail -> G2b FAIL, roadmap stops, both conclusions",
      d5["G2b"]["pass"] is False and d5["conclusions"] == [E.CONCLUSION_G2, E.CONCLUSION_G2B] and "roadmap stops" in d5["outcome"])
check("H empty -> STOP, G2b not passed", E.decide(50, 12, 0, 1, 1, None, 0, 0)["outcome"].startswith("STOP")
      and E.decide(50, 12, 0, 1, 1, None, 0, 0)["G2b"]["pass"] is False)

# 10. populations and labels (E2-5, E2-6) ------------------------------------------------------------------------------
pp = lambda n, r, f: {"n": n, "K": 0, "E": 0.0, "r": r, "judged": n >= 14, "bin": 1, "flag": f}
runs = {2: {"P": {(2, 10, 20): pp(20, 0.1, False),        # malicious O=10, honest X=20 -> H
                  (2, 11, 21): pp(30, 0.9, True),         # active X=21 -> D
                  (2, 11, 22): pp(30, 0.9, True),         # inactive X=22 -> excluded
                  (2, 12, 21): pp(13, 0.9, True),         # not judged -> excluded
                  (2, 12, 20): pp(600, 0.2, False)},      # honest, n > n_max -> H and listed
            "gt": {"malicious": {10, 21, 22}, "active": {21}}},
        3: {"P": {(3, 5, 21): pp(15, 0.7, False)}, "gt": {"malicious": {21}, "active": {21}}}}
H, D, above = E.populations(runs, 554)
check("malicious observers kept; inactive-malicious and unjudged pairs excluded",
      [(p["seed"], p["o"], p["x"]) for p in H] == [(2, 10, 20), (2, 12, 20)]
      and [(p["seed"], p["o"], p["x"]) for p in D] == [(2, 11, 21), (3, 5, 21)])
check("distinct malicious nodes counted as (seed, X): X = 21 in seeds 2 and 3 counts twice",
      len({(p["seed"], p["x"]) for p in D}) == 2)
check("judged pairs above n_max listed separately (and still judged)", [(a["x"], a["label"]) for a in above] == [(20, "honest")])

gt = {"malicious": {21, 22, 23, 24, 25}, "active": {21, 23, 24, 25}, "sink": 1, "nodes": set(range(1, 31)),
      "drops": {(21, 3, 1), (21, 3, 2), (23, 4, 1), (24, 4, 2)}}
Pc = {(2, 6, 23): pp(10, 0.9, False), (2, 6, 24): pp(20, 0.1, False), (2, 7, 25): pp(20, 0.9, True),
      (2, 7, 5): pp(20, 0.1, False), (2, 8, 6): pp(5, 0.1, False)}
oppc = [(21, 3, 1, 1), (21, 3, 1, 0), (23, 4, 1, 0), (23, 9, 9, 0), (24, 7, 7, 1), (25, 2, 2, 0), (5, 1, 1, 0), (6, 1, 1, 0)]
c = E.ceiling_run(2, Pc, gt, oppc)
check("ceiling: drops observable 2/4 (O=U 1, O!=U 2); classes unobservable/insufficient/detected/missed",
      (c["drops"], c["drops_observable"], c["drops_observable_O_eq_U"], c["drops_observable_O_ne_U"]) == (4, 2, 1, 2)
      and c["active_classification"] == {"unobservable": [], "insufficient": [21, 23], "detected": [25], "missed": [24]}
      and c["inactive_malicious"] == [22])
c2 = E.ceiling_run(2, Pc, dict(gt, active={21, 23, 24, 25, 26}, malicious={21, 22, 23, 24, 25, 26}), oppc)
check("ceiling: an active node with no MATCH/SILENT opportunity is unobservable", c2["active_classification"]["unobservable"] == [26])
check("ceiling: honest nodes exclude sink and malicious; judged honest 1/24; coverage = TDR x share judged",
      c["honest_nodes"] == 24 and c["honest_judged"] == 1 and c["tdr_pairs"] == 0.5
      and c["share_active_judged"] == 0.5 and c["system_coverage"] == 0.25)

# 11. meta check (E2-2) ---------------------------------------------------------------------------------------------------
md = os.path.join(TMP, "meta_run"); os.makedirs(md)
base = dict({k: (v if isinstance(v, str) else ("0.2" if k == "attacker_fraction" else str(int(v)))) for k, v in E.EXPECTED_META.items()},
            run="7", drop_probability="0.75", num_malicious="20", malicious_nodes="1 2")
def write_meta(dd):
    with open(os.path.join(md, "v1_7_meta.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(list(dd)); w.writerow(list(dd.values()))
write_meta(base)
okm = not raises_stop(E.check_meta, md, 7, 0.75)
write_meta(dict(base, attack_mode="1")); bad1 = raises_stop(E.check_meta, md, 7, 0.75)
write_meta(dict(base, drop_probability="1")); bad2 = raises_stop(E.check_meta, md, 7, 0.75)
write_meta(dict(base, eaqte_xi_env="0.3")); bad3 = raises_stop(E.check_meta, md, 7, 0.75)
check("meta check: frozen settings pass; AttackMode 1, wrong p, or EAQTE_XI set -> stop", okm and bad1 and bad2 and bad3)

# 12. development end-to-end on seed 1 (optional; not E2 data) ---------------------------------------------------------
dp075, dp100 = opt("--dev-p075"), opt("--dev-p100")
if dp075 and dp100:
    roots = {}
    for tag, d in (("p075", dp075), ("p100", dp100)):
        roots[tag] = os.path.join(TMP, "dev", tag); os.makedirs(roots[tag])
        os.symlink(os.path.abspath(os.path.expanduser(d)), os.path.join(roots[tag], "run_1"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    run = lambda *a: subprocess.run([sys.executable, os.path.join(HERE, "e2_evaluate.py"), *a], capture_output=True, text=True, env=env)
    o1, o2 = os.path.join(TMP, "dev_out1"), os.path.join(TMP, "dev_out2")
    r1 = run("--dev", "--seeds", "1", "--p075", roots["p075"], "--p100", roots["p100"], "--out", o1)
    r2 = run("--dev", "--seeds", "1", "--p075", roots["p075"], "--p100", roots["p100"], "--out", o2)
    check("dev seed 1: evaluator runs end-to-end twice", r1.returncode == 0 and r2.returncode == 0, (r1.stderr + r2.stderr)[-400:])
    if r1.returncode == 0 and r2.returncode == 0:
        j1, j2 = json.load(open(os.path.join(o1, "e2_results.json"))), json.load(open(os.path.join(o2, "e2_results.json")))
        j1c, j2c = dict(j1), dict(j2); j1c.pop("created_utc"); j2c.pop("created_utc")
        check("dev seed 1: two evaluations identical apart from created_utc", j1c == j2c)
        check("dev results labelled DEVELOPMENT ONLY", j1["status"].startswith("DEVELOPMENT ONLY"))
        before = E.md5(os.path.join(o1, "e2_results.json"))
        r3 = run("--dev", "--seeds", "1", "--p075", roots["p075"], "--p100", roots["p100"], "--out", o1)
        check("refuses to overwrite existing outputs", r3.returncode != 0 and E.md5(os.path.join(o1, "e2_results.json")) == before)
        r4 = run("--p075", roots["p075"], "--p100", roots["p100"], "--out", os.path.join(TMP, "prod_out"), "--seeds", "1")
        r5 = run("--p075", roots["p075"], "--p100", roots["p100"], "--out", os.path.join(TMP, "prod_out"))
        check("E2 mode rejects --seeds and stops on non-E2 roots without writing",
              r4.returncode != 0 and r5.returncode == 2 and not os.path.exists(os.path.join(TMP, "prod_out")), r5.stderr.strip()[-200:])
        r6 = run("--dev", "--seeds", "1", "--p075", roots["p075"], "--p100", roots["p100"], "--out", os.path.join(HERE, "devx"))
        check("dev output inside analysis/stageE/e2 refused", r6.returncode != 0 and not os.path.exists(os.path.join(HERE, "devx")))

        # independent recomputation from the raw files (plain loops; no evaluator functions)
        def indep(rundir):
            meta = dict(zip(*list(csv.reader(open(os.path.join(rundir, "v1_1_meta.csv"))))))
            mal = {int(x) + 1 for x in meta["malicious_nodes"].split()}
            act = set()
            for ln in open(os.path.join(rundir, "stderr.log"), errors="ignore"):
                if ln.startswith("[DECISION] ") and " act=DROP " in ln:
                    act.add(int(ln.split(" node=")[1].split()[0]))
            acc = {}
            for r in csv.DictReader(open(os.path.join(rundir, "e1_opportunities.csv"))):
                if r["out"] == "OTHER-UP":
                    continue
                a = acc.setdefault((int(r["o"]), int(r["x"])), [0, 0, 0.0])
                a[0] += 1; a[1] += r["out"] == "SILENT"; a[2] += cal["q"][cal["lab"][(int(r["k1"]), int(r["k2"]), int(r["k3"]))]]
            Hs, Ds = [], []
            for (o, x), (n, K, Ev) in acc.items():
                if n < 14 or (x in mal and x not in act):
                    continue
                rr = (K - Ev) / n; b = sum(1 for Lb in cal["L"] if n >= Lb) - 1
                (Ds if x in act else Hs).append((rr, rr > cal["tau"][b]))
            return Hs, Ds, mal, act
        Hs, Ds, mal, act = indep(dp075)
        pt, pop_ = j1["point"], j1["population_p075"]
        auc_ind = auc_exact([r for r, _ in Ds], [1] * len(Ds), [r for r, _ in Hs], [1] * len(Hs)) if Hs and Ds else None
        check("dev seed 1: |H|, |D|, flagged counts and AUC equal an independent recomputation",
              pop_["judged_honest_pairs"] == len(Hs) and pop_["judged_active_malicious_pairs"] == len(Ds)
              and pt["FA_flagged"] == sum(f for _, f in Hs) and pt["TDR_flagged"] == sum(f for _, f in Ds)
              and (pt["AUC"] is None if auc_ind is None else pt["AUC"] == float(auc_ind)),
              f"H {len(Hs)}, D {len(Ds)}")
        cp = j1["ceiling"]["p075"]["per_run"][0]
        check("dev seed 1: ceiling malicious/active sets equal the independent labels",
              set(cp["malicious"]) == mal and set(cp["active_malicious"]) == act)
        check("dev seed 1: bootstrap B = 10,000 recorded with PCG64 12345 and node universe",
              j1["bootstrap"]["B"] == 10000 and j1["bootstrap"]["seed"] == 12345 and "1" in j1["bootstrap"]["node_universe"])
else:
    print("  (development end-to-end check skipped: --dev-p075/--dev-p100 not given)")

shutil.rmtree(TMP)
print(f"\n{'ALL CHECKS PASSED' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
sys.exit(1 if FAILS else 0)
