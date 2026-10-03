#!/usr/bin/env python3
"""Stage C verification V2/V3 on one run directory (tag v1, run 1). Independent of the C++ code:
positions come from the exact mobility log (MCM state piecewise constant on [k, k+1)), copies from the
PHY trace, constants R=1000, W=400, T_delay=1.0, v0=1500, threshold 1.5, MAX_NEIGHBOR=10.
V2: alpha' = (R - d cos(theta))/R and d recomputed for every [HOLD]; hold T = sqrt(alpha')*T_delay + (R-d)/v0
    compared (a) internally against the logged full-precision fields, (b) against the independent values.
V3: every TimeoutTrustAware decision (FWD/SUPPRESS/INELIG/MAXNBR/DROP) re-derived with a Python
    re-implementation of the Aqua-Sim-NG rule (Aqua-Sim alpha = p/W + (R - d cos)/R; n==1: alpha<=1.5;
    n>1: min alpha <= 1.5/2^(n-1); n==10: quit), using the copies the node had decoded by its timer expiry."""
import re, sys, math, collections as C

d = sys.argv[1]
R, W, TDELAY, V0, PRIO, MAXN = 1000.0, 400.0, 1.0, 1500.0, 1.5, 10
T = (1500.0, 1500.0, 0.0)
EPS_T = 1e-6

pos = {}
with open(f"{d}/v1_1_mobility.csv") as fh:
    next(fh)
    for ln in fh:
        t, n, x, y, z = ln.split(",")[:5]
        pos[(int(n), int(float(t)))] = (float(x), float(y), float(z))
def at(idx, t): return pos[(idx, int(math.floor(t)))]
def ambiguous(t): return abs(t - round(t)) < EPS_T

sub = lambda a, b: (a[0] - b[0], a[1] - b[1], a[2] - b[2])
dot = lambda a, b: a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
norm = lambda a: math.sqrt(dot(a, a))
def cos_theta(me, f):
    v, w = sub(me, f), sub(T, f)
    dd, l = norm(v), norm(w)
    return dd, (0.0 if dd == 0 or l == 0 else dot(v, w) / (dd * l))
def alpha_prime(me, f):
    dd, ct = cos_theta(me, f)
    return (R - dd * ct) / R, dd
def projection(me, o):                 # Aqua-Sim Projection, hop-by-hop: o = f of the held copy
    w, v = sub(T, o), sub(me, o)
    cx, cy, cz = v[1] * w[2] - v[2] * w[1], v[2] * w[0] - v[0] * w[2], v[0] * w[1] - v[1] * w[0]
    l = norm(w)
    return 0.0 if l == 0 else math.sqrt(cx * cx + cy * cy + cz * cz) / l
def alpha_aquasim(me, o, f):
    dd, ct = cos_theta(me, f)
    return projection(me, o) / W + (R - dd * ct) / R

KV = re.compile(r"(\w+)=(\S+)")
holds, decs, guards = [], [], 0
for ln in open(f"{d}/stderr.log"):
    if ln.startswith("[HOLD] "):
        holds.append(dict(KV.findall(ln)))
    elif ln.startswith("[DECISION] "):
        decs.append(dict(KV.findall(ln)))
    elif ln.startswith("[GUARD]"):
        guards += 1

# stamped f of each transmission = transmitter position at its MACprepare (= its ORIGIN/FWD decision time)
txtime = {}
for k in decs:
    if k["act"] in ("FWD", "ORIGIN"):
        txtime[(int(k["node"]), int(k["src"]), int(k["pk"]))] = float(k["t"])   # 6 significant digits
def stamped_f(addr, src, pk):
    t = txtime.get((addr, src, pk))
    if t is None:
        return None, True
    amb = abs(t - round(t)) < 0.006            # printed time has ~2 decimals at this magnitude
    x, y, z = at(addr - 1, t)
    q = lambda v: math.floor(v * 1000.0 + 0.5) / 1000.0   # (fix) VBHeader serializes f as (uint32)(x*1000+0.5)
    return (q(x), q(y), q(z)), amb

# ---------------- V2
print(f"== {d}")
print(f"[V2] [HOLD] lines {len(holds)}; [GUARD] events {guards}")
fin = lambda s: float(s)
nonfinite = sum(1 for h in holds for k in ("halpha", "d", "hhx", "finx") if not math.isfinite(fin(h[k])))
hh = [fin(h["hhx"]) for h in holds]; fn = [fin(h["finx"]) for h in holds]; al = [fin(h["halpha"]) for h in holds]
print(f"[V2] non-finite halpha/d/hhx/finx: {nonfinite}; halpha min {min(al):.6f} max {max(al):.6f}; "
      f"hh min {min(hh):.6f} max {max(hh):.6f}; final min {min(fn):.6f} max {max(fn):.6f}; negative final: {sum(1 for v in fn if v < 0)}")
