#!/usr/bin/env python3
"""Stage D step 2: offline opportunity accounting on the corrected HH-VBF model (seed 1, diagnostic).

OPPORTUNITY (O, X, c=(U,P)), built ONLY from what O observes:
  source event: O decodes U's copy of P (O != U), or O itself transmits P (O == U)
  O's neighbour table: per node X, f and time of the last (and previous) copy O decoded from X before the event
  candidate X: in table, last heard <= 60 s, X not in {O, U, sink, P's source}
  eligibility estimate (corrected routing model, single-copy case, X's last known position x):
      |x - f_U| <= R, projection(x; pipe f_U -> sink) <= W, Aqua-Sim alpha(x) <= 1.5
  valid observable opportunity: eligible AND |pos_O - x| <= R (O could hear X's response)
  rank: alpha' hold time (Stage C) among eligible candidates, for stratification only
OUTCOME (observable): MATCH = O decodes X's copy of P whose recovered upstream (f_X - d_X) is within eps of f_U;
  OTHER-UP = O decodes X's copy but recovered upstream is elsewhere (EXCLUDED, never blamed);
  SILENT = O never decodes a copy of P from X.
GROUND TRUTH (oracle): X's [DECISION] for P: same upstream U -> FWD_TX / MAC_GIVEUP / DROP / SUPPRESS / INELIG /
  MAXNBR / OUTPIPE; different upstream -> DIFF_UP; no decision -> NORX (X never decoded any copy of P).
EAQTE exclusion: EE = 0.5*CCQ + 0.5*SS < 0.3 computed by O for X at the event (paper Eqs. 6-10, 13, 18, 25-26;
  f=25 kHz, k=1.5, Eb/N0=40 dB, m=640 bits; p-history = last 10 samples per (O,X) at opportunity events)."""
import sys, math, collections as C
from d_common import *

EPS, STALE = 25.0, 60.0
GTS = ["FWD_TX", "MAC_GIVEUP", "DROP", "SUPPRESS", "INELIG", "MAXNBR", "OUTPIPE", "DIFF_UP", "NORX"]

def p_success(dm):
    dk = dm / 1000.0
    if dk <= 0: return 1.0
    f2 = 25.0 ** 2
    adb = 0.11 * f2 / (1 + f2) + 44 * f2 / (4100 + f2) + 2.75e-4 * f2 + 0.003
    A = dk ** 1.5 * (10 ** (adb / 10)) ** dk
    snr = 1e4 / A
    pe = 0.5 * (1 - math.sqrt(snr / (1 + snr)))
    return min(1.0, max(0.0, (1 - pe) ** 640))

