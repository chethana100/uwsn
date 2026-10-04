"""Stage E — EVALUATION-ONLY ground truth (frozen spec rev 2, ../README.md §5).
Never imported by observer.py or calibrate.py (V5 audits this)."""
import re, csv, collections as C
from observer import load_inputs, KV, vec

GTS = ["FWD_TX", "MAC_GIVEUP", "DROP", "SUPPRESS", "INELIG", "MAXNBR", "OUTPIPE", "DIFF_UP", "NORX"]


class Truth:
    def __init__(self, rundir, run):
        meta = list(csv.reader(open(f"{rundir}/v1_{run}_meta.csv")))
        m = dict(zip(meta[0], meta[1]))
        self.malicious = {int(x) + 1 for x in m["malicious_nodes"].split()} if m.get("malicious_nodes") else set()
        self.dec = {}
        self.ccq_lines = []                     # (kind, observer, neighbour, value, printed dist or None, rx t, rx f)
        cur = None                              # (observer, tx, t, f) of the Recv call currently being logged
        for ln in open(f"{rundir}/stderr.log", errors="ignore"):
            if ln.startswith("[DECISION] "):
                k = dict(KV.findall(ln))
                self.dec[(int(k["node"]), int(k["src"]), int(k["pk"]))] = {"act": k["act"], "up": int(k["up"]), "t": float(k["t"])}
            elif ln.startswith("[RXHDR] "):
                k = dict(KV.findall(ln))
                cur = (int(k["node"]), int(k["tx"]), float(k["t"]), vec(k["f"]))
            elif ln.startswith("[EAQTE] TX "):
                k = dict(KV.findall(ln))
                cur = (int(k["src"]), int(k["src"]), float(k["t"]), None)   # origination Recv at the source itself
            elif ln.startswith("[EAQTE-CCQ] "):
                k = dict(KV.findall(ln))
                self.ccq_lines.append(("first-hear", cur, int(k["neighbor"]), float(k["CCQ"]), None))
            elif ln.startswith("[SSCCQ] "):
                k = dict(KV.findall(ln))
                self.ccq_lines.append(("envscore", cur, int(k["node"]), float(k["ccq"]), float(k["dist"])))
        dec_in, own, mob = load_inputs(rundir, run)
        self.mob = mob
        self.tx = {}                            # (node, src, pk) -> own t-record (t0, f)
        for node, lst in own.items():
            for (t0, s, p, f) in lst:
                self.tx[(node, s, p)] = (t0, f)
        self.rxf = C.defaultdict(set)           # (tx, src, pk) -> set of decoded f at receivers
        for node, lst in dec_in.items():
            for (t, tx, s, p, f, d, tgt) in lst:
                self.rxf[(tx, s, p)].add(f)
        self.bypkt = C.defaultdict(list)
        for (node, s, p) in self.tx:
            self.bypkt[(s, p)].append(node)

    def exact_f(self, key):                     # exact header f of a transmission (decoded at a receiver), else t record
        v = self.rxf.get(key)
        return next(iter(v)) if v else self.tx[key][1]

    def gt(self, x, u, s, p):
        v = self.dec.get((x, s, p))
        if v is None:
            return "NORX"
        if v["up"] != u:
            return "DIFF_UP"
        if v["act"] == "FWD":
            return "FWD_TX" if (x, s, p) in self.tx else "MAC_GIVEUP"
        return v["act"]
