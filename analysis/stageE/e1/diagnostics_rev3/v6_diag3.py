# Decompose pair-level excess variance into additive observer (O) and neighbour (X) effects within seed (read-only).
import csv, json, math, collections as C
import numpy as np
E1 = "/home/aswinlaks/ns-allinone-3.41/ns-3.41/analysis/stageE/e1"
cal = json.load(open(f"{E1}/e1_calibration.json")); mm = cal["merge_map"]; q = {k: v["q"] for k, v in cal["strata"].items()}
K1N, K2N, K3N = {0: "O!=U", 1: "O=U"}, {0: "rank1", 1: "rank2", 2: "rank>=3"}, {0: "age<=20", 1: "age20-40", 2: "age40-60"}
acc = C.defaultdict(lambda: [0, 0.0, 0.0])
for run in range(12, 22):
    for r in csv.DictReader(open(f"/home/aswinlaks/uwsn-runs/stageE/E1/run_{run}/e1_opportunities.csv")):
        if r["out"] == "OTHER-UP": continue
        qs = q[mm[f"{K1N[int(r['k1'])]}|{K2N[int(r['k2'])]}|{K3N[int(r['k3'])]}"]]
        a = acc[(run, int(r["o"]), int(r["x"]))]; a[0] += 1; a[1] += (r["out"] == "SILENT") - qs; a[2] += qs * (1 - qs)
keys = [k for k, v in acc.items() if v[0] >= 14]
n = np.array([acc[k][0] for k in keys], float); res = np.array([acc[k][1] / acc[k][0] for k in keys]); bv = np.array([acc[k][2] / acc[k][0] ** 2 for k in keys])
O = [(k[0], k[1]) for k in keys]; X = [(k[0], k[2]) for k in keys]
ao, bx = C.defaultdict(float), C.defaultdict(float)
for _ in range(50):                                   # weighted alternating least squares, weights n
    for grp, eff, oth in ((O, ao, bx), (X, bx, ao)):
        s, w = C.defaultdict(float), C.defaultdict(float)
        for i, g in enumerate(grp):
            other = oth[(X if grp is O else O)[i]]; s[g] += n[i] * (res[i] - other); w[g] += n[i]
        for g in s: eff[g] = s[g] / w[g]
fit = np.array([ao[O[i]] + bx[X[i]] for i in range(len(keys))])
tot_excess = np.average(res ** 2 - bv, weights=n); after = np.average((res - fit) ** 2 - bv, weights=n)
print(f"pairs n>=14: {len(keys)}; weighted excess variance of pair residual rate (beyond binomial): {tot_excess:.4f}")
print(f"  explained by additive observer + neighbour effects (within seed): {1 - after / tot_excess:.3f}; remaining pair-specific excess {after:.4f}")
oe = np.array([ao[g] for g in set(O)]); xe = np.array([bx[g] for g in set(X)])
print(f"  SD of observer effects {oe.std():.3f} (n={len(oe)}); SD of neighbour effects {xe.std():.3f} (n={len(xe)}); "
      f"SD of remaining pair-specific {math.sqrt(max(after, 0)):.3f}")