def analyse(d):
    r = Run(d)
    out = [f"\n######## {d}  (malicious nodes: {len(r.malicious)})"]
    # custody-equivalence check: [VERDICT] CREDIT means the custody tag prev == prev; compare with [DECISION] up
    ce = C.Counter(("eq" if r.dec.get((tx, s, p), {}).get("up") == prev else "ne") for tx, s, p, prev in r.credit)
    out.append(f"custody tag == [DECISION] up on [VERDICT] CREDIT lines: {dict(ce)}")

    rxby = C.defaultdict(list)                 # (O, src, pk) -> [(t, fwd)]
    events = C.defaultdict(list)               # O -> [(t, kind, U, src, pk)]
    for t, o, s, p, fwd in r.rx:
        rxby[(o, s, p)].append((t, fwd)); events[o].append((t, 1, fwd, s, p))
    for (u, s, p), e in r.tx.items():
        events[u].append((e["t"], 0, u, s, p))  # own transmission: O == U
    drops = {(x, s, p): v["up"] for (x, s, p), v in r.dec.items() if v["act"] == "DROP"}
    drop_by_c = C.defaultdict(list)
    for (x, s, p), u in drops.items(): drop_by_c[(u, s, p)].append(x)
    ever_tx = {k[0] for k in r.tx}

    def gt(x, u, s, p):
        v = r.dec.get((x, s, p))
        if v is None: return "NORX"
        if v["up"] != u: return "DIFF_UP"
        if v["act"] == "FWD": return "FWD_TX" if (x, s, p) in r.tx else "MAC_GIVEUP"
        return v["act"]

    def recovered(x, s, p):
        e = r.tx.get((x, s, p))
        if e is None: return None, None
        dd = e.get("d")
        if dd is None:                            # fallback: unwrap printed d (+/-5 m print precision)
            dd = tuple(v - 4294967.296 if v > 2147483.648 else v for v in e["d_print"])
        return sub(e["f"], dd), e.get("amb", False) or e.get("d") is None

    opps, stage = [], C.defaultdict(int)       # stage[(x,s,p)] = best observability stage over observers
    best_age = {}                              # freshest table entry for the dropper over potential observers
    obs_ok_noex = set()
    hist = C.defaultdict(list)
    for o, evs in events.items():
        evs.sort()
        table = {}
        for t, kind, u, s, p in evs:
            fu = r.tx.get((u, s, p), {}).get("f")
            if fu is not None:
                po = r.at(o, t); vo = r.velocity(o, t)
                # --- drop observability stages for every X that dropped this copy
                for x in drop_by_c.get((u, s, p), []):
                    st = 0
                    if x in table and x not in (o, u):
                        st = 1
                        lt, lf, pt, pf = table[x]
                        best_age[(x, s, p)] = min(best_age.get((x, s, p), 1e18), t - lt)
                        if t - lt <= STALE:
                            st = 2
                            if dist(lf, fu) <= R and projection(lf, fu) <= W and alpha_aquasim(lf, fu, fu) <= PRIO:
                                st = 3
                                if dist(po, lf) <= R: st = 4
                    stage[(x, s, p)] = max(stage[(x, s, p)], st)
                # --- candidates
                elig = []
                for x, (lt, lf, pt, pf) in table.items():
                    if x in (o, u, SINK, s) or t - lt > STALE: continue
                    if dist(lf, fu) > R or projection(lf, fu) > W or alpha_aquasim(lf, fu, fu) > PRIO: continue
                    elig.append((hold_paper(lf, fu), x, lf, lt, pt, pf))
                elig.sort()
                for rank, (hp, x, lf, lt, pt, pf) in enumerate(elig, 1):
                    if dist(po, lf) > R: continue          # O could not hear X's response
                    heard = [f for tt, f in rxby.get((o, s, p), []) if f == x]
                    if heard:
                        rec, ramb = recovered(x, s, p)
                        outc = "MATCH" if dist(rec, fu) <= EPS else "OTHER-UP"
                    else:
                        outc, rec, ramb = "SILENT", None, False
                    # EAQTE environment effect computed by O for X
                    if pt is not None and lt - pt >= 0.05:
                        vx = ((lf[0] - pf[0]) / (lt - pt), (lf[1] - pf[1]) / (lt - pt))
                    else:
                        vx = (0.0, 0.0)
                    ni, nj = math.hypot(vo[0], vo[1]), math.hypot(*vx)
                    ss = 0.5 if ni < 1e-6 or nj < 1e-6 else 0.5 * (1 + max(-1, min(1, (vo[0] * vx[0] + vo[1] * vx[1]) / (ni * nj))))
                    pnow = p_success(dist(po, lf))
                    h = hist[(o, x)]; h.append(pnow); del h[:-10]
                    var = 0.0 if len(h) < 2 else sum((v - sum(h) / len(h)) ** 2 for v in h) / len(h)
                    ee = 0.5 * pnow * (1 - math.tanh(var)) + 0.5 * ss
                    g = gt(x, u, s, p)
                    opps.append({"o": o, "x": x, "u": u, "s": s, "p": p, "own": o == u, "mal": x in r.malicious,
                                 "rank": rank, "out": outc, "gt": g, "ee": ee, "excl": ee < 0.3, "rec": rec, "ramb": ramb})
                    if g == "DROP" and not ee < 0.3: obs_ok_noex.add((x, s, p))
            if kind == 1:                                    # update O's table with this decoded copy
                f = r.tx.get((u, s, p), {}).get("f")
                if f is not None:
                    prev = table.get(u)
                    table[u] = (t, f, prev[0], prev[1]) if prev else (t, f, None, None)

    def split(o):
        return ("malicious" if o["mal"] else "honest") + (" | O=U" if o["own"] else " | O!=U")
    # ---------------- D1
    labels = {0: "X never heard by any potential observer", 1: "only stale entries (>60 s)",
              2: "fails observers' eligibility estimate", 3: "eligible but no observer within hearing range of X",
              4: "OBSERVABLE (>=1 valid opportunity)"}
    nd = len(drops)
    out.append(f"\n[D1] DROP observability: {nd} ground-truth DROP events by {len({k[0] for k in drops})} nodes")
    if nd:
        cnt = C.Counter(stage[k] for k in drops)
        for sidx in range(5):
            out.append(f"     {labels[sidx]:<55s} {cnt[sidx]:5d}  ({100*cnt[sidx]/nd:5.1f}%)")
        own_obs = sum(1 for k in drops if any(o["x"] == k[0] and o["s"] == k[1] and o["p"] == k[2] and o["own"] for o in opps))
        oth_obs = sum(1 for k in drops if any(o["x"] == k[0] and o["s"] == k[1] and o["p"] == k[2] and not o["own"] for o in opps))
        out.append(f"     observable via O=U: {own_obs} ({100*own_obs/nd:.1f}%);  via O!=U: {oth_obs} ({100*oth_obs/nd:.1f}%);  "
                   f"observable and not EAQTE-excluded for >=1 observer: {len(obs_ok_noex)} ({100*len(obs_ok_noex)/nd:.1f}%)")
        ag = sorted(best_age[k] for k in drops if stage[k] == 1)
        if ag:
            out.append(f"     'only stale' drops: freshest observer entry age min {ag[0]:.0f} s, median {ag[len(ag)//2]:.0f} s, max {ag[-1]:.0f} s; within 120 s: {sum(1 for a in ag if a <= 120)}, within 300 s: {sum(1 for a in ag if a <= 300)} of {len(ag)}")
        out.append(f"     dropping nodes that never transmitted anything in the run: {len({k[0] for k in drops} - ever_tx)} of {len({k[0] for k in drops})}")
    # ---------------- D2
    out.append(f"\n[D2] valid observable opportunities: {len(opps)}  (outcome rows x ground-truth columns)")
    for sp in ["honest | O!=U", "honest | O=U", "malicious | O!=U", "malicious | O=U"]:
        sel = [o for o in opps if split(o) == sp]
        if not sel: continue
        tab = C.defaultdict(C.Counter)
        for o in sel: tab[o["out"]][o["gt"]] += 1
        cols = [g for g in GTS if any(tab[k][g] for k in tab)]
        out.append(f"  -- {sp}  (n={len(sel)})")
        out.append("     " + f"{'':9s}" + "".join(f"{c:>11s}" for c in cols) + f"{'total':>8s}")
        for k in ["MATCH", "OTHER-UP", "SILENT"]:
            if k in tab:
                out.append("     " + f"{k:9s}" + "".join(f"{tab[k][c]:11d}" for c in cols) + f"{sum(tab[k].values()):8d}")
    # ---------------- D3
    out.append("\n[D3] silence vs ground truth (silent = the only outcome a blame could rest on; OTHER-UP excluded)")
    out.append(f"     {'split':18s} {'silent':>7s} {'=DROP':>6s} {'false-blame':>11s} | {'after EAQTE excl.':>17s} {'false-blame':>11s} | unique (X,c): silent {'=DROP':>6s} {'false-blame':>11s}")
    for sp in ["honest | O!=U", "honest | O=U", "malicious | O!=U", "malicious | O=U", "ALL"]:
        sel = [o for o in opps if o["out"] == "SILENT" and (sp == "ALL" or split(o) == sp)]
        if not sel: continue
        dr = sum(1 for o in sel if o["gt"] == "DROP")
        kept = [o for o in sel if not o["excl"]]; drk = sum(1 for o in kept if o["gt"] == "DROP")
        uniq = {}
        for o in sel: uniq[(o["x"], o["u"], o["s"], o["p"])] = o["gt"]
        du = sum(1 for g in uniq.values() if g == "DROP")
        fb = lambda a, b: f"{100*(a-b)/a:6.1f}%" if a else "   n/a"
        out.append(f"     {sp:18s} {len(sel):7d} {dr:6d} {fb(len(sel), dr):>11s} | {len(kept):17d} {fb(len(kept), drk):>11s} | {len(uniq):20d} {du:6d} {fb(len(uniq), du):>11s}")
    sil = [o for o in opps if o["out"] == "SILENT"]
    mk = C.Counter(o["gt"] for o in sil)
    out.append(f"     makeup of ALL silent opportunities: {dict(mk.most_common())}")
    for rk in (1, 2):
        s2 = [o for o in sil if (o["rank"] == 1) == (rk == 1)]
        if s2:
            out.append(f"     silent with predicted rank {'1 (first firer)' if rk == 1 else '>=2'}: n={len(s2)}, =DROP {sum(1 for o in s2 if o['gt']=='DROP')}, makeup {dict(C.Counter(o['gt'] for o in s2).most_common(5))}")
    mt = [o for o in opps if o["out"] == "MATCH"]
    out.append(f"     MATCH ground truth: {dict(C.Counter(o['gt'] for o in mt))}")
    # ---------------- D4
    resp = [o for o in opps if o["out"] in ("MATCH", "OTHER-UP")]
    pos_ag = C.Counter(); id_ag = C.Counter()
    for o in resp:
        prev = r.dec.get((o["x"], o["s"], o["p"]), {}).get("up")
        fprev = r.tx.get((prev, o["s"], o["p"]), {}).get("f") if prev else None
        pos_ag["agree" if fprev and dist(o["rec"], fprev) <= EPS else ("no custody/stamp" if not fprev else "disagree")] += 1
        known = {f for tt, f in rxby.get((o["o"], o["s"], o["p"]), []) if f != o["x"]}
        if (o["o"], o["s"], o["p"]) in r.tx: known.add(o["o"])
        best = min(((dist(o["rec"], r.tx[(y, o["s"], o["p"])]["f"]), y) for y in known if (y, o["s"], o["p"]) in r.tx), default=None)
        if best is None or best[0] > EPS: id_ag["unresolved (upstream not decoded by O)"] += 1
        else: id_ag["agree" if best[1] == prev else "disagree"] += 1
    out.append(f"\n[D4] recovered upstream vs custody tag over {len(resp)} heard responses (MATCH + OTHER-UP):")
    out.append(f"     position level (|f_X - d_X - f_custody| <= eps): {dict(pos_ag)}")
    out.append(f"     identity resolvable by O (nearest transmitter O decoded, within eps): {dict(id_ag)}")
    out.append(f"     recovered-position used fallback (printed d) in {sum(1 for o in resp if o['ramb'])} responses")
    # ---------------- D5
    ex = [o for o in opps if o["excl"]]
    out.append(f"\n[D5] EAQTE environmental exclusion (EE < 0.3): {len(ex)} of {len(opps)} opportunities ({100*len(ex)/max(1,len(opps)):.2f}%)")
    out.append(f"     excluded makeup: outcome {dict(C.Counter(o['out'] for o in ex))}; ground truth {dict(C.Counter(o['gt'] for o in ex).most_common())}")
    out.append(f"     excluded by split: {dict(C.Counter(split(o) for o in ex))}")
    ees = sorted(o["ee"] for o in opps)
    out.append(f"     EE over opportunities: p1 {ees[len(ees)//100]:.3f}, median {ees[len(ees)//2]:.3f}, max {ees[-1]:.3f}")
    # ---------------- relay-count observation
    grp = C.defaultdict(list)
    for (x, s, p), v in r.dec.items():
        if v["act"] in ("FWD", "DROP"): grp[(s, p, v["up"])].append(v["n"])
    sz = C.Counter(min(len(g), 5) for g in grp.values())
    out.append(f"\n[RELAYS] relays (FWD+DROP decisions) per (packet, upstream copy): {sorted(sz.items())}  (5 = 5+)")
    for k in sorted(sz):
        ns = [n for g in grp.values() if min(len(g), 5) == k for n in g]
        out.append(f"     group size {k}: {sz[k]} groups; members deciding with n=1 (no duplicate heard before timer): {sum(1 for n in ns if n == 1)}/{len(ns)}")
    print("\n".join(out))

for d in sys.argv[1:]:
    analyse(d)
