# Re-derive the Stage D opportunity list (same loop as analysis/d_accounting.py) and diff it with the E1 observer output.
import sys, csv, math, collections as C
sys.path.insert(0, "/home/aswinlaks/ns-allinone-3.41/ns-3.41/analysis")
from d_common import *
EPS, STALE = 25.0, 60.0
old, newcsv = sys.argv[1], sys.argv[2]
r = Run(old)
rxby = C.defaultdict(list); events = C.defaultdict(list)
for t, o, s, p, fwd in r.rx:
    rxby[(o, s, p)].append((t, fwd)); events[o].append((t, 1, fwd, s, p))
for (u, s, p), e in r.tx.items(): events[u].append((e["t"], 0, u, s, p))
def recovered(x, s, p):
    e = r.tx.get((x, s, p)); dd = e.get("d")
    if dd is None: dd = tuple(v - 4294967.296 if v > 2147483.648 else v for v in e["d_print"])
    return sub(e["f"], dd)
D = {}
for o, evs in events.items():
    evs.sort(); table = {}
    for t, kind, u, s, p in evs:
        fu = r.tx.get((u, s, p), {}).get("f")
        if fu is not None:
            po = r.at(o, t); elig = []
            for x, (lt, lf, pt, pf) in table.items():
                if x in (o, u, SINK, s) or t - lt > STALE: continue
                if dist(lf, fu) > R or projection(lf, fu) > W or alpha_aquasim(lf, fu, fu) > PRIO: continue
                elig.append((hold_paper(lf, fu), x, lf, lt))
            elig.sort()
            for rank, (hp, x, lf, lt) in enumerate(elig, 1):
                if dist(po, lf) > R: continue
                heard = [f for tt, f in rxby.get((o, s, p), []) if f == x]
                out = ("MATCH" if dist(recovered(x, s, p), fu) <= EPS else "OTHER-UP") if heard else "SILENT"
                D[(o, x, u, s, p)] = (out, rank, t)
        if kind == 1:
            f = r.tx.get((u, s, p), {}).get("f")
            if f is not None:
                prev = table.get(u); table[u] = (t, f, prev[0] if prev else None, prev[1] if prev else None)
N = {}
for row in csv.DictReader(open(newcsv)):
    N[(int(row["o"]), int(row["x"]), int(row["u"]), int(row["s"]), int(row["p"]))] = (row["out"], int(row["rank"]), float(row["t0"]))
print("stageD", len(D), "new", len(N))
for k in sorted(set(D) - set(N)): print("  only Stage D:", k, D[k])
for k in sorted(set(N) - set(D)): print("  only new   :", k, N[k])
diff = [(k, D[k], N[k]) for k in set(D) & set(N) if D[k][0] != N[k][0] or D[k][1] != N[k][1]]
print("  same key, different outcome/rank:", len(diff)); [print("   ", d) for d in diff[:10]]
