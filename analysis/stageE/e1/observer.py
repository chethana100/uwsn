#!/usr/bin/env python3
"""Stage E O1 opportunity construction — OBSERVER SIDE ONLY (frozen spec rev 2, ../README.md §5, §6).

observe() handles one observer O and receives ONLY O's own data:
  dec : O's own [RXHDR] records (copies O decoded): (t, tx, src, pk, f, d, tgt)
  own : O's own transmissions, from O's own trace 't' records: (t0, src, pk, f)  [6 significant digits]
  mob : O's own mobility rows {second: (x, y, z)}
This file reads no ground-truth source (audited by check V5 in e1_validate.py).

usage: observer.py <rundir> <run>   -> writes <rundir>/e1_opportunities.csv and prints a summary
"""
import sys, re, csv, math, bisect, collections as C
from geom import (R, W, PRIO, SINK, TGT, EPS, STALE, WINDOW, unwrap, res6, dist,
                  projection, alpha_aquasim, hold_paper, age_bin, rank_bin)

KV = re.compile(r"(\w+)=(\S+)")
TREC = re.compile(r"^t (\S+) /NodeList/(\d+)/")
VBH = re.compile(r"pkNum=(\d+) .*?senderAddr=(\d+) forwardAddr=(\d+).*?ForwardPos\(([^)]*)\)")


def vec(s):
    return tuple(float(v) for v in s.replace(",", ":").split(":"))


def load_inputs(rundir, run):
    """Partition the observer-visible inputs by node. Nothing else is read."""
    dec = C.defaultdict(list)
    with open(f"{rundir}/stderr.log", errors="ignore") as fh:
        for ln in fh:
            if ln.startswith("[RXHDR] "):
                k = dict(KV.findall(ln))
                dec[int(k["node"])].append((float(k["t"]), int(k["tx"]), int(k["src"]), int(k["pk"]),
                                            vec(k["f"]), vec(k["d"]), vec(k["tgt"])))
    own = C.defaultdict(list)
    cur = None
    with open(f"{rundir}/v1_{run}.tr", errors="ignore") as fh:
        for ln in fh:
            if ln[:2] in ("t ", "r "):
                m = TREC.match(ln)
                cur = (float(m.group(1)), int(m.group(2)) + 1) if m else None
            if cur is None:
                continue
            h = VBH.search(ln)
            if h:
                t0, node = cur
                if int(h.group(3)) != node:
                    raise SystemExit(f"t record at node {node} carries forwardAddr {h.group(3)}")
                own[node].append((t0, int(h.group(2)), int(h.group(1)), vec(h.group(4))))
                cur = None
    mob = C.defaultdict(dict)
    with open(f"{rundir}/v1_{run}_mobility.csv") as fh:
        next(fh)
        for ln in fh:
            t, n, x, y, z = ln.split(",")[:5]
            mob[int(n) + 1][int(math.floor(float(t)))] = (float(x), float(y), float(z))
    return dec, own, mob


