#!/usr/bin/env python3
"""Stage E E1 calibration — REVISION 3 (frozen spec, ../README.md §7 steps 1-6 and §12 V6; commit e9ddf04).
Reads ONLY the observer-side opportunity files of the clean calibration runs (seeds 12-21, every node honest).
Steps 1-2 (merge rule, q_s, q_bar, n_ref) are the revision-2 functions imported unchanged from calibrate.py.
Step 3: deterministic n-bins (M = 200, equal n never split, undersized last bin merged into the previous one,
L1 = n_ref, half-open intervals) and per-bin nearest-rank thresholds tau_A,b at the nominal 0.05 level.
Step 4: power per bin by thinning (one NumPy PCG64 generator, seed 12345, R = 10,000 per bin, bins ascending);
n_min = lower edge of the smallest bin with power >= 0.80, otherwise undefined (G1 fails; no adjustment).
V6: leave-one-seed-out recalibration (development validation), cluster bootstrap B = 10,000, PCG64 seed 12345.

usage: calibrate_rev3.py <E1 run root> <run> [<run> ...]
"""
import sys, os, json, math, bisect, hashlib, subprocess, datetime, collections as C
import numpy as np
from calibrate import load, merge_map, name, CELLS          # revision-2 steps 1-2, unchanged

HERE = os.path.dirname(os.path.abspath(__file__))
M_BIN, P_MIN, POWER, FA_NOMINAL = 200, 0.75, 0.80, 0.05
R_PWR, SEED, B_BOOT = 10000, 12345, 10000
CAL_SEEDS = set(range(12, 22))


def step12(rows):
    """Revision-2 steps 1-2: merge map, q_s, q_bar, n_ref (same formulas as calibrate.calibrate)."""
    cnt = C.Counter(cell for *_, cell, y in rows)
    lab, left = merge_map(cnt)
    tot, sil = C.Counter(), C.Counter()
    for *_, cell, y in rows:
        tot[lab[cell]] += 1; sil[lab[cell]] += y
    q = {l: sil[l] / tot[l] for l in tot}
    out = {"cell_counts": {name(c): cnt[c] for c in CELLS}, "merge_map": {name(c): name(lab[c]) for c in CELLS},
           "undersized_after_merge": left,
           "strata": {name(l): {"n": tot[l], "silent": sil[l], "q": q[l]} for l in sorted(tot, key=name)}}
    if any(v in (0.0, 1.0) for v in q.values()):
        out["stop"] = "a merged stratum has q_s in {0, 1}"
        return out, lab, q, None, None
    qbar = sum(sil.values()) / sum(tot.values())
    n_ref = math.ceil(5 / min(qbar, 1 - qbar))
    out.update({"qbar": qbar, "n_ref": n_ref})
    return out, lab, q, qbar, n_ref


def pairs_of(rows, lab, q):
    """Per pair (run, o, x), in stored opportunity order: n, K (silent), E = sum q, V = sum q(1-q), Z,
    and the MATCH count (thinning candidates)."""
    acc = {}
    for run, o, x, cell, y in rows:
        qs = q[lab[cell]]
        a = acc.setdefault((run, o, x), [0, 0, 0.0, 0.0, 0])
        a[0] += 1; a[1] += y; a[2] += qs; a[3] += qs * (1 - qs); a[4] += 1 - y
    return {k: {"n": n, "K": K, "E": E, "V": V, "Z": (K - E) / math.sqrt(V), "match": m}
            for k, (n, K, E, V, m) in acc.items()}


def build_bins(ns, n_ref):
    """Deterministic bin construction on the reference-set n values (all >= n_ref). Returns edges L (L1 = n_ref)."""
    groups = sorted(C.Counter(ns).items())               # (v_j, c_j), v ascending
    bins, cur, cnt = [], [], 0
    for v, c in groups:
        cur.append(v); cnt += c                            # whole equal-n group, never split
        if cnt >= M_BIN:
            bins.append((cur, cnt)); cur, cnt = [], 0
    if cur:
        bins.append((cur, cnt))
    if len(bins) > 1 and bins[-1][1] < M_BIN:              # undersized final bin -> merge into preceding bin
        (pv, pc), (lv, lc) = bins[-2], bins[-1]
        bins[-2:] = [(pv + lv, pc + lc)]
    L = [n_ref] + [b[0][0] for b in bins[1:]]
    return L, [b[1] for b in bins]


def bin_of(n, L):
    """Index b with L[b] <= n < L[b+1] (last bin open-ended); None if n < L[0] = n_ref."""
    return None if n < L[0] else bisect.bisect_right(L, n) - 1


