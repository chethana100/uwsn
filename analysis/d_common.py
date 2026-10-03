#!/usr/bin/env python3
"""Shared loaders for Stage D (offline accounting). Separates ORACLE fields (simulator ground truth:
[DECISION] act/up, custody-equivalent 'up', malicious list) from OBSERVABLE fields (what a node decodes
from packets it receives: transmitter address, packet identity, millimetre-rounded f and d, its own
reception times, its own position/velocity)."""
import re, math, csv, collections as C

R, W, PRIO, MAXN, V0, TDELAY = 1000.0, 400.0, 1.5, 10, 1500.0, 1.0
TGT = (1500.0, 1500.0, 0.0)
SINK = 1
KV = re.compile(r"(\w+)=(\S+)")

def q(v):                      # VBHeader position serialization: (uint32)(v*1000+0.5)/1000 (v >= 0)
    return math.floor(v * 1000.0 + 0.5) / 1000.0
def ser_d(v):                  # VBHeader d serialization incl. negative values (x86 cast truncates toward 0, wraps)
    iv = math.trunc(v * 1000.0 + 0.5)
    return iv / 1000.0, (iv % (1 << 32)) / 1000.0   # (decoded-with-unwrap, raw value as printed/decoded)
def res6(v):                   # half resolution of a 6-significant-digit print
    return 0.5 * 10 ** (math.floor(math.log10(abs(v))) - 5) if v else 1e-12
sub = lambda a, b: (a[0] - b[0], a[1] - b[1], a[2] - b[2])
dot = lambda a, b: a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
norm = lambda a: math.sqrt(dot(a, a))
dist = lambda a, b: norm(sub(a, b))

def projection(x, o):
    w, v = sub(TGT, o), sub(x, o)
    cx, cy, cz = v[1] * w[2] - v[2] * w[1], v[2] * w[0] - v[0] * w[2], v[0] * w[1] - v[1] * w[0]
    l = norm(w)
    return 0.0 if l == 0 else math.sqrt(cx * cx + cy * cy + cz * cz) / l
def dcos(x, f):
    v, w = sub(x, f), sub(TGT, f)
    dd, l = norm(v), norm(w)
    return dd, (0.0 if dd == 0 or l == 0 else dot(v, w) / (dd * l))
def alpha_aquasim(x, o, f):    # Aqua-Sim-NG CalculateDelay (VBF Def. 1), hop-by-hop pipe origin o
    dd, ct = dcos(x, f)
    return projection(x, o) / W + (R - dd * ct) / R
def alpha_prime(x, f):         # HH-VBF Def. 2
    dd, ct = dcos(x, f)
    return (R - dd * ct) / R
def hold_paper(x, f):
    a = max(0.0, alpha_prime(x, f))
    return math.sqrt(a) * TDELAY + (R - dist(x, f)) / V0

NODE = re.compile(r"^([tr]) (\S+) /NodeList/(\d+)/")
HDR = re.compile(r"pkNum=(\d+) .*?senderAddr=(\d+) forwardAddr=(\d+).*?ForwardPos\(([^)]*)\).*?RecvToForwarder\(([^)]*)\)")

class Run:
    def __init__(self, d):
        self.d = d
        meta = list(csv.reader(open(f"{d}/v1_1_meta.csv")))
        m = dict(zip(meta[0], meta[1]))
        self.malicious = {int(x) + 1 for x in m["malicious_nodes"].split()}
        self.pos, self.vel = {}, {}
        with open(f"{d}/v1_1_mobility.csv") as fh:
            next(fh)
            for ln in fh:
                t, n, x, y, z, vx, vy, vz = ln.rstrip().split(",")
                k = (int(n) + 1, int(float(t)))            # keyed by ADDRESS (= index + 1)
                self.pos[k] = (float(x), float(y), float(z)); self.vel[k] = (float(vx), float(vy), float(vz))
        self.dec, self.hold, self.credit = {}, {}, []
        for ln in open(f"{d}/stderr.log"):
            if ln.startswith("[DECISION] "):
                k = dict(KV.findall(ln)); key = (int(k["node"]), int(k["src"]), int(k["pk"]))
                self.dec[key] = {"act": k["act"], "up": int(k["up"]), "n": int(k["n"]), "t": float(k["t"])}
            elif ln.startswith("[HOLD] "):
                k = dict(KV.findall(ln)); key = (int(k["node"]), int(k["src"]), int(k["pk"]))
                self.hold[key] = {"tx": float(k["tx"]), "finx": float(k["finx"]), "up": int(k["up"])}
            elif ln.startswith("[VERDICT] ") and " kind=CREDIT " in ln:
                k = dict(KV.findall(ln)); self.credit.append((int(k["tx"]), int(k["src"]), int(k["pk"]), int(k["prev"])))
        self.tx, self.rx = {}, []       # tx[(addr,src,pk)] = dict ; rx = list of (t, obs_addr, src, pk, fwd)
        cur = None
        with open(f"{d}/v1_1.tr", errors="ignore") as fh:
            for ln in fh:
                mm = NODE.match(ln)
                if mm:
                    cur = (mm.group(1), float(mm.group(2)), int(mm.group(3)) + 1)
                if cur is None:
                    continue
                h = HDR.search(ln)
                if h:
                    ev, t, addr = cur
                    pk, src, fwd = int(h.group(1)), int(h.group(2)), int(h.group(3))
                    fp = tuple(float(v) for v in h.group(4).split(":")); dp = tuple(float(v) for v in h.group(5).split(":"))
                    if ev == "t":
                        self.tx[(fwd, src, pk)] = {"t": t, "f_print": fp, "d_print": dp}
                    else:
                        self.rx.append((t, addr, src, pk, fwd))
                    cur = None
        self.reconstruct()

    def at(self, addr, t):
        return self.pos[(addr, int(math.floor(t)))]
    def velocity(self, addr, t):
        return self.vel[(addr, int(math.floor(t)))]

    def reconstruct(self):
        """Exact header f and d of every transmission (what receivers decode)."""
        self.recon_amb = 0
        order = sorted(self.tx, key=lambda k: self.tx[k]["t"])
        for k in order:
            e = self.tx[k]; dec = self.dec.get(k)
            amb = False
            if dec and dec["act"] == "ORIGIN":
                ts = dec["t"]; amb = abs(ts - round(ts)) <= res6(ts) + 1e-9
            elif dec and dec["act"] == "FWD" and k in self.hold:
                ts = self.hold[k]["tx"] + self.hold[k]["finx"]; amb = abs(ts - round(ts)) < 1e-6
            else:
                e["f"], e["d"], e["amb"] = e["f_print"], None, True; self.recon_amb += 1; continue
            e["f"] = tuple(q(c) for c in self.at(k[0], ts))
            if dec["act"] == "ORIGIN":
                e["d"], e["d_raw"] = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
            else:
                up = (dec["up"], k[1], k[2])
                fup = self.tx.get(up, {}).get("f")
                th = self.hold[k]["tx"]
                if fup is None:
                    e["d"] = None; amb = True
                else:
                    me = self.at(k[0], th)
                    dd = [ser_d(me[i] - fup[i]) for i in range(3)]
                    e["d"] = tuple(x[0] for x in dd); e["d_raw"] = tuple(x[1] for x in dd)
                    amb = amb or abs(th - round(th)) < 1e-6 or self.tx[up].get("amb", False)
            e["amb"] = amb
            if amb:
                self.recon_amb += 1
