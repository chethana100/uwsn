#!/usr/bin/env python3
"""Forwarding change: range-corrected legacy run vs Stage C default run. Diagnostic only (seed 1).
Progress toward the sink = d*cos(theta), recomputed from exact positions (f quantized as in VBHeader)."""
import sys, re, math, collections as C

T, R = (1500.0, 1500.0, 0.0), 1000.0
KV = re.compile(r"(\w+)=(\S+)")
q = lambda v: math.floor(v * 1000.0 + 0.5) / 1000.0

def analyse(run):
    pos = {}
    with open(f"{run}/v1_1_mobility.csv") as fh:
        next(fh)
        for ln in fh:
            t, n, x, y, z = ln.split(",")[:5]
            pos[(int(n), int(float(t)))] = (float(x), float(y), float(z))
    at = lambda i, t: pos[(i, int(math.floor(t)))]
    hs, ds = [], []
    for ln in open(f"{run}/stderr.log"):
        if ln.startswith("[HOLD] "): hs.append(dict(KV.findall(ln)))
        elif ln.startswith("[DECISION] "): ds.append(dict(KV.findall(ln)))
    txt = {(int(k["node"]), int(k["src"]), int(k["pk"])): float(k["t"]) for k in ds if k["act"] in ("FWD", "ORIGIN")}
    band, pairs = C.defaultdict(list), []
    for h in hs:
        tt = txt.get((int(h["up"]), int(h["src"]), int(h["pk"])))
        if tt is None or abs(tt - round(tt)) < 0.006: continue
        f = tuple(q(c) for c in at(int(h["up"]) - 1, tt))
        me = at(int(h["node"]) - 1, float(h["tx"]))
        v, w = [a - b for a, b in zip(me, f)], [a - b for a, b in zip(T, f)]
        dd, l = math.sqrt(sum(a * a for a in v)), math.sqrt(sum(a * a for a in w))
        prog = 0.0 if dd == 0 or l == 0 else sum(a * b for a, b in zip(v, w)) / l
        hold = float(h["finx"])
        band[-1 if prog < 0 else min(3, int(prog // 250))].append(hold); pairs.append((prog, hold))
    def ranks(vals):
        o = sorted(range(len(vals)), key=lambda i: vals[i]); r = [0] * len(vals)
        for k, i in enumerate(o): r[i] = k
        return r
    rp, rh = ranks([p for p, _ in pairs]), ranks([h for _, h in pairs]); n = len(pairs)
    mp, mh = sum(rp) / n, sum(rh) / n
    rho = sum((a - mp) * (b - mh) for a, b in zip(rp, rh)) / math.sqrt(sum((a - mp) ** 2 for a in rp) * sum((b - mh) ** 2 for b in rh))
    acts = C.Counter(k["act"] for k in ds)
    relays = C.Counter((k["src"], k["pk"], k["up"]) for k in ds if k["act"] in ("FWD", "DROP"))
    print(f"== {run}: decisions {dict(acts)}")
    print(f"   relays per (packet, upstream copy): mean {sum(relays.values())/len(relays):.2f}; "
          f"distribution (5 = 5+) {sorted(C.Counter(min(x, 5) for x in relays.values()).items())}")
    lab = {-1: "progress<0", 0: "0-250 m", 1: "250-500 m", 2: "500-750 m", 3: "750-1000 m"}
    for b in sorted(band):
        v = sorted(band[b])
        print(f"   hold vs progress {lab[b]:>11}: n={len(v):5d} median {v[len(v)//2]:.3f} s  min {v[0]:.3f}  max {v[-1]:.3f}")
    print(f"   Spearman(hold, progress) = {rho:+.3f}  over {n} holds (negative = more progress fires earlier)")

for run in sys.argv[1:]:
    analyse(run)
