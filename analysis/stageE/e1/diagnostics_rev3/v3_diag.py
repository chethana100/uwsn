# V3 diagnosis from existing E1 outputs (read-only). Classification margin actually used by O1, and transmitter spacing.
import sys, csv, math, collections as C
E1 = "/home/aswinlaks/ns-allinone-3.41/ns-3.41/analysis/stageE/e1"; sys.path.insert(0, E1)
from geom import dist, EPS
from truth import Truth
root = "/home/aswinlaks/uwsn-runs/stageE/E1"
mx_match, mn_other, near_other = 0.0, 1e9, C.Counter()
spacing = []; close_pairs = C.Counter()
for run in range(12, 22):
    for r in csv.DictReader(open(f"{root}/run_{run}/e1_opportunities.csv")):
        if r["out"] == "SILENT": continue
        dd = dist(tuple(map(float, r["rec"].split(":"))), tuple(map(float, r["fu"].split(":"))))
        if r["out"] == "MATCH": mx_match = max(mx_match, dd)
        else:
            mn_other = min(mn_other, dd)
            for th in (25.6, 37.5, 50, 75): near_other[th] += dd < th
    T = Truth(f"{root}/run_{run}", run)
    for (s, p), nodes in T.bypkt.items():
        fs = [(y, T.exact_f((y, s, p))) for y in nodes]
        for i in range(len(fs)):
            for j in range(i + 1, len(fs)):
                d = dist(fs[i][1], fs[j][1]); spacing.append(d)
                if d < 50: close_pairs[(run, tuple(sorted((fs[i][0], fs[j][0]))))] += 1
spacing.sort()
print(f"O1 classification margin: max |u_hat - f_U| over MATCH = {mx_match:.3f} m; min over OTHER-UP = {mn_other:.1f} m (epsilon = {EPS} m)")
print(f"   OTHER-UP opportunities with |u_hat - f_U| below 25.6 / 37.5 / 50 / 75 m: {[near_other[t] for t in (25.6, 37.5, 50, 75)]}")
print(f"distinct transmitters of the same packet: {len(spacing)} pairs; min spacing {spacing[0]:.1f} m; "
      f"< 25.6 m: {sum(d < 25.6 for d in spacing)}; < 37.5 m: {sum(d < 37.5 for d in spacing)}; < 50 m: {sum(d < 50 for d in spacing)}")
print(f"   node pairs involved in < 50 m spacings: {dict(close_pairs)}")
