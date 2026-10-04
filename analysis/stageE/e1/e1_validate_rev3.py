#!/usr/bin/env python3
"""Stage E E1 — REVISION 3 validation (frozen spec ../README.md §12; commit e9ddf04). EVALUATION code.
- V3-a: recovery error <= 12.5 m and minimum separation > eps + 12.5 m = 37.5 m (same quantity as revision-2 V3);
  separations below 2*eps = 50 m are listed descriptively.
- V5 (extended): forbidden-token audit of observer.py, geom.py, calibrate.py and calibrate_rev3.py, plus an import
  audit (observer/calibration code never imports truth.py or any validator). This validator is evaluation code and
  may import truth.py; nothing imports it.
- V1, V2, V4, V7, V8 are unchanged by revision 3 (README §13 R3-5): taken from the revision-2 e1_validation.txt after
  verifying by md5 that it, its validator and its inputs are unchanged.
- V6: read from e1_calibration_rev3.json (development/recalibration validation).
Writes e1_validation_rev3.txt. Runs no simulation; reads no attacker data.

usage: e1_validate_rev3.py <E1 run root> <run> [<run> ...]
"""
import sys, os, re, csv, json, hashlib, collections as C
from geom import dist, EPS
from truth import Truth

HERE = os.path.dirname(os.path.abspath(__file__))
root, runs = sys.argv[1], [int(a) for a in sys.argv[2:]]
E_BOUND, SEP_MIN, SEP_REPORT = 12.5, EPS + 12.5, 2 * EPS
REV2 = {"e1_validation.txt": "fc56479f83fd740bf4be7a880530263f", "e1_validate.py": "6890525558534976331dbbfb1ba65cb5",
        "observer.py": "45d79f770c13f151bddee86b09bf96f6", "geom.py": "413d4f60b4efcdb125bf00c65d792e09",
        "truth.py": "203dbb7046bb1ad4323fdc222dfbacc8", "e1_calibration.json": "6504d1df09d5daaeef4e835611e424d4"}


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


L = []; W = L.append
W("Stage E E1 — REVISION 3 validation (G1 checks; frozen spec ../README.md §12, commit e9ddf04)")
W("Re-evaluation of the existing E1 outputs; no simulation rerun; no attacker data.")
W("")
# ---------- provenance of carried-over results ----------
prov = {f: md5(os.path.join(HERE, f)) == h for f, h in REV2.items()}
cal2 = json.load(open(os.path.join(HERE, "e1_calibration.json")))
inputs_ok = all(md5(f"{root}/run_{r}/e1_opportunities.csv") == cal2["inputs_md5"][str(r)]["e1_opportunities.csv"] for r in runs)
carry_ok = all(prov.values()) and inputs_ok
W(f"Revision-2 files unchanged (md5): {prov}; opportunity inputs identical to the revision-2 run: {inputs_ok}")
rev2 = open(os.path.join(HERE, "e1_validation.txt")).read()
carried = {}
for v in ("V1", "V2", "V4", "V7", "V8"):
    m = re.search(rf"^{v} .*?: (PASS|FAIL)", rev2, re.M)
    carried[v] = m.group(1) if (m and carry_ok) else "NOT CARRIED"
W("V1, V2, V4, V7, V8 (unchanged by revision 3; carried from revision-2 e1_validation.txt): " + str(carried))
W("")
# ---------- V3-a ----------
errs, seps, close, n_unique = [], [], [], 0
for run in runs:
    T = Truth(f"{root}/run_{run}", run); seen = set()
    for row in csv.DictReader(open(f"{root}/run_{run}/e1_opportunities.csv")):
        if row["out"] not in ("MATCH", "OTHER-UP"):
            continue
        x, s, p = int(row["x"]), int(row["s"]), int(row["p"])
        if (x, s, p) in seen:
            continue
        seen.add((x, s, p)); n_unique += 1
        rec = tuple(float(v) for v in row["rec"].split(":")); up = T.dec[(x, s, p)]["up"]
        errs.append(dist(rec, T.exact_f((up, s, p))))
        others = [(dist(rec, T.exact_f((y, s, p))), y) for y in T.bypkt[(s, p)] if y not in (up, x)]
        if others:
            sp, y = min(others); seps.append(sp)
            if sp < SEP_REPORT:
                close.append((run, x, s, p, up, y, round(sp, 1)))
errs.sort(); seps.sort()
v3_ok = errs[-1] <= E_BOUND and seps[0] > SEP_MIN
W(f"V3-a over {n_unique} unique responding transmissions: max recovery error {errs[-1]:.4f} m (<= {E_BOUND}); "
  f"minimum separation {seps[0]:.1f} m (> {SEP_MIN}): {'PASS' if v3_ok else 'FAIL'}")