def calibrate_rev3(rows):
    res, lab, q, qbar, n_ref = step12(rows)
    if "stop" in res:
        return res, lab, q, None
    P = pairs_of(rows, lab, q)
    ref = {k: p for k, p in P.items() if p["n"] >= n_ref}
    L, sizes = build_bins([p["n"] for p in ref.values()], n_ref)
    K = len(L)
    members = [[] for _ in range(K)]
    for k in sorted(ref):                                   # pairs ordered by (seed, O, X)
        members[bin_of(ref[k]["n"], L)].append(k)
    assert [len(m) for m in members] == sizes
    tau = []
    for b in range(K):
        z = sorted(ref[k]["Z"] for k in members[b])
        tau.append(z[math.ceil(0.95 * len(z)) - 1])         # nearest rank, nominal 0.05
    # step 4: power by thinning, one generator, bins ascending
    rng = np.random.Generator(np.random.PCG64(SEED))
    power = []
    for b in range(K):
        mem = members[b]
        idx = rng.integers(0, len(mem), R_PWR)
        Kp = np.array([P[mem[i]]["K"] for i in idx], float)
        Ep = np.array([P[mem[i]]["E"] for i in idx]); Vp = np.array([P[mem[i]]["V"] for i in idx])
        mt = np.array([P[mem[i]]["match"] for i in idx])
        u = rng.random(int(mt.sum()))                       # replicate order, stored MATCH order within each pair
        rep = np.repeat(np.arange(R_PWR), mt)               # replicate id of each drawn uniform
        flips = np.bincount(rep, weights=(u < P_MIN).astype(float), minlength=R_PWR)
        z = (Kp + flips - Ep) / np.sqrt(Vp)
        power.append(float((z > tau[b]).mean()))
    qual = [b for b in range(K) if power[b] >= POWER]
    n_min = L[qual[0]] if qual else None
    # step 5 reports (never tuned)
    zall = np.array([p["Z"] for p in ref.values()])
    per_bin = []
    for b in range(K):
        zb = np.array([ref[k]["Z"] for k in members[b]])
        per_bin.append({"bin": b + 1, "L": L[b], "U": L[b + 1] if b + 1 < K else None, "N": sizes[b],
                        "n_max_in_bin": max(ref[k]["n"] for k in members[b]), "tau": tau[b],
                        "fa_in_sample": float((zb > tau[b]).mean()), "flagged": int((zb > tau[b]).sum()),
                        "power": power[b], "var_Z": float(zb.var(ddof=1)), "mean_Z2": float(np.mean(zb ** 2))})
    judged = [k for k in ref if n_min is not None and ref[k]["n"] >= n_min]
    fl = sum(ref[k]["Z"] > tau[bin_of(ref[k]["n"], L)] for k in judged)
    res.update({"pairs_total": len(P), "pairs_ge_n_ref": len(ref), "M": M_BIN, "edges_L": L, "bin_sizes": sizes,
                "tau_A_b": tau, "power_b": power, "any_bin_reaches_0.80": bool(qual), "n_min": n_min,
                "per_bin": per_bin,
                "calibration_fa_judged": {"judged": len(judged), "flagged": int(fl), "fa": fl / len(judged) if judged else None},
                "overdispersion_all": {"N": int(len(zall)), "var_Z": float(zall.var(ddof=1)), "mean_Z2": float(np.mean(zall ** 2))}})
    model = {"lab": lab, "q": q, "L": L, "tau": tau, "n_min": n_min}
    return res, lab, q, model


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main():
    root, runs = sys.argv[1], [int(a) for a in sys.argv[2:]]
    if not set(runs) <= CAL_SEEDS:
        raise SystemExit("revision 3 calibrates on clean seeds 12-21 only")
    g = np.random.Generator(np.random.PCG64(1)); h = np.random.Generator(np.random.PCG64(1))
    assert np.array_equal(g.random(7), np.array([h.random() for _ in range(7)])), "block draw != successive draws"
    rows = load(root, runs)
    res, lab, q, model = calibrate_rev3(rows)
    out = []; W = out.append
    W("Stage E E1 calibration — REVISION 3 (frozen spec ../README.md §7, commit e9ddf04)")
    W("Re-evaluation of the existing E1 outputs (clean seeds " + ",".join(map(str, runs)) + "); no simulation rerun, no attacker data.")
    W(f"MATCH+SILENT opportunities: {len(rows)}; SILENT {sum(r[-1] for r in rows)}")
    W("")
    W("Steps 1-2 (revision-2 rules, unchanged): merged strata q_s")
    for l, v in res["strata"].items():
        W(f"   {l:28s} n {v['n']:7d}  q_s {v['q']:.6f}")
    if "stop" in res:
        W("STOP: " + res["stop"]); open(os.path.join(HERE, "e1_calibration_report_rev3.txt"), "w").write("\n".join(out) + "\n"); print("\n".join(out)); return
    W(f"   q_bar {res['qbar']:.6f}; n_ref = ceil(5 / min(q_bar, 1 - q_bar)) = {res['n_ref']}")
    W("")
    W(f"Step 3: bins (M = {M_BIN}; equal n never split; half-open [L_b, L_b+1)); reference pairs {res['pairs_ge_n_ref']} of {res['pairs_total']}")
    W("   Step 4: power by thinning (PCG64 seed 12345, R = 10,000 per bin, p_min 0.75)")
    W("   bin  interval        N   n max   tau_A,b   in-sample FA (flagged)   power_b   var(Z)")
    for pb in res["per_bin"]:
        iv = f"[{pb['L']},{pb['U'] if pb['U'] is not None else 'inf'})"
        W(f"   {pb['bin']:3d}  {iv:12s} {pb['N']:5d}  {pb['n_max_in_bin']:5d}  {pb['tau']:8.4f}   {pb['fa_in_sample']:.4f} ({pb['flagged']:3d})            {pb['power']:.4f}   {pb['var_Z']:6.2f}")
    W(f"   any bin with power >= {POWER}: {res['any_bin_reaches_0.80']}")
    W(f"   n_min = {res['n_min'] if res['n_min'] is not None else 'UNDEFINED -> G1 FAILS (no adjustment; 0.80 and p_min unchanged)'}")
    W("   The thresholds are calibrated empirically within each bin at the nominal 0.05 level; nearest rank does not")
    W("   guarantee an exact 0.05 false-alarm rate.")
    cf = res["calibration_fa_judged"]
    W(f"Step 5: in-sample calibration FA among pairs with n >= n_min: {cf['flagged']}/{cf['judged']}" + (f" = {cf['fa']:.4f}" if cf["fa"] is not None else " (n_min undefined)"))
    W(f"        over-dispersion of Z, all reference pairs: var {res['overdispersion_all']['var_Z']:.2f}, mean Z^2 {res['overdispersion_all']['mean_Z2']:.2f}")
    W("        model-based power ceiling ~0.41 (Beta(0.90, 1.48), strata only): DIAGNOSTIC ONLY, not used for G1")
    # ---------- V6 ----------
    W("")
    W("V6 leave-one-seed-out — RECALIBRATION / DEVELOPMENT VALIDATION (the revision-3 design was informed by these")
    W("seeds; the independent false-alarm assessment is G2b on held-out seeds 2-11):")
    clusters, folds, v6_eval = {}, [], True
    for k in runs:
        tr = [r for r in rows if r[0] != k]; te = [r for r in rows if r[0] == k]
        rk, labk, qk, mk = calibrate_rev3(tr)
        if "stop" in rk or mk["n_min"] is None:
            v6_eval = False
            folds.append({"seed": k, "n_ref": rk.get("n_ref"), "n_min": None, "status": rk.get("stop", "n_min undefined")})
            W(f"   seed {k}: fold n_ref {rk.get('n_ref')}, bins {len(rk.get('edges_L', []))}, n_min UNDEFINED ({rk.get('stop', 'no bin reaches 0.80')}); "
              f"fold powers {[round(p, 3) for p in rk.get('power_b', [])]}")
            continue
        Pk = pairs_of(te, labk, qk)
        perx = C.defaultdict(lambda: [0, 0]); perb = C.defaultdict(lambda: [0, 0])
        for (run, o, x), p in Pk.items():
            if p["n"] >= mk["n_min"]:
                b = bin_of(p["n"], mk["L"]); f = int(p["Z"] > mk["tau"][b])
                perx[x][0] += 1; perx[x][1] += f; perb[b + 1][0] += 1; perb[b + 1][1] += f
        clusters[k] = np.array(list(perx.values()), float).reshape(-1, 2)
        j, f = (clusters[k].sum(0) if len(clusters[k]) else (0, 0))
        folds.append({"seed": k, "n_ref": rk["n_ref"], "edges_L": mk["L"], "tau": mk["tau"], "n_min": mk["n_min"],
                      "judged": int(j), "flagged": int(f), "per_bin": {str(b): v for b, v in sorted(perb.items())}})
        W(f"   seed {k}: n_ref {rk['n_ref']}, bins {len(mk['L'])}, n_min {mk['n_min']}; judged {int(j)}, flagged {int(f)}, "
          f"FA {f / j if j else float('nan'):.4f}; per bin (judged/flagged): "
          + ", ".join(f"b{b}:{v[0]}/{v[1]}" for b, v in sorted(perb.items())))
    J = sum(c[:, 0].sum() for c in clusters.values()); F = sum(c[:, 1].sum() for c in clusters.values())
    lower, v6_pass = None, False
    if clusters:
        rngb = np.random.Generator(np.random.PCG64(SEED)); keys = sorted(clusters); boot = np.empty(B_BOOT)
        for i in range(B_BOOT):
            jj = ff = 0.0
            for s in rngb.integers(0, len(keys), len(keys)):
                c = clusters[keys[s]]
                if len(c):
                    pick = c[rngb.integers(0, len(c), len(c))]; jj += pick[:, 0].sum(); ff += pick[:, 1].sum()
            boot[i] = ff / jj if jj else np.nan
        lower = float(np.nanpercentile(boot, 5))
        v6_pass = v6_eval and J > 0 and lower <= FA_NOMINAL
    W(f"   pooled out-of-seed FA {int(F)}/{int(J)}" + (f" = {F / J:.4f}" if J else "") +
      (f"; one-sided 95% lower bound (cluster bootstrap seeds -> nodes, B = {B_BOOT}, PCG64 seed {SEED}) = {lower:.4f}" if lower is not None else ""))
    W(f"   all folds evaluable (n_min defined in every fold): {v6_eval}")
    W(f"   V6 (pooled FA not significantly above {FA_NOMINAL}): {'PASS' if v6_pass else 'FAIL'}")
    git = lambda *a: subprocess.run(["git", *a], cwd=HERE, capture_output=True, text=True).stdout.strip()
    frozen = {
        "spec": "analysis/stageE/README.md, frozen revision 3 (parent commit e9ddf04)",
        "status": "re-evaluation of existing E1 outputs; V6 is development/recalibration validation; independent FA = G2b on seeds 2-11",
        "created_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "calibration_seeds": runs, "p_min": P_MIN, "power_target": POWER, "fa_nominal": FA_NOMINAL,
        "rng": {"generator": "numpy.random.PCG64", "seed": SEED, "R_per_bin": R_PWR,
                "draw_order": "bins ascending; per bin: integers(0, N_b, R) over pairs sorted by (seed, O, X), then one uniform "
                              "per MATCH opportunity in replicate order and stored opportunity order; MATCH->SILENT if u < p_min"},
        **{k: res[k] for k in ("cell_counts", "merge_map", "undersized_after_merge", "strata", "qbar", "n_ref", "pairs_total",
                               "pairs_ge_n_ref", "M", "edges_L", "bin_sizes", "tau_A_b", "power_b", "any_bin_reaches_0.80",
                               "n_min", "per_bin", "calibration_fa_judged", "overdispersion_all")},
        "n_min_status": "defined" if res["n_min"] is not None else "undefined -> G1 fails (option i; no adjustment)",
        "V6": {"label": "development/recalibration validation", "folds": folds, "all_folds_evaluable": v6_eval,
               "pooled_judged": int(J), "pooled_flagged": int(F), "pooled_fa": (F / J) if J else None, "lower95_one_sided": lower,
               "bootstrap": {"B": B_BOOT, "generator": "numpy.random.PCG64", "seed": SEED, "clusters": "seeds then X nodes"},
               "pass": v6_pass},
        "code": {"parent_commit": git("rev-parse", "HEAD"), "submodule_commit": git("-C", "../../../src/aqua-sim-ng", "rev-parse", "HEAD"),
                 "scripts_md5": {f: md5(os.path.join(HERE, f)) for f in ("geom.py", "observer.py", "calibrate.py", "calibrate_rev3.py")}},
        "inputs_md5": {str(r): {f: md5(f"{root}/run_{r}/{f}") for f in ("stderr.log", f"v1_{r}.tr", "e1_opportunities.csv")} for r in runs},
        "revision2_calibration_md5_unchanged": md5(os.path.join(HERE, "e1_calibration.json")),
    }
    jp = os.path.join(HERE, "e1_calibration_rev3.json")
    if os.path.exists(jp):
        raise SystemExit("e1_calibration_rev3.json already exists; refusing to overwrite a frozen calibration")
    with open(jp, "w") as fh:
        json.dump(frozen, fh, indent=1)
    W("")
    W(f"Frozen revision-3 calibration: analysis/stageE/e1/e1_calibration_rev3.json  md5 {md5(jp)}")
    W(f"Revision-2 calibration e1_calibration.json md5 (unchanged): {frozen['revision2_calibration_md5_unchanged']}")
    open(os.path.join(HERE, "e1_calibration_report_rev3.txt"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
