#!/usr/bin/env python3
"""Stage E E1 calibration — REVISION 4 (frozen spec ../README.md §7 and §12 V6; commit 8a0ff2f).
Reads ONLY the observer-side opportunity files of the clean calibration runs (seeds 12-21, every node honest).

- Statistic (§7): r_w = (K_w - E_w)/S_w with K_w = sum w*y, E_w = sum w*q, S_w = sum w over MATCH and SILENT
  (OTHER-UP excluded); n_eff = (sum w)^2/sum w^2 when S_w > 0 and n_eff = 0 when S_w = 0. Arm A (w = 1):
  r = (K - E)/n. E1 calibrates Arm A only.
- Steps 1-2: revision-2 merge rule, q_s, q_bar, n_ref (imported unchanged).
- Step 3: revision-3 bin construction (imported unchanged); raw nearest-rank rho_b on r; weighted
  pool-adjacent-violators smoothing, non-increasing in n, exactly as frozen; step-function assignment.
- Step 4 (Arm A only): exact per-pair attacked flag probability pi_j(tau) (Binomial(m_j, 0.75) tail via lnGamma
  terms summed in ascending f); power_b; one-sided 95% percentile-bootstrap lower bound (B_cal = 1,000,
  NumPy PCG64 seed 12345, draw order as frozen); n_min by the P-suffix rule, else undefined (G1 fails).
- V6: leave-one-seed-out recalibration (development validation). V6-A false-alarm transfer over all folds
  (held-out pairs with n >= fold n_ref); V6-B power feasibility in every fold and the full calibration.

usage: calibrate_rev4.py <E1 run root> <run> [<run> ...] [--out JSON] [--report TXT]
"""
import sys, os, json, math, hashlib, subprocess, datetime, collections as C
import numpy as np
from calibrate import load                                   # revision-2 opportunity loader, unchanged
from calibrate_rev3 import step12, build_bins, bin_of        # revision-2 steps 1-2 and revision-3 bins, unchanged

HERE = os.path.dirname(os.path.abspath(__file__))
M_BIN, P_MIN, POWER, FA_NOMINAL = 200, 0.75, 0.80, 0.05
B_CAL, SEED, B_BOOT = 1000, 12345, 10000
LCB_RANK = math.ceil(0.05 * B_CAL)                           # 50th smallest
CAL_SEEDS = set(range(12, 22))
LN_P, LN_Q = math.log(P_MIN), math.log(1.0 - P_MIN)


# ---------------------------------------------------------------- statistic (§7) ----------
def weighted_pair(entries):
    """entries: [(y, q, w)] for one pair's MATCH/SILENT opportunities in stored order.
    Returns K_w, E_w, S_w, n_eff, r_w (r_w None when S_w = 0); n_eff = 0 when S_w = 0."""
    K_w = E_w = S_w = W2 = 0.0
    for y, q, w in entries:
        K_w += w * y; E_w += w * q; S_w += w; W2 += w * w
    if S_w == 0.0:
        return K_w, E_w, S_w, 0.0, None
    return K_w, E_w, S_w, S_w * S_w / W2, (K_w - E_w) / S_w


def judged(n_eff, n_min):
    """A pair is judged iff n_min is defined and n_eff >= n_min (n_eff = 0 when S_w = 0, so never judged then)."""
    return n_min is not None and n_eff >= n_min


def arm_a_pairs(rows, lab, q):
    """Arm A (w = 1). Per pair (run, o, x), stored opportunity order: n, K, m = n - K, E = sum q, V, r, Z."""
    acc = {}
    for run, o, x, cell, y in rows:
        qs = q[lab[cell]]
        a = acc.setdefault((run, o, x), [0, 0, 0.0, 0.0])
        a[0] += 1; a[1] += y; a[2] += qs; a[3] += qs * (1 - qs)
    out = {}
    for k, (n, K, E, V) in acc.items():
        out[k] = {"n": n, "K": K, "m": n - K, "E": E, "r": (K - E) / n, "Z": (K - E) / math.sqrt(V)}
    return out


# ---------------------------------------------------------------- step 3 ------------------
def nearest_rank_95(values):
    v = sorted(values)
    return v[math.ceil(0.95 * len(v)) - 1]


