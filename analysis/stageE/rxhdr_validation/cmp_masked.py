# Record-wise trace comparison with a configurable set of masked VBHeader fields; counts which fields differ.
import sys, re
from itertools import zip_longest
a, b = sys.argv[1], sys.argv[2]
FIELDS = ["token", "ts", "range"]
pats = {f: re.compile(r" %s=(\S+)" % f) for f in FIELDS}
def records(p):
    rec = []
    with open(p, errors="ignore") as fh:
        for ln in fh:
            if ln[:2] in ("t ", "r ", "d ") and rec:
                yield "".join(rec); rec = []
            rec.append(ln)
    if rec: yield "".join(rec)
n = 0; diff_field = {f: 0 for f in FIELDS}; other = 0; first_other = None
for x, y in zip_longest(records(a), records(b)):
    n += 1
    if x is None or y is None:
        other += 1; first_other = first_other or n; continue
    for f in FIELDS:
        if pats[f].findall(x) != pats[f].findall(y): diff_field[f] += 1
    mx, my = x, y
    for f in FIELDS: mx = pats[f].sub(" %s=X" % f, mx); my = pats[f].sub(" %s=X" % f, my)
    if mx != my:
        other += 1
        if first_other is None: first_other = n; fx, fy = mx, my
print(f"records={n}  records where field differs: {diff_field}  records differing after masking token/ts/range: {other}" + (f" first at {first_other}" if first_other else ""))