def observe(o, dec, own, mob):
    """O1 for observer o, using only o's own data. Returns (opportunities, stats)."""
    st = C.Counter()
    rxby = C.defaultdict(list)                       # (src, pk) -> [(t, tx, f, d)] decoded by o
    events = []
    for (t, tx, s, p, f, d, tgt) in dec:
        rxby[(s, p)].append((t, tx, f, d))
        # source event: o decodes U's copy; t0 = reception time; key = t0
        events.append((t, 1, tx, s, p, t, f, tgt))
    dec_times = sorted(e[0] for e in dec)
    for (t0, s, p, f) in own:
        # source event: o itself transmits P (O = U); tie rule: decodes count as "before" only if t < t0 - res6(t0)
        events.append((t0 - res6(t0), 0, o, s, p, t0, f, TGT))
        lo = bisect.bisect_left(dec_times, t0 - res6(t0))
        hi = bisect.bisect_right(dec_times, t0 + res6(t0))
        st["tie_window_decodes"] += hi - lo
        if abs(t0 - round(t0)) <= res6(t0):
            st["own_t0_near_whole_second"] += 1
    events.sort(key=lambda e: (e[0], e[1], e[2], e[3], e[4]))

    table = {}                                       # X -> (last t, last f, prev t, prev f)
    pending, cur_key = [], None
    opps = []
    for key, kind, u, s, p, t0, fu, tgt in events:
        if key != cur_key:                           # copies decoded strictly before this event
            for (y, ty, fy) in pending:
                prev = table.get(y)
                table[y] = (ty, fy, prev[0] if prev else None, prev[1] if prev else None)
            pending, cur_key = [], key
        st["events_own" if kind == 0 else "events_decode"] += 1
        if tgt != TGT:
            st["tgt_not_constant"] += 1
        sec = int(math.floor(t0))
        if kind == 1 and abs(t0 - round(t0)) < 1e-9:
            st["decode_t0_whole_second"] += 1
        po = mob.get(sec)
        if po is None:
            st["no_own_position"] += 1
        else:
            elig = []
            for x, (lt, lf, pt, pf) in table.items():
                if x in (o, u, SINK, s) or t0 - lt > STALE:
                    continue
                if dist(lf, fu) > R or projection(lf, fu, tgt) > W or alpha_aquasim(lf, fu, fu, tgt) > PRIO:
                    continue
                elig.append((hold_paper(lf, fu, tgt), x, lf, lt))
            elig.sort()                              # rank among ALL eligible, before the hearing filter (C3)
            for rank, (hp, x, lf, lt) in enumerate(elig, 1):
                if dist(po, lf) > R:                 # hearing filter
                    continue
                heard = [(tr, fx, dx) for (tr, tx, fx, dx) in rxby[(s, p)] if tx == x]
                if len(heard) > 1:
                    st["x_copy_decoded_more_than_once"] += 1
                if heard:
                    tr, fx, dx = heard[0]
                    rec = tuple(fx[i] - unwrap(dx[i]) for i in range(3))
                    out = "MATCH" if dist(rec, fu) <= EPS else "OTHER-UP"
                    ts = tr                          # secondary timestamp: response reception time
                else:
                    tr, rec, out = None, None, "SILENT"
                    ts = t0 + WINDOW                 # secondary timestamp for SILENT
                age = t0 - lt
                opps.append({"o": o, "x": x, "u": u, "s": s, "p": p, "t0": t0, "own": int(kind == 0),
                             "rank": rank, "n_elig": len(elig), "age": age,
                             "k1": int(kind == 0), "k2": rank_bin(rank), "k3": age_bin(age),
                             "out": out, "resp_t": tr, "ts": ts,
                             "rec": rec, "fu": fu, "xpos": lf})
        if kind == 1:
            pending.append((u, t0, fu))
    return opps, st


COLS = ["o", "x", "u", "s", "p", "t0", "own", "rank", "n_elig", "age", "k1", "k2", "k3", "out", "resp_t", "ts",
        "rec", "fu", "xpos"]


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, tuple):
        return ":".join(repr(c) for c in v)
    return repr(v) if isinstance(v, float) else str(v)


def main():
    rundir, run = sys.argv[1], int(sys.argv[2])
    dec, own, mob = load_inputs(rundir, run)
    nodes = sorted(set(dec) | set(own))
    allst = C.Counter()
    with open(f"{rundir}/e1_opportunities.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run"] + COLS)
        n_out = C.Counter()
        for o in nodes:
            opps, st = observe(o, dec.get(o, []), own.get(o, []), mob.get(o, {}))
            allst.update(st)
            for op in opps:
                n_out[op["out"]] += 1
                w.writerow([run] + [fmt(op[c]) for c in COLS])
    print(f"run {run}: observers {len(nodes)}; opportunities {sum(n_out.values())} {dict(n_out)}; stats {dict(sorted(allst.items()))}")


if __name__ == "__main__":
    main()
