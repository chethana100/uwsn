#!/usr/bin/env python3
"""Stage E E1 calibration — O2 (frozen spec rev 2, ../README.md §7) and check V6 (§12).
Reads ONLY the observer-side opportunity files of the clean calibration runs (every node honest).
Order: stratum rates -> n_ref -> tau_A -> n_min (Monte Carlo, R = 10,000, NumPy PCG64 seed 12345) -> freeze.

usage: calibrate.py <E1 run root> <run> [<run> ...]
"""
import sys, os, csv, json, math, hashlib, subprocess, datetime, collections as C
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NS, P_MIN, POWER, FA_TARGET = 2401, 0.75, 0.80, 0.05
R_MC, SEED = 10000, 12345
B_BOOT = 10000                      # V6 cluster bootstrap replicates (implementation choice, see report)
CELLS = [(k1, k2, k3) for k1 in (0, 1) for k2 in (0, 1, 2) for k3 in (0, 1, 2)]
K1N, K2N, K3N = {0: "O!=U", 1: "O=U"}, {0: "rank1", 1: "rank2", 2: "rank>=3", "2+": "rank>=2"}, \
    {0: "age<=20", 1: "age20-40", 2: "age40-60", "*": "age-any"}


def name(lbl):
    return f"{K1N[lbl[0]]}|{K2N[lbl[1]]}|{K3N[lbl[2]]}"


def load(root, runs):
    """(run, o, x, cell, y) for MATCH (y=0) and SILENT (y=1); OTHER-UP is excluded."""
    rows = []
    for run in runs:
        for r in csv.DictReader(open(f"{root}/run_{run}/e1_opportunities.csv")):
            if r["out"] == "OTHER-UP":
                continue
            rows.append((run, int(r["o"]), int(r["x"]), (int(r["k1"]), int(r["k2"]), int(r["k3"])),
                         1 if r["out"] == "SILENT" else 0))
    return rows


def merge_map(cnt):
    """Merge rule: merge K3 levels first, then merge rank 2 with >=3. Deterministic reading:
    (1) within each (K1,K2), if any K3 cell < N_s, collapse K3 for that (K1,K2);
    (2) within each K1, if any rank-2 or rank>=3 cell is still < N_s, merge ranks 2 and >=3
        (K3 kept split only if neither was collapsed and every merged K3 cell >= N_s)."""
    lab = {c: c for c in CELLS}
    for k1 in (0, 1):
        for k2 in (0, 1, 2):
            if any(cnt[(k1, k2, k3)] < NS for k3 in (0, 1, 2)):
                for k3 in (0, 1, 2):
                    lab[(k1, k2, k3)] = (k1, k2, "*")

    def size(l):
        return sum(cnt[c] for c in CELLS if lab[c] == l)

    for k1 in (0, 1):
        ls = {lab[c] for c in CELLS if c[0] == k1 and c[1] in (1, 2)}
        if any(size(l) < NS for l in ls):
            keep = all(lab[(k1, k2, k3)] == (k1, k2, k3) for k2 in (1, 2) for k3 in (0, 1, 2)) and \
                all(cnt[(k1, 1, k3)] + cnt[(k1, 2, k3)] >= NS for k3 in (0, 1, 2))
            for k2 in (1, 2):
                for k3 in (0, 1, 2):
                    lab[(k1, k2, k3)] = (k1, "2+", k3 if keep else "*")
    left = sorted({name(l) for l in lab.values() if size(l) < NS})
    return lab, left


def pair_stats(rows, lab, q):
    """Per pair (run, o, x): n, sum(y - q), sum q(1 - q), Z."""
    acc = C.defaultdict(lambda: [0, 0.0, 0.0])
    for run, o, x, cell, y in rows:
        qs = q[lab[cell]]
        a = acc[(run, o, x)]
        a[0] += 1; a[1] += y - qs; a[2] += qs * (1 - qs)
    return {k: (n, num / math.sqrt(den)) for k, (n, num, den) in acc.items()}


