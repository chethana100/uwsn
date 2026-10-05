#!/usr/bin/env python3
"""Stage E E1 — REVISION 4 G1 summary (frozen spec ../README.md §12; commit 8a0ff2f). Evaluation code.
- V1, V2, V4, V7, V8: unchanged by revision 4; carried from the revision-2 e1_validation.txt.
- V3-a: unchanged by revision 4; carried from the revision-3 e1_validation_rev3.txt.
  Both are carried only after verifying by md5 that those files, their validators and the inputs are unchanged.
- V5: static audit re-run over observer.py, geom.py, calibrate.py, calibrate_rev3.py and calibrate_rev4.py
  (the revision-4 calibration script is audited in addition to the revision-3 one).
- V6 = V6-A and V6-B, read from e1_calibration_rev4.json (development/recalibration validation).
Writes e1_validation_rev4.txt (refuses to overwrite). Runs no simulation; reads no attacker data.

usage: e1_validate_rev4.py <E1 run root> <run> [<run> ...] [--out TXT]
"""
import sys, os, re, json, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
out = os.path.join(HERE, "e1_validation_rev4.txt")
if "--out" in args:
    i = args.index("--out"); out = args[i + 1]; del args[i:i + 2]
root, runs = args[0], [int(a) for a in args[1:]]
if os.path.exists(out):
    raise SystemExit(f"{out} exists; refusing to overwrite")
HIST = {"e1_validation.txt": "fc56479f83fd740bf4be7a880530263f", "e1_validate.py": "6890525558534976331dbbfb1ba65cb5",
        "e1_validation_rev3.txt": "8b67d376761e067c99fa8c120f9441c4", "e1_validate_rev3.py": "5537043236adf8f9519991e6ef6dadc2",
        "observer.py": "45d79f770c13f151bddee86b09bf96f6", "geom.py": "413d4f60b4efcdb125bf00c65d792e09",
        "truth.py": "203dbb7046bb1ad4323fdc222dfbacc8", "calibrate.py": "17b4b39af32b64cbb7eaaeb003216069",
        "calibrate_rev3.py": "03a6ff9cb9b4bcfbc4dd6423b78aaa48", "e1_calibration.json": "6504d1df09d5daaeef4e835611e424d4",
        "e1_calibration_rev3.json": "f49e6f764088bd500ef302dc01a281c1"}


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


L = []; W = L.append
W("Stage E E1 — REVISION 4 G1 summary (frozen spec ../README.md §12, commit 8a0ff2f)")
W("Re-evaluation of the existing E1 outputs; no simulation rerun; no attacker data.")
W("")
prov = {f: md5(os.path.join(HERE, f)) == h for f, h in HIST.items()}
cal2 = json.load(open(os.path.join(HERE, "e1_calibration.json")))
inputs_ok = all(md5(f"{root}/run_{r}/e1_opportunities.csv") == cal2["inputs_md5"][str(r)]["e1_opportunities.csv"] for r in runs)
carry_ok = all(prov.values()) and inputs_ok
W(f"Historical revision-2/3 files unchanged (md5): {all(prov.values())} {[f for f, ok in prov.items() if not ok] or ''}; "
  f"opportunity inputs identical to E-32: {inputs_ok}")
rev2 = open(os.path.join(HERE, "e1_validation.txt")).read(); rev3 = open(os.path.join(HERE, "e1_validation_rev3.txt")).read()
carried = {}
for v in ("V1", "V2", "V4", "V7", "V8"):
    m = re.search(rf"^{v} .*?: (PASS|FAIL)", rev2, re.M); carried[v] = m.group(1) if (m and carry_ok) else "NOT CARRIED"
m = re.search(r"^V3-a .*?: (PASS|FAIL)", rev3, re.M); carried["V3-a"] = m.group(1) if (m and carry_ok) else "NOT CARRIED"
W("Carried (unchanged by revision 4): " + str(carried))
W("")
FORBIDDEN = ["[DECISION]", "[HOLD]", "[VERDICT]", "[OBSERVER]", "[EAQTE", "[SSCCQ]", "[EE]", "custody", "Custody",
             "malicious", "_meta", "truth", "d_common", "act=", "trust.csv", "observed.csv"]
