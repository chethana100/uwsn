# Revision-3 diagnosis of the V6 failure from existing E1 outputs (read-only; no new runs).
import sys, csv, json, math, collections as C
import numpy as np
E1 = "/home/aswinlaks/ns-allinone-3.41/ns-3.41/analysis/stageE/e1"
sys.path.insert(0, E1)
from geom import dist, alpha_prime, projection, R, W
cal = json.load(open(f"{E1}/e1_calibration.json"))
K1N, K2N, K3N = {0: "O!=U", 1: "O=U"}, {0: "rank1", 1: "rank2", 2: "rank>=3"}, {0: "age<=20", 1: "age20-40", 2: "age40-60"}
mm = cal["merge_map"]; q = {k: v["q"] for k, v in cal["strata"].items()}
tau = cal["tau_A"]; n_min = cal["n_min"]; n_ref = cal["n_ref"]
root = "/home/aswinlaks/uwsn-runs/stageE/E1"
rows = []
for run in range(12, 22):
    for r in csv.DictReader(open(f"{root}/run_{run}/e1_opportunities.csv")):
        if r["out"] == "OTHER-UP": continue
        cell = f"{K1N[int(r['k1'])]}|{K2N[int(r['k2'])]}|{K3N[int(r['k3'])]}"
        xp = tuple(map(float, r["xpos"].split(":"))); fu = tuple(map(float, r["fu"].split(":")))
        rows.append(dict(run=run, o=int(r["o"]), x=int(r["x"]), y=int(r["out"] == "SILENT"), qs=q[mm[cell]],
                         D=dist(xp, fu), ap=alpha_prime(xp, fu, (1500., 1500., 0.)), pj=projection(xp, fu, (1500., 1500., 0.)),
                         nel=int(r["n_elig"]), rank=int(r["rank"]), own=int(r["own"]), age=float(r["age"])))
y = np.array([r["y"] for r in rows]); qs = np.array([r["qs"] for r in rows])
print(f"opportunities {len(rows)}; pooled silence {y.mean():.4f}")
# --- pair statistics
pairs = C.defaultdict(list)
for i, r in enumerate(rows): pairs[(r["run"], r["o"], r["x"])].append(i)
P = []
for k, idx in pairs.items():
    idx = np.array(idx); n = len(idx); K = y[idx].sum(); E = qs[idx].sum(); V = (qs[idx] * (1 - qs[idx])).sum()
    P.append((k, n, K, E, V, (K - E) / math.sqrt(V)))
n_ = np.array([p[1] for p in P]); K_ = np.array([p[2] for p in P]); E_ = np.array([p[3] for p in P]); V_ = np.array([p[4] for p in P]); Z = np.array([p[5] for p in P])
print("\n[1] False alarms at the frozen tau_A by pair size (honest clean pairs):")
for lo, hi in [(14, 28), (28, 50), (50, 98), (98, 150), (150, 250), (250, 600)]:
    s = (n_ >= lo) & (n_ < hi)
    print(f"   n [{lo},{hi}): pairs {s.sum():4d}  FA@tau {np.mean(Z[s] > tau):.3f}  var(Z) {Z[s].var(ddof=1):6.2f}  95th pct Z {np.percentile(Z[s], 95):6.2f}")
print("\n[2] Binomial vs observed variance of pair counts: ratio = sum (K-E)^2 / sum V, by n; beta-binomial predicts 1 + (n-1)*rho")
rat = []
for lo, hi in [(14, 28), (28, 50), (50, 98), (98, 150), (150, 250), (250, 600)]:
    s = (n_ >= lo) & (n_ < hi)
    ratio = ((K_[s] - E_[s]) ** 2).sum() / V_[s].sum(); nb = n_[s].mean(); rat.append((nb, ratio))
    print(f"   n [{lo},{hi}): mean n {nb:6.1f}  variance ratio {ratio:6.2f}  implied rho {(ratio - 1) / (nb - 1):.4f}")
s = n_ >= n_ref
rho = (((K_[s] - E_[s]) ** 2 - V_[s]).sum()) / ((V_[s] * (n_[s] - 1)).sum())
print(f"   pooled moment estimate rho = {rho:.4f}  -> pair-level SD of the silence propensity around its stratum mean ~ sqrt(rho*q(1-q)) = {math.sqrt(rho * 0.378 * 0.622):.3f}")
# --- where does the heterogeneity sit? share of residual sum of squares explained by seed, observer, neighbour, pair
res = y - qs
def r2(keyf):
    g = C.defaultdict(lambda: [0.0, 0])
    for i, r in enumerate(rows): a = g[keyf(r)]; a[0] += res[i]; a[1] += 1
    ss_between = sum(s * s / n for s, n in g.values()); ss_tot = (res ** 2).sum() - res.sum() ** 2 / len(res)
    return ss_between / ss_tot, len(g)
print("\n[3] Share of opportunity-level residual variance (y - q_s) explained by group means (ANOVA R^2; upper bound, unadjusted):")
for nm, f in [("seed", lambda r: r["run"]), ("seed x observer O", lambda r: (r["run"], r["o"])), ("seed x neighbour X", lambda r: (r["run"], r["x"])),
              ("seed x pair (O,X)", lambda r: (r["run"], r["o"], r["x"]))]:
    v, g = r2(f); print(f"   {nm:20s} groups {g:5d}  R^2 {v:.4f}")
# --- per-seed silence after stratum adjustment
print("\n[4] Per-seed observed vs stratum-expected silence (shows seed-level shifts):")
for run in range(12, 22):
    m = np.array([r["run"] == run for r in rows]); print(f"   seed {run}: observed {y[m].mean():.3f}  expected {qs[m].mean():.3f}  diff {y[m].mean() - qs[m].mean():+.3f}")
# --- observer-observable covariates: silence rate by bins (residual vs stratum)
print("\n[5] Residual silence (observed - stratum q) by observer-observable covariates:")
def tab(nm, val, edges):
    v = np.array([val(r) for r in rows]); out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (v >= lo) & (v < hi)
        if m.sum(): out.append(f"[{lo},{hi}) n={m.sum()} res={res[m].mean():+.3f}")
    print(f"   {nm}: " + "; ".join(out))
tab("D=|x-f_U| m", lambda r: r["D"], [0, 250, 500, 750, 1001])
tab("alpha' (progress)", lambda r: r["ap"], [0, .5, .8, 1.0, 1.2, 2.01])
tab("projection/W", lambda r: r["pj"] / W, [0, .25, .5, .75, 1.01])
tab("n eligible", lambda r: r["nel"], [1, 2, 4, 7, 11, 100])