def pava_nonincreasing(rho, weights):
    """Frozen weighted pool-adjacent-violators procedure, non-increasing in bin order. Returns tau per bin."""
    stack = []                                                # [value, weight, first, last]
    for b, (v, w) in enumerate(zip(rho, weights)):
        stack.append([float(v), float(w), b, b])
        while len(stack) >= 2 and stack[-2][0] < stack[-1][0]:
            (v1, w1, f1, l1), (v2, w2, f2, l2) = stack[-2], stack[-1]
            stack[-2:] = [[(w1 * v1 + w2 * v2) / (w1 + w2), w1 + w2, f1, l2]]
    tau = [None] * len(rho)
    for v, w, f, l in stack:
        for b in range(f, l + 1):
            tau[b] = v
    return tau


# ---------------------------------------------------------------- step 4 ------------------
_TAIL = {}


def tail_table(m):
    """tail[f] = sum_{g=f}^{m} exp(lnG(m+1) - lnG(g+1) - lnG(m-g+1) + g ln0.75 + (m-g) ln0.25), summed in
    ascending g; f = 0..m (index m+1 unused: f* > m gives pi = 0 by definition)."""
    if m not in _TAIL:
        lm = math.lgamma(m + 1)
        terms = [math.exp(lm - math.lgamma(g + 1) - math.lgamma(m - g + 1) + g * LN_P + (m - g) * LN_Q) for g in range(m + 1)]
        tl = []
        for f in range(m + 1):
            s = 0.0
            for g in range(f, m + 1):                     # ascending f, as frozen
                s += terms[g]
            tl.append(s)
        _TAIL[m] = tl
    return _TAIL[m]


def pi_attacked(n, K, m, E, tau):
    """Exact Arm-A attacked flag probability for one pair (frozen §7 step 4)."""
    x = n * tau + E - K
    fstar = math.floor(x) + 1
    if fstar <= 0:
        return 1.0
    if fstar > m:
        return 0.0
    return tail_table(m)[fstar]


class BinArrays:
    """Vectorised view of one bin's reference pairs (sorted by (seed, O, X)) for exact power."""
    def __init__(self, P, keys):
        self.keys = keys
        self.n = np.array([P[k]["n"] for k in keys], dtype=np.float64)
        self.K = np.array([P[k]["K"] for k in keys], dtype=np.float64)
        self.m = np.array([P[k]["m"] for k in keys], dtype=np.int64)
        self.E = np.array([P[k]["E"] for k in keys], dtype=np.float64)
        self.r = np.array([P[k]["r"] for k in keys], dtype=np.float64)
        mx = int(self.m.max())
        self.T = np.zeros((mx + 1, mx + 2))
        for mm in set(int(v) for v in self.m):
            t = tail_table(mm)
            self.T[mm, :mm + 1] = t

    def pi(self, tau, idx=None):
        n, K, m, E = (self.n, self.K, self.m, self.E) if idx is None else (self.n[idx], self.K[idx], self.m[idx], self.E[idx])
        x = n * tau + E - K
        fstar = np.floor(x).astype(np.int64) + 1
        inside = (fstar > 0) & (fstar <= m)
        out = np.where(fstar <= 0, 1.0, 0.0)
        out[inside] = self.T[m[inside], fstar[inside]]
        return out