def calibrate(rows, full_curve=True):
    cnt = C.Counter(cell for *_, cell, y in rows)
    lab, left = merge_map(cnt)
    tot, sil = C.Counter(), C.Counter()
    for *_, cell, y in rows:
        tot[lab[cell]] += 1; sil[lab[cell]] += y
    q = {l: sil[l] / tot[l] for l in tot}
    res = {"cell_counts": {name(c): cnt[c] for c in CELLS}, "merge_map": {name(c): name(lab[c]) for c in CELLS},
           "undersized_after_merge": left,
           "strata": {name(l): {"n": tot[l], "silent": sil[l], "q": q[l]} for l in sorted(tot, key=name)}}
    if any(v in (0.0, 1.0) for v in q.values()):
        res["stop"] = "a merged stratum has q_s in {0, 1}"
        return res, lab, q
    qbar = sum(sil.values()) / sum(tot.values())
    n_ref = math.ceil(5 / min(qbar, 1 - qbar))
    ps = pair_stats(rows, lab, q)
    ref = sorted(z for n, z in ps.values() if n >= n_ref)
    N = len(ref)
    tau = ref[math.ceil(0.95 * N) - 1]
    n_cap = max(n for n, z in ps.values())
    labels = sorted(tot, key=name)
    probs = np.array([tot[l] for l in labels], float); probs /= probs.sum()
    cum = np.cumsum(probs); cum[-1] = 1.0
    qv = np.array([q[l] for l in labels]); q1 = 1 - (1 - qv) * (1 - P_MIN)
    rng = np.random.Generator(np.random.PCG64(SEED))
    curve, n_min = [], None
    for n in range(n_ref, n_cap + 1):
        S = np.searchsorted(cum, rng.random((R_MC, n)), side="right")   # strata i.i.d. from the empirical mix
        y = rng.random((R_MC, n)) < q1[S]                                # y ~ Bernoulli(q1_s)
        qs = qv[S]
        z = (y - qs).sum(1) / np.sqrt((qs * (1 - qs)).sum(1))            # Z with the calibration q_s
        pw = float((z > tau).mean())
        curve.append((n, pw))
        if n_min is None and pw >= POWER:
            n_min = n
            if not full_curve:
                break
    res.update({"qbar": qbar, "n_ref": n_ref, "pairs_total": len(ps), "pairs_ge_n_ref": N, "tau_A": tau,
                "n_cap": n_cap, "power_curve": curve, "n_min": n_min})
    return res, lab, q


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    root, runs = sys.argv[1], [int(a) for a in sys.argv[2:]]
    rows = load(root, runs)
    res, lab, q = calibrate(rows, full_curve=True)
    out = []
    P = out.append
    P("Stage E E1 calibration (frozen spec rev 2, README §7) — clean seeds " + ",".join(map(str, runs)))
    P(f"MATCH+SILENT opportunities: {len(rows)} (OTHER-UP excluded); SILENT {sum(r[-1] for r in rows)}")
    P("")
    P(f"Step 1 cell counts (N_s = {NS}):")
    for c, v in res["cell_counts"].items():
        P(f"   {c:28s} {v:7d}  -> {res['merge_map'][c]}")
    P(f"   undersized after merge rule: {res['undersized_after_merge'] if res['undersized_after_merge'] else 'none'}")
    P("   merged strata q_s:")
    for l, v in res["strata"].items():
        P(f"   {l:28s} n {v['n']:7d}  silent {v['silent']:6d}  q_s {v['q']:.6f}")
    if "stop" in res:
        P(f"STOP: {res['stop']}")
        open(os.path.join(HERE, "e1_calibration_report.txt"), "w").write("\n".join(out) + "\n")
        print("\n".join(out)); return
    P("")
    P(f"Step 2  q_bar = {res['qbar']:.6f}; n_ref = ceil(5 / min(q_bar, 1 - q_bar)) = {res['n_ref']}")
    P(f"Step 3  tau_A = {res['tau_A']:.6f} (nearest rank ceil(0.95 N) over N = {res['pairs_ge_n_ref']} honest pairs "
      f"with n >= n_ref; {res['pairs_total']} pairs in total)")
    P(f"Step 4  power curve n = {res['n_ref']}..{res['n_cap']} (R = {R_MC}, PCG64 seed {SEED}, p_min {P_MIN}):")
    curve = res["power_curve"]
    for i in range(0, len(curve), 10):
        P("   " + "  ".join(f"{n}:{p:.4f}" for n, p in curve[i:i + 10]))
    P(f"        n_min = {res['n_min']} (smallest n with power >= {POWER})")
    if res["n_min"] is None:
        P("        n_min undefined -> G1 FAILS (no adjustment)")
    # Step 5 — reported, never tuned
    ps = pair_stats(rows, lab, q)
    tau, n_min, n_ref = res["tau_A"], res["n_min"], res["n_ref"]
    judged = [z for n, z in ps.values() if n_min is not None and n >= n_min]
    fa = sum(z > tau for z in judged) / len(judged) if judged else float("nan")
    zr = np.array([z for n, z in ps.values() if n >= n_ref])
    P("")
    P(f"Step 5  calibration FA among honest pairs with n >= n_min at tau_A: {sum(z > tau for z in judged)}/{len(judged)} = {fa:.4f}")
    P(f"        over-dispersion of Z (pairs with n >= n_ref, N = {len(zr)}): mean {zr.mean():.4f}, variance {zr.var(ddof=1):.4f}, "
      f"mean Z^2 {np.mean(zr ** 2):.4f} (1 expected for independent Bernoulli opportunities with correct q_s)")
    nz = np.array([n for n, z in ps.values() if n >= n_ref])
    for lo, hi in [(n_ref, 2 * n_ref), (2 * n_ref, 5 * n_ref), (5 * n_ref, 10 ** 9)]:
        sel = zr[(nz >= lo) & (nz < hi)]
        if len(sel) > 1:
            P(f"        n in [{lo}, {hi if hi < 10 ** 9 else 'max'}): N {len(sel)}, var(Z) {sel.var(ddof=1):.4f}, "
              f"95th pct {np.percentile(sel, 95):.4f}")
    per_seed = C.defaultdict(lambda: [0, 0])
    for (run, o, x), (n, z) in ps.items():
        if n_min is not None and n >= n_min:
            per_seed[run][0] += 1; per_seed[run][1] += z > tau
    P("        per-seed calibration FA (in-sample): " + ", ".join(f"{r}:{f}/{j}" for r, (j, f) in sorted(per_seed.items())))
    # ---------- V6: leave-one-seed-out ----------
    P("")
    P("V6 leave-one-seed-out (steps 1-4 rerun on the other nine seeds; FA on the left-out seed's judged pairs):")
    clusters, v6_ok, v6_fail = {}, True, []
    for k in runs:
        tr = [r for r in rows if r[0] != k]
        te = [r for r in rows if r[0] == k]
        rk, labk, qk = calibrate(tr, full_curve=False)
        if "stop" in rk or rk.get("n_min") is None:
            v6_ok = False; v6_fail.append(k); P(f"   seed {k}: fold calibration failed ({rk.get('stop', 'n_min undefined')})"); continue
        psk = pair_stats(te, labk, qk)
        perx = C.defaultdict(lambda: [0, 0])
        for (run, o, x), (n, z) in psk.items():
            if n >= rk["n_min"]:
                perx[x][0] += 1; perx[x][1] += z > rk["tau_A"]
        clusters[k] = np.array(list(perx.values()), float).reshape(-1, 2)
        j, f = clusters[k].sum(0) if len(clusters[k]) else (0, 0)
        P(f"   seed {k}: n_ref {rk['n_ref']}, tau {rk['tau_A']:.4f}, n_min {rk['n_min']}; judged {int(j)}, flagged {int(f)}, "
          f"FA {f / j if j else float('nan'):.4f}")
    J = sum(c[:, 0].sum() for c in clusters.values()); F = sum(c[:, 1].sum() for c in clusters.values())
    rngb = np.random.Generator(np.random.PCG64(SEED))
    keys = sorted(clusters)
    boot = np.empty(B_BOOT)
    for b in range(B_BOOT):
        jj = ff = 0.0
        for s in rngb.integers(0, len(keys), len(keys)):
            c = clusters[keys[s]]
            if len(c):
                pick = c[rngb.integers(0, len(c), len(c))]
                jj += pick[:, 0].sum(); ff += pick[:, 1].sum()
        boot[b] = ff / jj if jj else np.nan
    lower = float(np.nanpercentile(boot, 5))
    v6_pass = v6_ok and lower <= FA_TARGET
    P(f"   pooled out-of-seed FA {int(F)}/{int(J)} = {F / J:.4f}; one-sided 95% lower bound (cluster bootstrap seeds -> nodes, "
      f"B = {B_BOOT}, PCG64 seed {SEED}) = {lower:.4f}")
    P(f"   V6 (pooled FA not significantly above {FA_TARGET}): {'PASS' if v6_pass else 'FAIL'}")
    # ---------- freeze ----------
    git = lambda *a: subprocess.run(["git", *a], cwd=HERE, capture_output=True, text=True).stdout.strip()
    frozen = {
        "spec": "analysis/stageE/README.md, frozen revision 2 (parent commit c0d2cec)",
        "created_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "calibration_seeds": runs, "N_s": NS, "p_min": P_MIN, "power_target": POWER, "fa_target": FA_TARGET,
        "mc": {"R": R_MC, "rng": "numpy.random.PCG64", "seed": SEED,
               "sampling": "strata by inverse-CDF on the empirical stratum mix; y ~ Bernoulli(q1_s); one generator, n ascending"},
        **{k: res[k] for k in ("cell_counts", "merge_map", "undersized_after_merge", "strata", "qbar", "n_ref", "pairs_total",
                               "pairs_ge_n_ref", "tau_A", "n_cap", "n_min", "power_curve")},
        "calibration_fa": {"judged": len(judged), "flagged": int(sum(z > tau for z in judged)), "fa": fa},
        "overdispersion": {"N": int(len(zr)), "mean_Z": float(zr.mean()), "var_Z": float(zr.var(ddof=1)), "mean_Z2": float(np.mean(zr ** 2))},
        "V6": {"pooled_judged": int(J), "pooled_flagged": int(F), "pooled_fa": F / J, "lower95_one_sided": lower,
               "bootstrap": {"B": B_BOOT, "rng": "numpy.random.PCG64", "seed": SEED, "clusters": "seeds then X nodes"}, "pass": v6_pass},
        "code": {"parent_commit": git("rev-parse", "HEAD"), "submodule_commit": git("-C", "../../../src/aqua-sim-ng", "rev-parse", "HEAD"),
                 "scripts_md5": {f: md5(os.path.join(HERE, f)) for f in ("geom.py", "observer.py", "calibrate.py")}},
        "inputs_md5": {str(r): {f: md5(f"{root}/run_{r}/{f}") for f in ("stderr.log", f"v1_{r}.tr", "e1_opportunities.csv")} for r in runs},
    }
    jp = os.path.join(HERE, "e1_calibration.json")
    with open(jp, "w") as fh:
        json.dump(frozen, fh, indent=1)
    P("")
    P(f"Frozen calibration file: analysis/stageE/e1/e1_calibration.json  md5 {md5(jp)}")
    open(os.path.join(HERE, "e1_calibration_report.txt"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
