#!/usr/bin/env python3
"""Compare two run directories. usage: cmp_runs.py A B [--mask range] [--mask dataType]
Trace records are compared after masking ONLY the named header fields; reports the first divergence."""
import sys, re, hashlib, csv
a, b = sys.argv[1], sys.argv[2]
masks = [sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == "--mask"]
pat = []
if "range" in masks:    pat.append((re.compile(r" range=\S+"), " range=X"))
if "dataType" in masks: pat.append((re.compile(r"dataType=.*? originalSource="), "dataType=X originalSource="))
def mask(s):
    for p, r in pat: s = p.sub(r, s)
    return s
def md5(p): return hashlib.md5(open(p, "rb").read()).hexdigest()
for f in ["v1_1_energy.csv", "v1_1_mobility.csv", "v1_1_trust.csv", "v1_1_observed.csv", "stdout.log", "stderr.log"]:
    print(f"  {'IDENTICAL' if md5(f'{a}/{f}') == md5(f'{b}/{f}') else 'DIFFERENT'}  {f}")
ma, mb = list(csv.reader(open(f"{a}/v1_1_meta.csv"))), list(csv.reader(open(f"{b}/v1_1_meta.csv")))
diffcols = [h for h, x, y in zip(ma[0], ma[1], mb[1]) if x != y]
print(f"  meta: differing columns = {diffcols if diffcols else 'none'}")
# trace: record-wise
def records(p):
    rec = []
    with open(p, errors="ignore") as fh:
        for ln in fh:
            if ln[:2] in ("t ", "r ", "d ") and rec:
                yield "".join(rec); rec = []
            rec.append(ln)
    if rec: yield "".join(rec)
n = 0; first = None; cnt = {"t": 0, "r": 0}
from itertools import zip_longest
for x, y in zip_longest(records(f"{a}/v1_1.tr"), records(f"{b}/v1_1.tr")):
    n += 1
    if x is None or y is None or mask(x) != mask(y):
        first = (n, x, y); break
    cnt[x[0]] = cnt.get(x[0], 0) + 1
if first is None:
    print(f"  IDENTICAL  v1_1.tr after masking {masks or 'nothing'} ({n} records: {cnt['t']} t, {cnt['r']} r)")
else:
    k, x, y = first
    print(f"  DIFFERENT  v1_1.tr: first divergence at record {k} (masks {masks})")
    print("   A:", (x or "<end>")[:600]); print("   B:", (y or "<end>")[:600])