internal = max(abs(fin(h["hhx"]) - (math.sqrt(fin(h["halpha"])) * TDELAY + (R - fin(h["d"])) / V0)) for h in holds)
print(f"[V2] internal hold identity max |hh - (sqrt(halpha)*T_delay + (R-d)/v0)| = {internal:.3e}")
eq_final = sum(1 for h in holds if h["finx"] == h["hhx"])
print(f"[V2] final == hh (string-exact, 17 digits): {eq_final}/{len(holds)}")
ea, ed, eh, amb, nof = [], [], [], 0, 0
for h in holds:
    node, src, pk, up, t = int(h["node"]), int(h["src"]), int(h["pk"]), int(h["up"]), fin(h["tx"])
    f, famb = stamped_f(up, src, pk)
    if f is None:
        nof += 1; continue
    if famb or ambiguous(t):
        amb += 1; continue
    a2, dd = alpha_prime(at(node - 1, t), f)
    ea.append(abs(a2 - fin(h["halpha"]))); ed.append(abs(dd - fin(h["d"])))
    eh.append(abs(math.sqrt(a2) * TDELAY + (R - dd) / V0 - fin(h["hhx"])))
print(f"[V2] independent recomputation from mobility log: compared {len(ea)}, skipped-ambiguous-time {amb}, no-stamp {nof}")
print(f"[V2]   max |alpha'_indep - halpha| = {max(ea):.3e};  max |d_indep - d| = {max(ed):.3e} m;  max |T_indep - hh| = {max(eh):.3e} s")

# ---------------- V3
copies = C.defaultdict(list)          # (node_addr, src, pk) -> [(t_r, transmitter_addr)]
NODE = re.compile(r"^r (\S+) /NodeList/(\d+)/")
HDR = re.compile(r"pkNum=(\d+) .*?senderAddr=(\d+) forwardAddr=(\d+)")
cur = None
with open(f"{d}/v1_1.tr", errors="ignore") as fh:
    for ln in fh:
        if ln[:2] in ("t ", "r ", "d "):
            m = NODE.match(ln); cur = (float(m.group(1)), int(m.group(2)) + 1) if m else None
        if cur:
            h = HDR.search(ln)
            if h:
                copies[(cur[1], int(h.group(2)), int(h.group(1)))].append((cur[0], int(h.group(3)))); cur = None
holdmap = {(int(h["node"]), int(h["src"]), int(h["pk"])): h for h in holds}
res, amb3 = C.Counter(), 0
mism = []
for k in decs:
    act = k["act"]
    if act not in ("FWD", "SUPPRESS", "INELIG", "MAXNBR", "DROP"):
        continue
    key = (int(k["node"]), int(k["src"]), int(k["pk"]))
    h = holdmap.get(key)
    if h is None:
        res["no HOLD"] += 1; continue
    texp = fin(h["tx"]) + fin(h["finx"])            # timer expiry
    cps = sorted(copies[key])
    got = [c for c in cps if c[0] <= texp + 1e-9]
    res6 = lambda v: 0.5 * 10 ** (math.floor(math.log10(abs(v))) - 5) if v else 0.0   # (fix) trace prints 6 sig. digits
    if any(abs(c[0] - texp) <= res6(c[0]) + 1e-9 for c in cps) or ambiguous(texp):
        amb3 += 1; continue
    fs, bad = [], False
    for tr, xmit in got[:MAXN]:
        f, famb = stamped_f(xmit, key[1], key[2])
        if f is None or famb:
            bad = True; break
        fs.append(f)
    if bad or not fs:
        amb3 += 1; continue
    n = min(len(got), MAXN)
    me = at(key[0] - 1, texp)
    o = fs[0]                                          # held copy = first copy
    if n == MAXN:
        pred, margin = "MAXNBR", None
    elif n == 1:
        a = alpha_aquasim(me, o, fs[0]); thr = PRIO
        pred, margin = ("FWD" if a <= thr else "INELIG"), a - thr
    else:
        a = min(alpha_aquasim(me, o, f) for f in fs[:n]); thr = PRIO / 2 ** (n - 1)
        pred, margin = ("FWD" if a <= thr else "SUPPRESS"), a - thr
    logged = "FWD" if act == "DROP" else act          # DROP = would have forwarded (malicious)
    ok = pred == logged
    res["match" if ok else "MISMATCH"] += 1
    if not ok:
        mism.append((key, act, pred, n, margin))
print(f"[V3] decisions re-derived: {dict(res)}; skipped (ambiguous time/stamp) {amb3}")
for m in mism[:10]:
    print("   mismatch", m)
print(f"[V3] decision mix: {dict(C.Counter(k['act'] for k in decs))}")
