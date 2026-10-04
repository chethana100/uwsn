# (a) Is a pair's silence propensity stable over time?  (b) What power is possible at all against p = 0.75 given the
# observed honest heterogeneity (model-based limit, no candidate calibrated on E1)?  (c) How much do observer-visible
# covariates reduce the heterogeneity?  Read-only on existing E1 outputs.
import sys, csv, json, math, collections as C
import numpy as np
E1 = "/home/aswinlaks/ns-allinone-3.41/ns-3.41/analysis/stageE/e1"
sys.path.insert(0, E1)
from geom import dist, projection, alpha_prime, W
cal = json.load(open(f"{E1}/e1_calibration.json")); mm = cal["merge_map"]; q = {k: v["q"] for k, v in cal["strata"].items()}
K1N, K2N, K3N = {0: "O!=U", 1: "O=U"}, {0: "rank1", 1: "rank2", 2: "rank>=3"}, {0: "age<=20", 1: "age20-40", 2: "age40-60"}
root = "/home/aswinlaks/uwsn-runs/stageE/E1"; TG = (1500., 1500., 0.)
rows = []
for run in range(12, 22):
    for r in csv.DictReader(open(f"{root}/run_{run}/e1_opportunities.csv")):
        if r["out"] == "OTHER-UP": continue
        xp = tuple(map(float, r["xpos"].split(":"))); fu = tuple(map(float, r["fu"].split(":")))
        cell = f"{K1N[int(r['k1'])]}|{K2N[int(r['k2'])]}|{K3N[int(r['k3'])]}"
        rows.append((run, int(r["o"]), int(r["x"]), float(r["t0"]), int(r["out"] == "SILENT"), q[mm[cell]],
                     projection(xp, fu, TG) / W, dist(xp, fu) / 1000.0, alpha_prime(xp, fu, TG), int(r["n_elig"]), cell))
pairs = C.defaultdict(list)
for r in rows: pairs[r[:3]].append(r)
# (a) stationarity: residual rate in first vs second half of each pair's opportunities (time order)
a, b, gaps = [], [], []
for k, lst in pairs.items():
    if len(lst) < 40: continue
    lst.sort(key=lambda r: r[3]); h = len(lst) // 2
    f = np.mean([r[4] - r[5] for r in lst[:h]]); s = np.mean([r[4] - r[5] for r in lst[h:]]); a.append(f); b.append(s)
    gaps.append(lst[-1][3] - lst[0][3])
print(f"(a) pairs with n>=40: {len(a)}; corr(first-half residual, second-half residual) = {np.corrcoef(a, b)[0,1]:.3f}; "
      f"median time span of a pair {np.median(gaps):.0f} s")
lagc = C.defaultdict(list)
for k, lst in pairs.items():
    if len(lst) < 40: continue
    lst.sort(key=lambda r: r[3]); t = np.array([r[3] for r in lst]); e = np.array([r[4] - r[5] for r in lst])
    for lo, hi in [(0, 60), (60, 300), (300, 900), (900, 3000)]:
        for i in range(0, len(lst), 3):
            j = np.where((t - t[i] >= lo) & (t - t[i] < hi) & (np.arange(len(t)) > i))[0]
            if len(j): lagc[(lo, hi)].append((e[i], e[j[0]]))
print("    within-pair residual correlation vs time lag: " + "; ".join(f"[{lo},{hi}) s r={np.corrcoef(*zip(*v))[0,1]:.3f} (n={len(v)})" for (lo, hi), v in sorted(lagc.items())))
# (b) model-based power ceiling: honest propensity theta ~ Beta with the pooled mean and rho (moment fit), attacker theta1 = 1-(1-theta)(1-0.75)
qbar, rho = 0.378, 0.2954
ab = 1 / rho - 1; A, B = qbar * ab, (1 - qbar) * ab
g = np.random.default_rng(1); hb = g.beta(A, B, 400000); thr = np.quantile(hb, 0.95)
pw_inf = np.mean(1 - 0.25 * (1 - g.beta(A, B, 400000)) > thr)
print(f"(b) honest propensity ~ Beta({A:.3f},{B:.3f}) (mean {qbar}, rho {rho}); 95th percentile {thr:.3f}; "
      f"n->infinity power vs p=0.75 at FA 0.05 = {pw_inf:.3f}")
for rr in (0.15, 0.10, 0.05):
    ab = 1 / rr - 1; A2, B2 = qbar * ab, (1 - qbar) * ab; t2 = np.quantile(g.beta(A2, B2, 400000), 0.95)
    print(f"    if covariates reduced rho to {rr}: 95th pct {t2:.3f}; n->inf power {np.mean(1 - 0.25 * (1 - g.beta(A2, B2, 400000)) > t2):.3f}")
# (c) covariate reduction of pair heterogeneity: logistic fit on stratum + observable geometry, then moment rho on residuals
X = np.column_stack([np.ones(len(rows)), [r[6] for r in rows], [r[7] for r in rows], [r[7] ** 2 for r in rows], [r[8] for r in rows],
                     [min(r[9], 6) for r in rows]] + [[1.0 if r[10] == c else 0.0 for r in rows] for c in sorted(set(r[10] for r in rows))[1:]])
yv = np.array([r[4] for r in rows], float)
beta = np.zeros(X.shape[1])
for _ in range(30):                                   # IRLS logistic regression
    p = 1 / (1 + np.exp(-X @ beta)); w = p * (1 - p)
    beta += np.linalg.solve(X.T @ (X * w[:, None]) + 1e-9 * np.eye(len(beta)), X.T @ (yv - p))
p = 1 / (1 + np.exp(-X @ beta))
def rho_of(pred):
    idx = C.defaultdict(list)
    for i, r in enumerate(rows): idx[r[:3]].append(i)
    num = den = 0.0
    for k, ii in idx.items():
        if len(ii) < 14: continue
        ii = np.array(ii); K = yv[ii].sum(); E = pred[ii].sum(); V = (pred[ii] * (1 - pred[ii])).sum()
        num += (K - E) ** 2 - V; den += V * (len(ii) - 1)
    return num / den
qs = np.array([r[5] for r in rows])
print(f"(c) pair-level rho: strata only {rho_of(qs):.4f}; strata + observable geometry (projection/W, D, D^2, alpha', n_elig) {rho_of(p):.4f}")
