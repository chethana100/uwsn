import sys, re, math, collections as C
sys.path.insert(0, "/home/aswinlaks/ns-allinone-3.41/ns-3.41/analysis")
from d_common import Run
new, old = sys.argv[1], sys.argv[2]
unwrap = lambda v: v - 4294967.296 if v > 2147483.648 else v
vec = lambda s: tuple(float(x) for x in s.split(":"))
KV = re.compile(r"(\w+)=(\S+)")
dec = {}
for ln in open(f"{new}/stderr.log", errors="ignore"):
    if ln.startswith("[RXHDR] "):
        k = dict(KV.findall(ln)); dec[(int(k["tx"]), int(k["src"]), int(k["pk"]))] = (vec(k["f"]), vec(k["d"]))
r = Run(old)
fs, ds, recs = [], [], []
for key, (f, d) in dec.items():
    e = r.tx.get(key)
    if not e or not (e.get("amb", False) or e.get("d") is None): continue
    fs.append(math.dist(f, e["f"]))
    if e.get("d") is not None:
        ds.append(math.dist(tuple(unwrap(x) for x in d), e["d"]))
        # recovered upstream position: decoded vs Stage D reconstruction
        recs.append(math.dist(tuple(a - unwrap(b) for a, b in zip(f, d)), tuple(a - b for a, b in zip(e["f"], e["d"]))))
fmt = lambda v: f"n={len(v)} max={max(v):.4f} m nonzero={sum(x > 1e-9 for x in v)}" if v else "n=0"
print(f"  ambiguous transmissions: |f diff| {fmt(fs)}; |d diff| {fmt(ds)}; |recovered upstream diff| {fmt(recs)}")