v5 = True
W("V5 static audit (forbidden ground-truth tokens in code, docstrings excluded; imports):")
for fn in ["observer.py", "geom.py", "calibrate.py", "calibrate_rev3.py", "calibrate_rev4.py"]:
    body = re.sub(r'"""(.|\n)*?"""', "", open(os.path.join(HERE, fn)).read())
    hits = [t for t in FORBIDDEN if t in body]
    imps = sorted({a or b for a, b in re.findall(r"^\s*(?:from\s+(\S+)\s+import|import\s+([\w, .]+))", body, re.M)})
    bad = [i for i in imps if re.search(r"\b(truth|e1_validate\w*|d_common|test_rev4)\b", i)]
    ok = not hits and not bad; v5 &= ok
    W(f"   {fn}: {'clean' if ok else 'VIOLATION'}; tokens {hits or 'none'}; imports {imps}")
obs = re.sub(r'"""(.|\n)*?"""', "", open(os.path.join(HERE, "observer.py")).read())
own_only = "def observe(o, dec, own, mob)" in obs and "observe(o, dec.get(o, []), own.get(o, []), mob.get(o, {}))" in obs
importers = [f for f in os.listdir(HERE) if f.endswith(".py") and f != "e1_validate_rev4.py"
             and re.search(r"^\s*(from|import)\s+e1_validate_rev4\b", open(os.path.join(HERE, f)).read(), re.M)]
v5 = v5 and own_only and prov["observer.py"] and prov["geom.py"] and not importers
W(f"   observe() boundary intact: {own_only}; observer.py/geom.py unchanged: {prov['observer.py']}/{prov['geom.py']}; "
  f"modules importing this validator: {importers or 'none'}")
W(f"V5: {'PASS' if v5 else 'FAIL'}")
W("")
cal4 = json.load(open(os.path.join(HERE, "e1_calibration_rev4.json")))
v6 = cal4["V6"]; a, b = v6["V6A"], v6["V6B"]
W(f"V6 (development/recalibration validation; independent FA assessment = G2b on sealed seeds 2-11):")
W(f"   V6-A false-alarm transfer: pooled FA {a['pooled_flagged']}/{a['pooled_pairs']} = {a['pooled_fa']:.4f}, one-sided lower bound "
  f"{a['lower95_one_sided']:.4f}: {'PASS' if a['pass'] else 'FAIL'}")
undefined = [f["seed"] for f in v6["folds"] if f.get("n_min") is None]
W(f"   V6-B power feasibility: full-calibration n_min {cal4['n_min']}; folds with undefined n_min {undefined or 'none'}: {'PASS' if b['pass'] else 'FAIL'}")
W(f"   V6: {'PASS' if v6['pass'] else 'FAIL'}")
W("")
checks = {"V1": carried["V1"] == "PASS", "V2": carried["V2"] == "PASS", "V3-a": carried["V3-a"] == "PASS", "V4": carried["V4"] == "PASS",
          "V5": v5, "V6-A": bool(a["pass"]), "V6-B": bool(b["pass"]), "V7": carried["V7"] == "PASS", "V8": carried["V8"] == "PASS"}
W("G1 summary: " + ", ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in checks.items()))
g1 = all(checks.values())
W(f"G1 (revision 4): {'PASS' if g1 else 'FAIL'}")
if not b["pass"]:
    W("D4-5 stop rule applies: revision 4 failed V6-B -> stop and open the separately scoped Option C discussion; no further redesign aimed only at 0.80 power.")
W("Power claims, if any, are Arm-A only; no calibrated power claim for Arms B/C. Seeds 2-11 remain sealed unless G1 passes.")
open(out, "w").write("\n".join(L) + "\n")
print("\n".join(L))
