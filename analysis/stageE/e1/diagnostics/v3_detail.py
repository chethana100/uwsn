# Evaluation-only detail for the V3 separation failure (no methodology change).
import sys, csv, collections as C
sys.path.insert(0, "/home/aswinlaks/ns-allinone-3.41/ns-3.41/analysis/stageE/e1")
from geom import dist, EPS
from truth import Truth
root = "/home/aswinlaks/uwsn-runs/stageE/E1"
seps = []; close = []
for run in range(12, 22):
    T = Truth(f"{root}/run_{run}", run); seen = set()
    for row in csv.DictReader(open(f"{root}/run_{run}/e1_opportunities.csv")):
        if row["out"] == "SILENT": continue
        x, s, p = int(row["x"]), int(row["s"]), int(row["p"])
        if (x, s, p) in seen: continue
        seen.add((x, s, p))
        rec = tuple(float(v) for v in row["rec"].split(":")); up = T.dec[(x, s, p)]["up"]
        best = min(((dist(rec, T.exact_f((y, s, p))), y) for y in T.bypkt[(s, p)] if y not in (up, x)), default=None)
        if best:
            seps.append(best[0])
            if best[0] < 2 * EPS:
                y = best[1]
                close.append((run, x, s, p, up, y, round(best[0], 1), round(dist(T.exact_f((up, s, p)), T.exact_f((y, s, p))), 1),
                              round(T.tx[(up, s, p)][0], 3), round(T.tx[(y, s, p)][0], 3)))
seps.sort()
print("unique responding transmissions with another transmitter considered:", len(seps))
for th in (25, 50, 75, 100, 136):
    print(f"  separation < {th} m: {sum(s < th for s in seps)}")
print("  min, p0.1%, p1%:", round(seps[0], 1), round(seps[int(.001 * len(seps))], 1), round(seps[int(.01 * len(seps))], 1))
print("cases < 50 m: (run, X, src, pk, true upstream U, nearby transmitter Y, |rec - f_Y|, |f_U - f_Y|, t_U, t_Y)")
for c in close: print("  ", c)
