#!/usr/bin/env python3
"""Stage D step 1: upstream-position recovery validation (before accepting eps).
recovered upstream position = f_X - d_X (both decoded from X's on-air header, mm-rounded).
Truth = header f of X's actual upstream copy (oracle: X's [DECISION] up). Also: distance from the
recovered position to every OTHER transmitter of the same packet (ambiguity at eps)."""
import sys, collections as C
from d_common import *

EPS = 25.0
for d in sys.argv[1:]:
    r = Run(d)
    # (a) reconstruction vs printed trace values (validates the exact header rebuild)
    fbad = dbad = n = 0
    for k, e in r.tx.items():
        if e.get("amb") or e.get("d") is None:
            continue
        n += 1
        if any(abs(e["f"][i] - e["f_print"][i]) > res6(e["f"][i]) + 1e-9 for i in range(3)): fbad += 1
        if any(abs(e["d_raw"][i] - e["d_print"][i]) > res6(e["d_raw"][i]) + 1e-9 for i in range(3)): dbad += 1
    # (b) recovery error and ambiguity
    errs, seps, amb_eps = [], [], 0
    bypkt = C.defaultdict(list)
    for k, e in r.tx.items():
        bypkt[(k[1], k[2])].append(k[0])
    for k, e in r.tx.items():
        dec = r.dec.get(k)
        if not dec or dec["act"] != "FWD" or e.get("amb") or e.get("d") is None:
            continue
        rec = sub(e["f"], e["d"])
        up = (dec["up"], k[1], k[2])
        if up not in r.tx or r.tx[up].get("amb"):
            continue
        errs.append(dist(rec, r.tx[up]["f"]))
        others = [dist(rec, r.tx[(y, k[1], k[2])]["f"]) for y in bypkt[(k[1], k[2])] if y not in (dec["up"], k[0])]
        if others:
            s = min(others); seps.append(s)
            if s <= EPS: amb_eps += 1
    errs.sort(); seps.sort()
    qt = lambda a, p: a[min(len(a) - 1, int(p * len(a)))]
    print(f"== {d}: transmissions {len(r.tx)}, exact header rebuild {n} (ambiguous/unrebuildable {r.recon_amb})")
    print(f"   rebuild vs printed trace (within 6-digit print resolution): f mismatches {fbad}, d mismatches {dbad}")
    print(f"   relay transmissions evaluated: {len(errs)}")
    print(f"   recovery error |(f_X - d_X) - f_upstream|: median {qt(errs,.5):.4f} m, p95 {qt(errs,.95):.4f}, p99 {qt(errs,.99):.4f}, max {errs[-1]:.4f} m")
    print(f"   nearest OTHER transmitter of the same packet to the recovered position: min {seps[0]:.1f} m, p1 {qt(seps,.01):.1f}, p5 {qt(seps,.05):.1f}, median {qt(seps,.5):.1f}")
    print(f"   relay transmissions with another transmitter within eps={EPS} m of the recovered position: {amb_eps}")
    print(f"   eps acceptance rule (stated before running): max error <= {EPS/2} m -> {'ACCEPT' if errs[-1] <= EPS/2 else 'STOP AND REPORT'}")
