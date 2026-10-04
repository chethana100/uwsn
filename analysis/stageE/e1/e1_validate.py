#!/usr/bin/env python3
"""Stage E E1 — G1 evidence-layer checks V1-V5, V7, V8 (frozen spec rev 2, ../README.md §12).
V6 (leave-one-seed-out FA) is computed in calibrate.py. Evaluation code: uses ground truth (truth.py).

usage: e1_validate.py <E1 run root> <run> [<run> ...]
"""
import sys, os, re, csv, math, collections as C
from geom import dist, res6, p_success, EPS, WINDOW
from truth import Truth, GTS

HERE = os.path.dirname(os.path.abspath(__file__))
root, runs = sys.argv[1], [int(a) for a in sys.argv[2:]]
EBN0_CPP = 40.0                                    # value compiled into the C++ binary (V7 compares against it)


def tup(s):
    return tuple(float(v) for v in s.split(":")) if s else None


# ---------- V5: static audit of the observer-side and calibration code ----------
FORBIDDEN = ["[DECISION]", "[HOLD]", "[VERDICT]", "[OBSERVER]", "[EAQTE", "[SSCCQ]", "[EE]", "custody", "Custody",
             "malicious", "_meta", "truth", "d_common", "act=", "trust.csv", "observed.csv"]
v5 = {}
for fn in ["observer.py", "geom.py", "calibrate.py"]:
    src = open(os.path.join(HERE, fn)).read()
    body = re.sub(r'"""(.|\n)*?"""', "", src)      # docstrings may describe the boundary; code may not cross it
    hits = [t for t in FORBIDDEN if t in body]
    imports = sorted(set(re.findall(r"^\s*(?:from\s+(\S+)\s+import|import\s+([\w, .]+))", body, re.M)))
    v5[fn] = (hits, imports)
v5_ok = all(not h for h, _ in v5.values())
obs_src = re.sub(r'"""(.|\n)*?"""', "", open(os.path.join(HERE, "observer.py")).read())
own_only = "def observe(o, dec, own, mob)" in obs_src and "observe(o, dec.get(o, []), own.get(o, []), mob.get(o, {}))" in obs_src

lines = []
P = lines.append
P("Stage E E1 — G1 checks V1-V5, V7, V8 (V6 in e1_calibration_report.txt)")
P(f"runs: {runs}")
P("")
P(f"V5 static audit (no ground-truth token in code, docstrings excluded): {'PASS' if v5_ok and own_only else 'FAIL'}")
for fn, (hits, imps) in v5.items():
    P(f"   {fn}: forbidden tokens {hits if hits else 'none'}; imports {[a or b for a, b in imps]}")
P(f"   observe() receives only the observer's own decoded copies, own t records and own mobility rows: {own_only}")
P("")

tot = C.Counter(); xt = C.Counter(); v1_bad = v2_bad = 0
v3_err, v3_sep, v3_n = [], [], 0
v4 = C.Counter(); v4_max = 0.0
v7 = C.Counter(); v7_maxdiff = 0.0; v7_examples = []
v8 = C.Counter(); v8_max = 0.0
per_run = []
for run in runs:
    rd = f"{root}/run_{run}"
    T = Truth(rd, run)
    rc = C.Counter()
    seen_tx = set()
    for row in csv.DictReader(open(f"{rd}/e1_opportunities.csv")):
        o, x, u, s, p = (int(row[k]) for k in ("o", "x", "u", "s", "p"))
        out = row["out"]; g = T.gt(x, u, s, p)
        rc[out] += 1; xt[(out, g)] += 1
        if out == "MATCH" and g != "FWD_TX": v1_bad += 1
        if out == "OTHER-UP" and g != "DIFF_UP": v2_bad += 1
        if out in ("MATCH", "OTHER-UP"):
            dly = float(row["resp_t"]) - float(row["t0"])
            if out == "MATCH":
                v4["match"] += 1; v4_max = max(v4_max, dly)
                if dly > WINDOW: v4["match_after_8s"] += 1
                if dly < 0: v4["match_before_t0"] += 1
            else:
                v4["otherup"] += 1
                if dly > WINDOW: v4["otherup_after_8s"] += 1
                if dly < 0: v4["otherup_before_t0"] += 1
            if (x, s, p) not in seen_tx:             # V3 per unique responding transmission
                seen_tx.add((x, s, p))
                rec = tup(row["rec"]); up = T.dec[(x, s, p)]["up"]
                v3_n += 1
                v3_err.append(dist(rec, T.exact_f((up, s, p))))
                others = [dist(rec, T.exact_f((y, s, p))) for y in T.bypkt[(s, p)] if y not in (up, x)]
                if others: v3_sep.append(min(others))
    tot.update(rc)
    mal = len(T.malicious)
    drops = sum(1 for v in T.dec.values() if v["act"] == "DROP")
    per_run.append((run, dict(rc), sum(rc.values()), mal, drops))
    # ---------- V7: first CCQ computation per (observer, neighbour) has history 1 -> CCQ = p(d) ----------
    calls = C.Counter()
    for kind, cur, nb, val, pdist in T.ccq_lines:
        if cur is None:
            v7["unattributed"] += 1; continue
        obs, ctx, ct, cf = cur
        key = (obs, nb); calls[key] += 1
        if calls[key] != 1 or nb == obs:
            continue
        if kind == "first-hear":
            if ctx != nb or cf is None:
                v7["attribution_mismatch"] += 1; continue
            if abs(ct - round(ct)) < 1e-9:
                v7["skipped_whole_second"] += 1; continue
            d = dist(T.mob[obs][int(math.floor(ct))], cf)
            pv = p_success(d, EBN0_CPP)
            diff = abs(val - pv)
            ok = diff <= res6(pv) + 1e-12
        else:
            lo, hi = p_success(pdist + res6(pdist), EBN0_CPP), p_success(max(0.0, pdist - res6(pdist)), EBN0_CPP)
            diff = 0.0 if lo - res6(lo) <= val <= hi + res6(hi) else min(abs(val - lo), abs(val - hi))
            ok = diff == 0.0
        v7["checked_" + kind] += 1
        v7_maxdiff = max(v7_maxdiff, diff)
        if not ok:
            v7["mismatch"] += 1
            if len(v7_examples) < 5: v7_examples.append((run, obs, nb, val, pv if kind == "first-hear" else pdist))
    # ---------- V8: own t-record f vs receivers' decoded f ----------
    for key, (t0, f) in T.tx.items():
        rx = T.rxf.get(key)
        if not rx:
            v8["not_decoded_by_anyone"] += 1; continue
        v8["transmissions"] += 1
        if len(rx) > 1: v8["receivers_disagree"] += 1
        for fr in rx:
            md = max(abs(a - b) for a, b in zip(f, fr)); v8_max = max(v8_max, md)
            if any(abs(a - b) > res6(a) + 1e-9 for a, b in zip(f, fr)): v8["beyond_print_resolution"] += 1