def calibrate_rev4(rows, with_bootstrap=True):
    res, lab, q, qbar, n_ref = step12(rows)
    if "stop" in res:
        return res, None
    P = arm_a_pairs(rows, lab, q)
    ref = {k: p for k, p in P.items() if p["n"] >= n_ref}
    L, sizes = build_bins([p["n"] for p in ref.values()], n_ref)
    Kb = len(L)
    members = [[] for _ in range(Kb)]
    for k in sorted(ref):                                    # (seed, O, X) order
        members[bin_of(ref[k]["n"], L)].append(k)
    assert [len(mm) for mm in members] == sizes
    bins = [BinArrays(ref, mm) for mm in members]
    rho = [nearest_rank_95(ba.r.tolist()) for ba in bins]
    tau = pava_nonincreasing(rho, sizes)
    power = [float(np.mean(bins[b].pi(tau[b]))) for b in range(Kb)]
    n_max = max(p["n"] for p in ref.values())
    lcb, boot = None, None
    if with_bootstrap:
        rng = np.random.Generator(np.random.PCG64(SEED))
        boot = np.empty((B_CAL, Kb))
        for k in range(B_CAL):
            idxs = [rng.integers(0, sizes[b], sizes[b]) for b in range(Kb)]      # replicate k, bins in order
            rho_s = [nearest_rank_95(bins[b].r[idxs[b]].tolist()) for b in range(Kb)]
            tau_s = pava_nonincreasing(rho_s, sizes)
            for b in range(Kb):
                boot[k, b] = float(np.mean(bins[b].pi(tau_s[b], idxs[b])))
        lcb = [float(np.sort(boot[:, b])[LCB_RANK - 1]) for b in range(Kb)]
    n_min = None
    if lcb is not None:
        for b in range(Kb):                                 # P-suffix: smallest b with every b' >= b qualifying
            if all(lcb[bp] >= POWER for bp in range(b, Kb)):
                n_min = L[b]
                break
    per_bin = []
    for b in range(Kb):
        rb = bins[b].r
        zb = np.array([ref[k]["Z"] for k in members[b]])
        per_bin.append({"bin": b + 1, "L": L[b], "U": L[b + 1] if b + 1 < Kb else None, "N": sizes[b],
                        "n_max_in_bin": int(bins[b].n.max()), "rho": rho[b], "tau": tau[b],
                        "fa_at_rho": float((rb > rho[b]).mean()), "fa_at_tau": float((rb > tau[b]).mean()),
                        "power": power[b], "lcb": None if lcb is None else lcb[b],
                        "var_r": float(rb.var(ddof=1)), "var_Z_descriptive": float(zb.var(ddof=1))})
    jk = [k for k in ref if judged(ref[k]["n"], n_min)]
    fl = sum(ref[k]["r"] > tau[bin_of(ref[k]["n"], L)] for k in jk)
    zall = np.array([p["Z"] for p in ref.values()])
    res.update({"pairs_total": len(P), "pairs_ge_n_ref": len(ref), "M": M_BIN, "edges_L": L, "bin_sizes": sizes,
                "rho_b": rho, "tau_A_b": tau, "power_b": power, "lcb_b": lcb, "n_max": n_max, "n_min": n_min,
                "per_bin": per_bin,
                "calibration_fa_judged": {"judged": len(jk), "flagged": int(fl), "fa": fl / len(jk) if jk else None},
                "overdispersion_Z_descriptive": {"N": int(len(zall)), "var_Z": float(zall.var(ddof=1))}})
    model = {"lab": lab, "q": q, "n_ref": n_ref, "L": L, "tau": tau, "n_min": n_min, "n_max": n_max}
    return res, model


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main():
    args = sys.argv[1:]
    out_json = os.path.join(HERE, "e1_calibration_rev4.json"); out_rep = os.path.join(HERE, "e1_calibration_report_rev4.txt")
    if "--out" in args:
        i = args.index("--out"); out_json = args[i + 1]; del args[i:i + 2]
    if "--report" in args:
        i = args.index("--report"); out_rep = args[i + 1]; del args[i:i + 2]
    root, runs = args[0], [int(a) for a in args[1:]]
    if not set(runs) <= CAL_SEEDS:
        raise SystemExit("revision 4 calibrates on clean seeds 12-21 only")
    for p in (out_json, out_rep):
        if os.path.exists(p):
            raise SystemExit(f"{p} exists; refusing to overwrite a frozen output")
    rows = load(root, runs)
    res, model = calibrate_rev4(rows)
    W = []; w = W.append
    w("Stage E E1 calibration — REVISION 4 (frozen spec ../README.md §7, commit 8a0ff2f), Arm A only")
    w("Re-evaluation of the existing E1 outputs (clean seeds " + ",".join(map(str, runs)) + "); no simulation rerun, no attacker data.")
    w(f"MATCH+SILENT opportunities: {len(rows)}; SILENT {sum(r[-1] for r in rows)}")
    if "stop" in res:
        w("STOP: " + res["stop"]); open(out_rep, "w").write("\n".join(W) + "\n"); print("\n".join(W)); return
    w(f"Steps 1-2 (unchanged): q_bar {res['qbar']:.6f}; n_ref {res['n_ref']}; reference pairs {res['pairs_ge_n_ref']} of {res['pairs_total']}")
    w("Step 3 (rate scale r = (K - E)/n; nearest-rank rho_b; PAVA non-increasing tau_A,b) and step 4 (exact Arm-A power;")
    w(f"bootstrap LCB = {LCB_RANK}th smallest of B_cal = {B_CAL}, PCG64 seed {SEED}):")
    w("   bin  interval        N   n max     rho_b      tau_A,b   FA@rho  FA@tau   power_b   LCB_b    var(r)")
    for pb in res["per_bin"]:
        iv = f"[{pb['L']},{pb['U'] if pb['U'] is not None else 'inf'})"
        w(f"   {pb['bin']:3d}  {iv:12s} {pb['N']:5d}  {pb['n_max_in_bin']:5d}  {pb['rho']:9.5f}  {pb['tau']:9.5f}  {pb['fa_at_rho']:.4f}  {pb['fa_at_tau']:.4f}   {pb['power']:.4f}   {pb['lcb']:.4f}   {pb['var_r']:.4f}")
    w(f"   n_max (verified power range limit) = {res['n_max']}")
    w(f"   P-suffix n_min = {res['n_min'] if res['n_min'] is not None else 'UNDEFINED -> G1 FAILS (option i; no adjustment)'}")
    cf = res["calibration_fa_judged"]
    w(f"   in-sample FA among pairs with n >= n_min: {cf['flagged']}/{cf['judged']}" + (f" = {cf['fa']:.4f}" if cf["fa"] is not None else " (n_min undefined)"))
    w(f"   Z over-dispersion (descriptive only): var(Z) {res['overdispersion_Z_descriptive']['var_Z']:.2f}")
    w("   The power guarantee, when n_min is defined, is an Arm-A claim only; no calibrated power is claimed for Arms B/C.")
    w("   Revision-3 figures ~0.41 / ~0.60 are revision-3 diagnostics only, not a ceiling for this statistic.")
    # ---------------- V6 ----------------
    w("")
    w("V6 leave-one-seed-out — RECALIBRATION / DEVELOPMENT VALIDATION (independent FA assessment = G2b on sealed seeds 2-11)")
    clusters, folds, all_defined = {}, [], res["n_min"] is not None
    above_nmax = 0
    for k in runs:
        tr = [r for r in rows if r[0] != k]; te = [r for r in rows if r[0] == k]
        rk, mk = calibrate_rev4(tr)
        if "stop" in rk:
            all_defined = False; folds.append({"seed": k, "status": rk["stop"]}); w(f"   seed {k}: STOP {rk['stop']}"); continue
        Pk = arm_a_pairs(te, mk["lab"], mk["q"])
        perx = C.defaultdict(lambda: [0, 0]); perb = C.defaultdict(lambda: [0, 0])
        for (run, o, x), p in Pk.items():
            if p["n"] >= mk["n_ref"]:                      # V6-A population: independent of n_min
                b = bin_of(p["n"], mk["L"]); f = int(p["r"] > mk["tau"][b])
                perx[x][0] += 1; perx[x][1] += f; perb[b + 1][0] += 1; perb[b + 1][1] += f
                above_nmax += p["n"] > mk["n_max"]
        clusters[k] = np.array(list(perx.values()), float).reshape(-1, 2)
        j, fl = (clusters[k].sum(0) if len(clusters[k]) else (0, 0))
        defined = mk["n_min"] is not None
        all_defined &= defined
        folds.append({"seed": k, "n_ref": rk["n_ref"], "edges_L": mk["L"], "tau": mk["tau"], "lcb": rk["lcb_b"],
                      "n_min": mk["n_min"], "n_max": mk["n_max"], "v6a_pairs": int(j), "v6a_flagged": int(fl),
                      "per_bin": {str(b): v for b, v in sorted(perb.items())}})
        w(f"   seed {k}: n_ref {rk['n_ref']}, bins {len(mk['L'])}, n_min {mk['n_min'] if defined else 'UNDEFINED'}; "
          f"V6-A pairs {int(j)}, flagged {int(fl)}, FA {fl / j if j else float('nan'):.4f}; fold LCB "
          + "[" + ", ".join(f"{v:.3f}" for v in rk["lcb_b"]) + "]")
    J = sum(c[:, 0].sum() for c in clusters.values()); F = sum(c[:, 1].sum() for c in clusters.values())
    rngb = np.random.Generator(np.random.PCG64(SEED)); keys = sorted(clusters); boot = np.empty(B_BOOT)
    for i in range(B_BOOT):
        jj = ff = 0.0
        for s in rngb.integers(0, len(keys), len(keys)):
            c = clusters[keys[s]]
            if len(c):
                pick = c[rngb.integers(0, len(c), len(c))]; jj += pick[:, 0].sum(); ff += pick[:, 1].sum()
        boot[i] = ff / jj if jj else np.nan
    lower = float(np.nanpercentile(boot, 5))
    v6a = bool(J > 0 and lower <= FA_NOMINAL and len(clusters) == len(runs))
    v6b = bool(all_defined)
    w(f"   V6-A false-alarm transfer (all {len(runs)} folds, held-out pairs n >= fold n_ref): pooled FA {int(F)}/{int(J)} = {F / J:.4f}; "
      f"one-sided 95% lower bound (cluster bootstrap seeds -> nodes, B = {B_BOOT}, PCG64 seed {SEED}) = {lower:.4f}: {'PASS' if v6a else 'FAIL'}")
    w(f"      held-out pairs above their fold's n_max (judged, outside the verified power range): {above_nmax}")
    w(f"   V6-B power feasibility (n_min defined in every fold and in the full calibration): {'PASS' if v6b else 'FAIL'}")
    w(f"   V6 = V6-A and V6-B: {'PASS' if (v6a and v6b) else 'FAIL'}")
    git = lambda *a: subprocess.run(["git", *a], cwd=HERE, capture_output=True, text=True).stdout.strip()
    frozen = {
        "spec": "analysis/stageE/README.md, frozen revision 4 (commit 8a0ff2f); project docs synced at c2a5077",
        "status": "E1 re-evaluation of existing outputs, Arm A only; V6 is development/recalibration validation; independent FA = G2b on sealed seeds 2-11",
        "created_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "calibration_seeds": runs, "p_min": P_MIN, "power_target": POWER, "fa_nominal": FA_NOMINAL,
        "bootstrap": {"B_cal": B_CAL, "generator": "numpy.random.PCG64", "seed": SEED, "lcb_rank": LCB_RANK,
                      "draw_order": "replicates 1..B_cal; within each, bins 1..K: integers(0, N_b, N_b) over the bin's reference pairs sorted by (seed, O, X)"},
        **{k: res[k] for k in ("cell_counts", "merge_map", "undersized_after_merge", "strata", "qbar", "n_ref", "pairs_total",
                               "pairs_ge_n_ref", "M", "edges_L", "bin_sizes", "rho_b", "tau_A_b", "power_b", "lcb_b", "n_max",
                               "n_min", "per_bin", "calibration_fa_judged", "overdispersion_Z_descriptive")},
        "n_min_status": "defined" if res["n_min"] is not None else "undefined -> G1 fails (option i; no adjustment)",
        "power_claim_scope": "Arm A only; no calibrated power claim for Arms B or C (D4-6)",
        "V6": {"label": "development/recalibration validation", "folds": folds,
               "V6A": {"pooled_pairs": int(J), "pooled_flagged": int(F), "pooled_fa": F / J if J else None, "lower95_one_sided": lower,
                       "held_out_above_fold_n_max": int(above_nmax),
                       "bootstrap": {"B": B_BOOT, "generator": "numpy.random.PCG64", "seed": SEED, "clusters": "seeds then X nodes"},
                       "pass": v6a},
               "V6B": {"all_folds_and_full_defined": v6b, "pass": v6b}, "pass": bool(v6a and v6b)},
        "code": {"parent_commit": git("rev-parse", "HEAD"), "submodule_commit": git("-C", "../../../src/aqua-sim-ng", "rev-parse", "HEAD"),
                 "scripts_md5": {f: md5(os.path.join(HERE, f)) for f in ("geom.py", "observer.py", "calibrate.py", "calibrate_rev3.py", "calibrate_rev4.py")}},
        "inputs_md5": {str(r): {f: md5(f"{root}/run_{r}/{f}") for f in ("stderr.log", f"v1_{r}.tr", "e1_opportunities.csv")} for r in runs},
        "historical_md5_unchanged": {f: md5(os.path.join(HERE, f)) for f in ("e1_calibration.json", "e1_calibration_rev3.json")},
    }
    with open(out_json, "w") as fh:
        json.dump(frozen, fh, indent=1)
    w("")
    w(f"Frozen revision-4 calibration: {os.path.relpath(out_json, os.path.join(HERE, '..', '..', '..'))}  md5 {md5(out_json)}")
    open(out_rep, "w").write("\n".join(W) + "\n")
    print("\n".join(W))


if __name__ == "__main__":
    main()