W(f"   descriptive: separations < {SEP_REPORT:.0f} m: {len(close)} (run, X, src, pk, true upstream, nearby transmitter, separation m):")
for c in close:
    W(f"      {c}")
W("")
# ---------- V5 extended ----------
FORBIDDEN = ["[DECISION]", "[HOLD]", "[VERDICT]", "[OBSERVER]", "[EAQTE", "[SSCCQ]", "[EE]", "custody", "Custody",
             "malicious", "_meta", "truth", "d_common", "act=", "trust.csv", "observed.csv"]
AUDITED = ["observer.py", "geom.py", "calibrate.py", "calibrate_rev3.py"]
v5_ok = True
W("V5 (extended to the revision-3 calibration script) — forbidden tokens in code (docstrings excluded) and imports:")
for fn in AUDITED:
    body = re.sub(r'"""(.|\n)*?"""', "", open(os.path.join(HERE, fn)).read())
    hits = [t for t in FORBIDDEN if t in body]
    imps = sorted({a or b for a, b in re.findall(r"^\s*(?:from\s+(\S+)\s+import|import\s+([\w, .]+))", body, re.M)})
    bad_imp = [i for i in imps if re.search(r"\b(truth|e1_validate\w*|d_common)\b", i)]
    ok = not hits and not bad_imp
    v5_ok &= ok
    W(f"   {fn}: {'clean' if ok else 'VIOLATION'}; forbidden tokens {hits or 'none'}; imports {imps}")
obs = re.sub(r'"""(.|\n)*?"""', "", open(os.path.join(HERE, "observer.py")).read())
own_only = "def observe(o, dec, own, mob)" in obs and "observe(o, dec.get(o, []), own.get(o, []), mob.get(o, {}))" in obs
v5_ok &= own_only and prov.get("observer.py", False) and prov.get("geom.py", False)
importers = [f for f in os.listdir(HERE) if f.endswith(".py") and f != "e1_validate_rev3.py"
             and re.search(r"^\s*(from|import)\s+e1_validate_rev3\b", open(os.path.join(HERE, f)).read(), re.M)]
W(f"   observe() receives only the observer's own decoded copies, own t records and own mobility rows: {own_only}")
W(f"   observer.py and geom.py unchanged since revision 2 (O1 boundary intact): {prov.get('observer.py')} / {prov.get('geom.py')}")
W(f"   e1_validate_rev3.py is evaluation code (imports truth.py for V3-a); modules importing it: {importers or 'none'}")
W(f"V5: {'PASS' if v5_ok and not importers else 'FAIL'}")
v5_ok = v5_ok and not importers
W("")
# ---------- V6 from the revision-3 calibration ----------
cal3 = json.load(open(os.path.join(HERE, "e1_calibration_rev3.json")))
v6 = cal3["V6"]
W(f"V6 (development/recalibration validation; independent FA assessment = G2b on seeds 2-11): pooled FA "
  f"{v6['pooled_flagged']}/{v6['pooled_judged']}" + (f" = {v6['pooled_fa']:.4f}" if v6["pooled_fa"] is not None else "")
  + (f", one-sided lower bound {v6['lower95_one_sided']:.4f}" if v6["lower95_one_sided"] is not None else "")
  + f"; all folds evaluable {v6['all_folds_evaluable']}: {'PASS' if v6['pass'] else 'FAIL'}")
nmin_ok = cal3["n_min"] is not None
W(f"n_min: {cal3['n_min'] if nmin_ok else 'UNDEFINED (no bin reaches power 0.80) -> G1 fails by §7 step 4'}")
W("")
checks = {"V1": carried["V1"] == "PASS", "V2": carried["V2"] == "PASS", "V3-a": v3_ok, "V4": carried["V4"] == "PASS",
          "V5": v5_ok, "V6": bool(v6["pass"]), "V7": carried["V7"] == "PASS", "V8": carried["V8"] == "PASS", "n_min defined": nmin_ok}
W("G1 summary: " + ", ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in checks.items()))
W(f"G1 (revision 3): {'PASS' if all(checks.values()) else 'FAIL'}")
out = os.path.join(HERE, "e1_validation_rev3.txt")
if os.path.exists(out):
    raise SystemExit("e1_validation_rev3.txt already exists; refusing to overwrite")
open(out, "w").write("\n".join(L) + "\n")
print("\n".join(L))