P("Per run: opportunities by outcome; configured malicious nodes; ground-truth DROP decisions")
for run, rc, n, mal, drops in per_run:
    P(f"   run {run}: {n} {rc}; malicious {mal}; drops {drops}")
P(f"   pooled: {sum(tot.values())} {dict(tot)}")
P("")
P("Outcome x ground truth (pooled):")
for out in ("MATCH", "OTHER-UP", "SILENT"):
    P(f"   {out:9s} " + "  ".join(f"{g}={xt[(out, g)]}" for g in GTS if xt[(out, g)]))
P("")
v1_ok, v2_ok = v1_bad == 0, v2_bad == 0
P(f"V1 MATCH = 100% FWD_TX: {'PASS' if v1_ok else 'FAIL'} (exceptions {v1_bad} of {tot['MATCH']})")
P(f"V2 OTHER-UP = 100% DIFF_UP: {'PASS' if v2_ok else 'FAIL'} (exceptions {v2_bad} of {tot['OTHER-UP']})")
v3_err.sort(); v3_sep.sort()
v3_ok = v3_err[-1] <= EPS / 2 and v3_sep[0] >= 2 * EPS
P(f"V3 upstream recovery over {v3_n} unique responding transmissions: max error {v3_err[-1]:.4f} m (<= 12.5), "
  f"median {v3_err[len(v3_err)//2]:.4f} m; min separation to another transmitter of the packet {v3_sep[0]:.1f} m (>= 50): "
  f"{'PASS' if v3_ok else 'FAIL'}")
v4_ok = v4["match_after_8s"] == 0
P(f"V4 MATCH responses after t0 + 8 s: {v4['match_after_8s']} of {v4['match']} (max delay {v4_max:.3f} s; before t0: "
  f"{v4['match_before_t0']}): {'PASS' if v4_ok else 'FAIL'}")
P(f"   (information only) OTHER-UP responses: {v4['otherup']}; after t0 + 8 s {v4['otherup_after_8s']}; before t0 "
  f"{v4['otherup_before_t0']} — a response to a different upstream copy has no timing relation to t0")
v7_ok = v7["mismatch"] == 0 and v7["attribution_mismatch"] == 0 and (v7["checked_first-hear"] + v7["checked_envscore"]) > 0
P(f"V7 offline p(d) (Eb/N0 40 dB, as compiled) vs C++ CCQ on the first computation per (observer, neighbour): "
  f"{'PASS' if v7_ok else 'FAIL'}; {dict(v7)}; max |diff| {v7_maxdiff:.2e}")
if v7_examples: P(f"   mismatch examples (run, obs, nb, C++ value, offline/printed-dist): {v7_examples}")
v8_ok = v8["beyond_print_resolution"] == 0 and v8["receivers_disagree"] == 0
P(f"V8 own t-record f vs receivers' [RXHDR] f: {'PASS' if v8_ok else 'FAIL'}; {dict(v8)}; max component diff {v8_max:.4f} m")
P("")
P(f"V1-V5, V7, V8 all pass: {all([v1_ok, v2_ok, v3_ok, v4_ok, v5_ok and own_only, v7_ok, v8_ok])}")
open(os.path.join(HERE, "e1_validation.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
