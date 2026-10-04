# Validate [RXHDR] decoded header logging against (a) the printed trace header and (b) the Stage D reconstruction.
import sys, re, math, collections as C
sys.path.insert(0, "/home/aswinlaks/ns-allinone-3.41/ns-3.41/analysis")
from d_common import Run, NODE, HDR, res6, TGT
new, old = sys.argv[1], sys.argv[2]
unwrap = lambda v: v - 4294967.296 if v > 2147483.648 else v
vec = lambda s: tuple(float(x) for x in s.split(":"))
KV = re.compile(r"(\w+)=(\S+)")
rx = {}; dup = 0
for ln in open(f"{new}/stderr.log", errors="ignore"):
    if ln.startswith("[RXHDR] "):
        k = dict(KV.findall(ln)); key = (int(k["node"]), int(k["tx"]), int(k["src"]), int(k["pk"]))
        dup += key in rx
        rx[key] = {"f": vec(k["f"]), "d": vec(k["d"]), "tgt": vec(k["tgt"]), "t": float(k["t"])}
tr = {}; cur = None
with open(f"{new}/v1_1.tr", errors="ignore") as fh:
    for ln in fh:
        m = NODE.match(ln)
        if m: cur = (m.group(1), float(m.group(2)), int(m.group(3)) + 1)
        if cur is None: continue
        h = HDR.search(ln)
        if h:
            ev, t, addr = cur
            if ev == "r":
                tr[(addr, int(h.group(3)), int(h.group(2)), int(h.group(1)))] = {"f": vec(h.group(4).replace(",", ":")), "d": vec(h.group(5).replace(",", ":")), "t": t}
            cur = None
print(f"  [RXHDR] lines {len(rx)} (duplicate keys {dup}); trace r-records {len(tr)}; keys only in RXHDR {len(set(rx)-set(tr))}, only in trace {len(set(tr)-set(rx))}")
# (a) vs printed trace (6 significant digits)
bad = C.Counter(); maxrel = 0.0
for k in set(rx) & set(tr):
    a, b = rx[k], tr[k]
    for fld in ("f", "d"):
        for x, y in zip(a[fld], b[fld]):
            if abs(x - y) > res6(y) + 1e-9: bad[fld] += 1
    if abs(a["t"] - b["t"]) > res6(b["t"]) + 1e-9: bad["time"] += 1
    if a["tgt"] != TGT: bad["tgt"] += 1
    for x in a["f"] + a["d"]:
        if abs(x * 1000 - round(x * 1000)) > 1e-6: bad["not_mm_grid"] += 1
print(f"  (a) vs printed trace: component mismatches beyond print resolution {dict(bad) if bad else 'none'}; target != (1500,1500,0): {bad['tgt']}")
# consistency across receivers of the same transmission
pertx = C.defaultdict(set)
for (n, x, s, p), v in rx.items(): pertx[(x, s, p)].add((v["f"], v["d"]))
print(f"  transmissions heard {len(pertx)}; with >1 distinct decoded (f,d) across receivers: {sum(1 for v in pertx.values() if len(v) > 1)}")
# (b) vs Stage D reconstruction (archived run of the identical configuration)
r = Run(old)
cnt = C.Counter()
for (x, s, p), vals in pertx.items():
    (f, d), = vals if len(vals) == 1 else (next(iter(vals)),)
    e = r.tx.get((x, s, p))
    if e is None: cnt["no_tx_in_stageD"] += 1; continue
    amb = e.get("amb", False) or e.get("d") is None
    tag = "amb" if amb else "exact"
    cnt[tag + "_n"] += 1
    if max(abs(a - b) for a, b in zip(f, e["f"])) > 1e-9: cnt[tag + "_f_mismatch"] += 1
    if e.get("d") is not None:
        if max(abs(unwrap(a) - b) for a, b in zip(d, e["d"])) > 1e-9: cnt[tag + "_d_mismatch"] += 1
    else:
        cnt[tag + "_d_unreconstructed"] += 1
print(f"  (b) vs Stage D reconstruction: {dict(sorted(cnt.items()))}")
# (c) upstream recovery from genuinely decoded values: f_X - unwrap(d_X) vs decoded f of the upstream copy ([DECISION] up used ONLY to pick the reference)
err = []; miss = 0
for (x, s, p), vals in pertx.items():
    f, d = next(iter(vals)); dec = r.dec.get((x, s, p))
    if not dec or dec["act"] != "FWD": continue
    up = dec["up"]; ref = pertx.get((up, s, p))
    if not ref: miss += 1; continue
    fu = next(iter(ref))[0]
    rec = tuple(a - unwrap(b) for a, b in zip(f, d))
    err.append(math.dist(rec, fu))
err.sort()
print(f"  (c) upstream recovery from decoded f,d: n={len(err)}, max err {err[-1]:.3f} m, median {err[len(err)//2]:.3f} m, >25 m: {sum(e > 25 for e in err)}; upstream copy never decoded by anyone: {miss}")
