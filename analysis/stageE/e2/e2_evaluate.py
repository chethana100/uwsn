#!/usr/bin/env python3
"""Stage E E2 — held-out Arm-A evaluation (frozen ../E2_SPEC.md, commit a87ffbc; D-20). Evaluation code.

Implements E2_SPEC.md E2-4 to E2-10 and E2-14 exactly; nothing is recalibrated:
- E2-4  r = (K - E)/n per pair (seed, O, X) over MATCH and SILENT, q_s from the frozen revision-4 JSON;
        judged iff n >= n_ref = 14; bin [L_b, L_b+1); flagged iff r > tau_A,b; n > n_max reported separately.
- E2-5  labels: malicious from truth.py (meta); active = at least one "[DECISION] ... act=DROP" line for X
        in the run (literal scan, cross-checked against truth.py; any disagreement stops the evaluation).
- E2-6  H = judged honest pairs, D = judged active-malicious pairs (p = 0.75 runs; every observer O kept;
        inactive-malicious pairs excluded); FA, TDR, Mann-Whitney AUC (ties 1/2).
- E2-7  G2: |D| >= 43 and >= 10 distinct (seed, X) in D.
- E2-8  cluster bootstrap: seeds, then X nodes within seeds, with occurrence-specific node draws; the
        multiplicity of (seed, X) is the sum of X's counts over all occurrences of that seed; B = 10,000,
        NumPy PCG64(12345); zero denominators -> FA* = 1, TDR* = 0, AUC* = 0 (never discarded);
        numpy.percentile with linear interpolation.
- E2-9  G2b items 1-3; E2-10 ceiling tables (p = 1.0 the ceiling; p = 0.75 descriptive); E2-14 outcome.
Reads only: the frozen calibration JSON, the E2 run directories, and the unchanged e1 helpers.
Writes <out>/e2_results.json and <out>/e2_report.txt and refuses to overwrite either.

usage:
  e2_evaluate.py --p075 ROOT --p100 ROOT [--out DIR]                        E2 (seeds 2-11; ROOT/run_N)
  e2_evaluate.py --dev --seeds 1 --p075 ROOT --p100 ROOT --out DIR          development only (never E2)
"""
import sys, os, csv, json, hashlib, subprocess, datetime, platform, collections as C
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE_E = os.path.dirname(HERE)
E1 = os.path.join(STAGE_E, "e1")
REPO = os.path.abspath(os.path.join(STAGE_E, "..", ".."))
sys.dont_write_bytecode = True                   # never leave caches next to the frozen e1 helpers
sys.path.insert(0, E1)
from calibrate import load, name, CELLS          # revision-2 opportunity loader and cell names, unchanged
from calibrate_rev3 import bin_of                # revision-3 bin assignment, unchanged
from calibrate_rev4 import arm_a_pairs           # revision-4 Arm-A pair statistic, unchanged
from truth import Truth                          # evaluation-only ground truth, unchanged
from observer import KV                          # key=value parser used by truth.py, unchanged

# ---------------------------------------------------------------- frozen constants (E2_SPEC.md) ----------
SEEDS_E2 = tuple(range(2, 12))                   # E2-1
P_SETS = (("p075", 0.75), ("p100", 1.0))         # E2-1: p075 feeds G2/G2b; p100 feeds the ceiling table only
N_REF = 14                                       # E2-4 (C-d J1)
FA_BAR, AUC_BAR, AUC_NULL = 0.05, 0.70, 0.5      # E2-9
G2_MIN_PAIRS, G2_MIN_NODES = 43, 10              # E2-7
B_BOOT, BOOT_SEED = 10000, 12345                 # E2-8
PCT = {"fa_lb": 5.0, "fa_ub": 97.5, "tdr_lb": 2.5, "auc_lb": 2.5}   # E2-9 (linear interpolation)
FROZEN_MD5 = {                                   # inputs this evaluator depends on (E2-3, E2-4, E2-5, E2-13)
    "analysis/stageE/E2_SPEC.md": "7f37d81dbc8cc4b823c2036e80190960",
    "analysis/stageE/e1/e1_calibration_rev4.json": "0ca88a0e4c8fc56f63e6b44b496b65fd",
    "analysis/stageE/e1/observer.py": "45d79f770c13f151bddee86b09bf96f6",
    "analysis/stageE/e1/geom.py": "413d4f60b4efcdb125bf00c65d792e09",
    "analysis/stageE/e1/truth.py": "203dbb7046bb1ad4323fdc222dfbacc8",
    "analysis/stageE/e1/calibrate.py": "17b4b39af32b64cbb7eaaeb003216069",
    "analysis/stageE/e1/calibrate_rev3.py": "03a6ff9cb9b4bcfbc4dd6423b78aaa48",
    "analysis/stageE/e1/calibrate_rev4.py": "830a3733f378fb04a4680e43d0c60cf6"}
BUILD_MD5 = {                                    # E2-2
    "build/lib/libns3.41-aqua-sim-ng-default.so": "871c50fc90cc613513ce25211cc8e450",
    "build/scratch/ns3.41-uwsn-trustq-attack-default": "54e444ed2ade8baf1c5fc3f54be5ad36"}
EXPECTED_META = {                                # E2-2 settings as recorded in _meta.csv (numeric fields compared as floats)
    "attacker_fraction": 0.2, "attack_start": 0.0, "attack_mode": 0.0, "priority_scale": 0.0,
    "observed_trust_weight": 0.0, "pact_enabled": 0.0, "paper_hold_time": 1.0, "paper_desirableness": 1.0,
    "hop_by_hop": 1.0, "width": 400.0, "stream_base": 1000.0,
    "propagation": "ns3::AquaSimRangePropagation", "routing": "ns3::AquaSimTrustQVBF",
    "sink_mobility": "ns3::ConstantPositionMobilityModel", "rx_range_m_env": "unset", "eaqte_xi_env": "unset"}
CONCLUSION_G2 = ("With overhearing-only evidence in beaconless HH-VBF, the attacker is not observable often enough "
                 "to evaluate trust.")
CONCLUSION_G2B = ("Oracle-free overhearing evidence does not separate droppers from honest nodes at the declared "
                  "false-alarm rate.")


class Stop(Exception):
    """A frozen precondition failed: the evaluation stops and reports; no gate is interpreted."""


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- E2-4: frozen calibration and pairs ------
def frozen_calibration(path):
    cal = json.load(open(path))
    lab = {c: cal["merge_map"][name(c)] for c in CELLS}
    q = {l: cal["strata"][l]["q"] for l in sorted(set(lab.values()))}
    L, tau = list(cal["edges_L"]), list(cal["tau_A_b"])
    if cal["n_ref"] != N_REF or L[0] != N_REF or len(L) != len(tau):
        raise Stop(f"frozen calibration inconsistent: n_ref {cal['n_ref']}, L {L}, {len(tau)} thresholds")
    return {"lab": lab, "q": q, "L": L, "tau": tau, "n_ref": cal["n_ref"], "n_max": cal["n_max"]}


def judge_pairs(root, seed, cal):
    """Arm-A pairs of one run: (seed, O, X) -> n, K, E, r, judged, bin (1-based), flagged."""
    out = {}
    for key, p in arm_a_pairs(load(root, [seed]), cal["lab"], cal["q"]).items():
        b = bin_of(p["n"], cal["L"])
        judged = p["n"] >= cal["n_ref"]
        if judged != (b is not None):
            raise Stop(f"judging and binning disagree for pair {key}")
        out[key] = {"n": p["n"], "K": p["K"], "E": p["E"], "r": p["r"], "judged": judged,
                    "bin": None if b is None else b + 1, "flag": bool(judged and p["r"] > cal["tau"][b])}
    return out


# ---------------------------------------------------------------- E2-5: labels ----------------------------
def ground_truth(rundir, seed):
    T = Truth(rundir, seed)
    drops, sink = set(), set()
    with open(f"{rundir}/stderr.log", errors="ignore") as fh:
        for ln in fh:
            if ln.startswith("[DECISION] "):
                k = dict(KV.findall(ln))
                if k.get("act") == "DROP":
                    drops.add((int(k["node"]), int(k["src"]), int(k["pk"])))
                elif k.get("act") == "SINK":
                    sink.add(int(k["node"]))
    via_truth = {key for key, v in T.dec.items() if v["act"] == "DROP"}
    mal = set(T.malicious)
    active = {x for x, _, _ in drops}
    problems = []
    if via_truth != drops:
        problems.append(f"DROP set differs between the literal scan ({len(drops)}) and truth.py ({len(via_truth)})")
    if not active <= mal:
        problems.append(f"DROP by non-malicious nodes {sorted(active - mal)}")
    if len(sink) != 1 or sink & mal:
        problems.append(f"sink not uniquely identified or malicious: {sorted(sink)}")
    if problems:
        raise Stop(f"run {rundir}: " + "; ".join(problems))
    return {"malicious": mal, "active": active, "drops": drops, "sink": sink.pop(), "nodes": set(T.mob)}


def check_meta(rundir, seed, p):
    r = list(csv.reader(open(f"{rundir}/v1_{seed}_meta.csv")))
    m = dict(zip(r[0], r[1]))
    want = dict(EXPECTED_META, run=float(seed), drop_probability=p)
    bad = {}
    for k, v in want.items():
        got = m.get(k)
        try:
            ok = got is not None and ((float(got) == v) if isinstance(v, float) else got == v)
        except ValueError:
            ok = False
        if not ok:
            bad[k] = (got, v)
    if bad:
        raise Stop(f"run {rundir}: _meta.csv differs from E2-2: {bad}")
    return {"num_malicious": int(m["num_malicious"]), "malicious_nodes_meta": m["malicious_nodes"]}


def opportunity_rows(rundir):
    """(x, s, p, k1) of every MATCH or SILENT opportunity (ceiling table; OTHER-UP never counts)."""
    rows = []
    for r in csv.DictReader(open(f"{rundir}/e1_opportunities.csv")):
        if r["out"] in ("MATCH", "SILENT"):
            rows.append((int(r["x"]), int(r["s"]), int(r["p"]), int(r["k1"])))
    return rows


# ---------------------------------------------------------------- E2-6: point statistics ------------------
class AUCIndex:
    """Weighted Mann-Whitney AUC with ties counted 1/2:
    AUC = sum_{i in D} sum_{j in H} m_i m_j [1(r_i > r_j) + 1/2 1(r_i = r_j)] / (sum_D m * sum_H m).
    The H scores are sorted once; per call only cumulative weights are formed. With integer weights every
    partial sum is an exact integer or half-integer in float64, so the value equals the double sum."""

    def __init__(self, rD, rH):
        self.order = np.argsort(np.asarray(rH, float), kind="stable")
        rHs = np.asarray(rH, float)[self.order]
        rD = np.asarray(rD, float)
        self.lo = np.searchsorted(rHs, rD, side="left")
        self.hi = np.searchsorted(rHs, rD, side="right")

    def __call__(self, mD, mH):
        sD, sH = float(np.sum(mD)), float(np.sum(mH))
        if sD == 0.0 or sH == 0.0:
            return None
        cw = np.concatenate(([0.0], np.cumsum(np.asarray(mH, float)[self.order])))
        num = float(np.dot(np.asarray(mD, float), cw[self.lo] + 0.5 * (cw[self.hi] - cw[self.lo])))
        return num / (sD * sH)


def ratio(num, den):
    return None if den == 0 else num / den


def populations(runs, n_max):
    """E2-6: H = judged pairs with honest X; D = judged pairs with active-malicious X; every observer O is kept
    (malicious or not); pairs with inactive-malicious X are excluded. Judged pairs with n > n_max are also listed."""
    H, D, above = [], [], []
    for seed in sorted(runs):
        R = runs[seed]
        for (s, o, x), p in sorted(R["P"].items()):
            if not p["judged"] or (x in R["gt"]["malicious"] and x not in R["gt"]["active"]):
                continue
            row = {"seed": s, "o": o, "x": x, "n": p["n"], "r": p["r"], "bin": p["bin"], "flag": p["flag"]}
            (D if x in R["gt"]["active"] else H).append(row)
            if p["n"] > n_max:
                above.append(dict(row, label="active_malicious" if x in R["gt"]["active"] else "honest"))
    return H, D, above


# ---------------------------------------------------------------- E2-8: cluster bootstrap -----------------
def draw_replicate(rng, S, U):
    """One replicate's draws, in the frozen order: sigma = integers(0, |S|, |S|); then, for every occurrence
    t in order, nu_t = integers(0, |U_s|, |U_s|) for s = S[sigma_t] (no call when |U_s| = 0).
    A seed drawn twice gets two independent node draws."""
    sigma = rng.integers(0, len(S), len(S))
    occ = []
    for t in range(len(S)):
        s = S[sigma[t]]
        occ.append((s, rng.integers(0, len(U[s]), len(U[s])) if len(U[s]) else None))
    return sigma, occ


def node_multiplicities(occ, U):
    """m(s, X) = sum over the occurrences of s of X's count in that occurrence's node draw (0 if s not drawn)."""
    m = C.Counter()
    for s, nu in occ:
        if nu is not None:
            for j in nu:
                m[(s, U[s][j])] += 1
    return m


def bootstrap(S, H, D, B=B_BOOT, seed=BOOT_SEED):
    """H, D: lists of pairs {"seed", "x", "r", "flag"}. Returns the replicate arrays FA*, TDR*, AUC*, the
    zero-denominator counts and the node universe. Nothing is discarded."""
    U = {s: sorted({p["x"] for p in H + D if p["seed"] == s}) for s in S}
    off, tot = {}, 0
    for s in S:
        off[s] = tot; tot += len(U[s])
    gidx = {(s, x): off[s] + i for s in S for i, x in enumerate(U[s])}
    iH = np.array([gidx[(p["seed"], p["x"])] for p in H], dtype=np.int64)
    iD = np.array([gidx[(p["seed"], p["x"])] for p in D], dtype=np.int64)
    fH = np.array([p["flag"] for p in H], float)
    fD = np.array([p["flag"] for p in D], float)
    auc = AUCIndex([p["r"] for p in D], [p["r"] for p in H])
    rng = np.random.Generator(np.random.PCG64(seed))
    fa, tdr, au = np.empty(B), np.empty(B), np.empty(B)
    zero = {"fa": 0, "tdr": 0, "auc": 0}
    for b in range(B):
        _, occ = draw_replicate(rng, S, U)
        cnt = np.zeros(tot)
        for s, nu in occ:
            if nu is not None:
                cnt[off[s]:off[s] + len(U[s])] += np.bincount(nu, minlength=len(U[s]))
        mH, mD = cnt[iH], cnt[iD]
        sH, sD = float(mH.sum()), float(mD.sum())
        if sH == 0.0:
            fa[b] = 1.0; zero["fa"] += 1
        else:
            fa[b] = float(np.dot(mH, fH)) / sH
        if sD == 0.0:
            tdr[b] = 0.0; zero["tdr"] += 1
        else:
            tdr[b] = float(np.dot(mD, fD)) / sD
        a = auc(mD, mH)
        if a is None:
            au[b] = 0.0; zero["auc"] += 1
        else:
            au[b] = a
    return {"fa": fa, "tdr": tdr, "auc": au, "zero": zero, "U": U}


def pct(values, q):
    return float(np.percentile(values, q, method="linear"))


# ---------------------------------------------------------------- E2-7, E2-9, E2-14: decisions ------------
def decide(nD, nD_nodes, nH, fa_lb, fa_ub, auc, auc_lb, tdr_lb):
    """Pure decision rule. Returns the G2 and G2b items, the overall outcome and the frozen conclusions."""
    g2 = nD >= G2_MIN_PAIRS and nD_nodes >= G2_MIN_NODES
    out = {"G2": {"judged_active_malicious_pairs": nD, "distinct_seed_X": nD_nodes, "pass": g2}}
    if nH == 0:
        out["G2b"] = {"item1_fa": "not evaluable (no judged honest pairs)", "item2_auc": "not evaluable",
                      "item3_tdr_vs_fa": "not evaluable", "pass": False}
        out["outcome"] = "STOP: G2b-FA not evaluable (H empty); G2b not passed; report for review"
        out["conclusions"] = []
        return out
    i1 = fa_lb <= FA_BAR
    if g2:
        i2 = auc is not None and auc >= AUC_BAR and auc_lb > AUC_NULL
        i3 = tdr_lb > fa_ub
        out["G2b"] = {"item1_fa": i1, "item2_auc": i2, "item3_tdr_vs_fa": i3, "pass": i1 and i2 and i3}
    else:
        out["G2b"] = {"item1_fa": i1, "item2_auc": "not interpretable (G2 failed)",
                      "item3_tdr_vs_fa": "not interpretable (G2 failed)", "pass": None if i1 else False}
    conc = []
    if not g2:
        conc.append(CONCLUSION_G2)
    if not i1 or (g2 and not out["G2b"]["pass"]):
        conc.append(CONCLUSION_G2B)
        outcome = "G2b FAIL: the roadmap stops; Option C discussion follows (E3-E5 do not run)"
    elif not g2:
        outcome = ("G2 FAIL (G2b-FA passed; G2b detection not interpretable): one extension to newly approved "
                   "held-out seeds is allowed, then Option C; E3 on hold")
    else:
        outcome = "G2 PASS and G2b PASS: stop and report; E3 only with explicit approval"
    out["outcome"], out["conclusions"] = outcome, conc
    return out


# ---------------------------------------------------------------- E2-10: ceiling table --------------------
def ceiling_run(seed, P, gt, opp):
    mal, act = gt["malicious"], gt["active"]
    pkt_k1 = C.defaultdict(set)
    for x, s, p, k1 in opp:
        pkt_k1[(x, s, p)].add(k1)
    obs_x = {x for x, _, _, _ in opp}
    n_drops = len(gt["drops"])
    any_ = sum(1 for d in gt["drops"] if pkt_k1.get(d))
    ou = sum(1 for d in gt["drops"] if 1 in pkt_k1.get(d, ()))
    onu = sum(1 for d in gt["drops"] if 0 in pkt_k1.get(d, ()))
    judged_x, flagged_x = set(), set()
    for (_, o, x), p in P.items():
        if p["judged"]:
            judged_x.add(x)
            if p["flag"]:
                flagged_x.add(x)
    cls = {"unobservable": [], "insufficient": [], "detected": [], "missed": []}
    for x in sorted(act):
        if x not in obs_x:
            cls["unobservable"].append(x)
        elif x not in judged_x:
            cls["insufficient"].append(x)
        elif x in flagged_x:
            cls["detected"].append(x)
        else:
            cls["missed"].append(x)
    honest = gt["nodes"] - {gt["sink"]} - mal
    hj = honest & judged_x
    Dp = [p for (_, o, x), p in P.items() if p["judged"] and x in act]
    tdr = ratio(sum(p["flag"] for p in Dp), len(Dp))
    share = ratio(len(cls["detected"]) + len(cls["missed"]), len(act))
    return {"seed": seed, "drops": n_drops, "drops_observable": any_, "drops_observable_O_eq_U": ou,
            "drops_observable_O_ne_U": onu, "frac_observable": ratio(any_, n_drops),
            "frac_observable_O_eq_U": ratio(ou, n_drops), "frac_observable_O_ne_U": ratio(onu, n_drops),
            "malicious": sorted(mal), "active_malicious": sorted(act), "inactive_malicious": sorted(mal - act),
            "active_classification": cls, "honest_nodes": len(honest), "honest_judged": len(hj),
            "frac_honest_judged": ratio(len(hj), len(honest)), "tdr_pairs": tdr, "judged_active_pairs": len(Dp),
            "flagged_active_pairs": sum(p["flag"] for p in Dp),
            "share_active_judged": share,
            "system_coverage": None if tdr is None or share is None else tdr * share}


def ceiling_pooled(runs):
    tot = lambda k: sum(r[k] for r in runs)
    nd, na = tot("drops"), sum(len(r["active_malicious"]) for r in runs)
    cls = {c: sum(len(r["active_classification"][c]) for r in runs) for c in ("unobservable", "insufficient", "detected", "missed")}
    tdr = ratio(tot("flagged_active_pairs"), tot("judged_active_pairs"))
    share = ratio(cls["detected"] + cls["missed"], na)
    return {"drops": nd, "frac_observable": ratio(tot("drops_observable"), nd),
            "frac_observable_O_eq_U": ratio(tot("drops_observable_O_eq_U"), nd),
            "frac_observable_O_ne_U": ratio(tot("drops_observable_O_ne_U"), nd),
            "active_malicious_seed_X": na, "inactive_malicious_seed_X": sum(len(r["inactive_malicious"]) for r in runs),
            "active_classification_counts": cls, "honest_nodes": tot("honest_nodes"), "honest_judged": tot("honest_judged"),
            "frac_honest_judged": ratio(tot("honest_judged"), tot("honest_nodes")), "tdr_pairs": tdr,
            "share_active_judged": share, "system_coverage": None if tdr is None or share is None else tdr * share}


# ---------------------------------------------------------------- main ------------------------------------
def git(*a, cwd=REPO):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True).stdout.strip()


def evaluate(roots, seeds, dev):
    prov = {f: md5(os.path.join(REPO, f)) for f in FROZEN_MD5}
    bad = [f for f, h in FROZEN_MD5.items() if prov[f] != h]
    if bad:
        raise Stop(f"frozen inputs changed: {bad}")
    build = {f: (md5(os.path.join(REPO, f)) if os.path.exists(os.path.join(REPO, f)) else None) for f in BUILD_MD5}
    if not dev and any(build[f] != h for f, h in BUILD_MD5.items()):
        raise Stop(f"library/binary md5 differ from E2-2: {build}")
    me = os.path.relpath(os.path.abspath(__file__), REPO)
    if not dev and (git("ls-files", "--error-unmatch", me) != me or git("status", "--porcelain", "--", me)):
        raise Stop(f"{me} is not committed and unmodified; E2 must use the committed evaluator")
    cal = frozen_calibration(os.path.join(REPO, "analysis/stageE/e1/e1_calibration_rev4.json"))

    per_p, inputs = {}, {}
    for tag, p in P_SETS:
        runs = {}
        for seed in seeds:
            rundir = os.path.join(roots[tag], f"run_{seed}")
            files = ["stderr.log", f"v1_{seed}.tr", f"v1_{seed}_meta.csv", f"v1_{seed}_mobility.csv", "e1_opportunities.csv"]
            missing = [f for f in files if not os.path.exists(os.path.join(rundir, f))]
            if missing:
                raise Stop(f"{rundir}: missing {missing}")
            inputs[f"{tag}/run_{seed}"] = {f: md5(os.path.join(rundir, f)) for f in files}
            meta = check_meta(rundir, seed, p)
            gt = ground_truth(rundir, seed)
            P = judge_pairs(roots[tag], seed, cal)
            runs[seed] = {"meta": meta, "gt": gt, "P": P, "opp": opportunity_rows(rundir)}
        per_p[tag] = runs

    H, D, above = populations(per_p["p075"], cal["n_max"])          # E2-6: p = 0.75 runs only
    nH, nD = len(H), len(D)
    fa = ratio(sum(p["flag"] for p in H), nH)
    tdr = ratio(sum(p["flag"] for p in D), nD)
    auc = AUCIndex([p["r"] for p in D], [p["r"] for p in H])(np.ones(nD), np.ones(nH)) if nD and nH else None
    nodes_D = len({(p["seed"], p["x"]) for p in D})

    bs = bootstrap(list(seeds), H, D)
    q = {k: pct(bs[{"fa_lb": "fa", "fa_ub": "fa", "tdr_lb": "tdr", "auc_lb": "auc"}[k]], v) for k, v in PCT.items()}
    dec = decide(nD, nodes_D, nH, q["fa_lb"], q["fa_ub"], auc, q["auc_lb"], q["tdr_lb"])

    per_bin = {}
    for lab, pop in (("honest", H), ("active_malicious", D)):
        cnt = C.Counter((p["bin"], p["flag"]) for p in pop)
        per_bin[lab] = {str(b): {"judged": cnt[(b, False)] + cnt[(b, True)], "flagged": cnt[(b, True)]}
                        for b in range(1, len(cal["L"]) + 1)}
    ceil = {}
    for tag, _ in P_SETS:
        rr = [ceiling_run(seed, R["P"], R["gt"], R["opp"]) for seed, R in per_p[tag].items()]
        ceil[tag] = {"role": "observability ceiling (E2-10)" if tag == "p100" else "descriptive, alongside the ceiling (E2-10)",
                     "per_run": rr, "pooled": ceiling_pooled(rr)}
    malsets = {str(s): {"num_malicious_p075": per_p["p075"][s]["meta"]["num_malicious"],
                        "num_malicious_p100": per_p["p100"][s]["meta"]["num_malicious"],
                        "same_malicious_set": per_p["p075"][s]["gt"]["malicious"] == per_p["p100"][s]["gt"]["malicious"]}
               for s in seeds}

    return {
        "spec": "analysis/stageE/E2_SPEC.md (frozen at commit a87ffbc; D-20)",
        "status": ("DEVELOPMENT ONLY - not E2; no gate applies" if dev else "E2 held-out Arm-A evaluation"),
        "created_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seeds": list(seeds), "roots": roots,
        "frozen": {"n_ref": cal["n_ref"], "edges_L": cal["L"], "tau_A_b": cal["tau"], "n_max": cal["n_max"],
                   "fa_bar": FA_BAR, "auc_bar": AUC_BAR, "auc_null": AUC_NULL, "g2_min_pairs": G2_MIN_PAIRS,
                   "g2_min_nodes": G2_MIN_NODES, "percentiles": PCT, "percentile_method": "linear"},
        "population_p075": {"judged_honest_pairs": nH, "judged_active_malicious_pairs": nD,
                            "distinct_seed_X_in_D": nodes_D, "per_bin": per_bin,
                            "judged_above_n_max": above},
        "point": {"FA": fa, "TDR": tdr, "AUC": auc,
                  "FA_flagged": sum(p["flag"] for p in H), "TDR_flagged": sum(p["flag"] for p in D)},
        "bootstrap": {"B": B_BOOT, "generator": "numpy.random.PCG64", "seed": BOOT_SEED,
                      "hierarchy": "seeds, then X nodes within each seed occurrence; O not resampled",
                      "multiplicity": "m(seed, X) = sum of X's counts over all occurrences of that seed",
                      "node_universe": {str(s): u for s, u in bs["U"].items()},
                      "zero_denominator_replicates": bs["zero"],
                      "FA_lb_5": q["fa_lb"], "FA_ub_97_5": q["fa_ub"], "TDR_lb_2_5": q["tdr_lb"],
                      "AUC_lb_2_5": q["auc_lb"],
                      "descriptive": {"TDR_ub_97_5": pct(bs["tdr"], 97.5), "AUC_ub_97_5": pct(bs["auc"], 97.5)}},
        "decision": dec,
        "ceiling": ceil,
        "malicious_sets": malsets,
        "provenance": {"frozen_md5": prov, "build_md5": build, "inputs_md5": inputs,
                       "evaluator_md5": md5(os.path.abspath(__file__)),
                       "parent_commit": git("rev-parse", "HEAD"),
                       "submodule_commit": git("-C", "src/aqua-sim-ng", "rev-parse", "HEAD"),
                       "python": platform.python_version(), "numpy": np.__version__}}


def report(res):
    L = []; W = L.append
    d, pt, bs, pop = res["decision"], res["point"], res["bootstrap"], res["population_p075"]
    W(f"Stage E E2 - {res['status']}")
    W(f"Specification: {res['spec']}; seeds {res['seeds']}; created {res['created_utc']}")
    W("")
    W(f"Population (p = 0.75): judged honest pairs |H| = {pop['judged_honest_pairs']}; judged active-malicious pairs "
      f"|D| = {pop['judged_active_malicious_pairs']}; distinct (seed, X) in D = {pop['distinct_seed_X_in_D']}; "
      f"judged pairs above n_max {res['frozen']['n_max']}: {len(pop['judged_above_n_max'])}")
    f = lambda v: "undefined" if v is None else f"{v:.4f}"
    W(f"Point: FA {pt['FA_flagged']}/{pop['judged_honest_pairs']} = {f(pt['FA'])}; TDR {pt['TDR_flagged']}/"
      f"{pop['judged_active_malicious_pairs']} = {f(pt['TDR'])}; AUC {f(pt['AUC'])}")
    W(f"Bootstrap (B = {bs['B']}, PCG64 {bs['seed']}; {bs['hierarchy']}): FA 5th {bs['FA_lb_5']:.4f}, FA 97.5th "
      f"{bs['FA_ub_97_5']:.4f}, TDR 2.5th {bs['TDR_lb_2_5']:.4f}, AUC 2.5th {bs['AUC_lb_2_5']:.4f}; zero-denominator "
      f"replicates {bs['zero_denominator_replicates']}")
    W("")
    W(f"G2: |D| {d['G2']['judged_active_malicious_pairs']} >= {G2_MIN_PAIRS} and distinct (seed, X) "
      f"{d['G2']['distinct_seed_X']} >= {G2_MIN_NODES}: {'PASS' if d['G2']['pass'] else 'FAIL'}")
    g = d["G2b"]
    W(f"G2b item 1 (FA 5th percentile <= {FA_BAR}): {g['item1_fa']}")
    W(f"G2b item 2 (AUC >= {AUC_BAR} and AUC 2.5th percentile > {AUC_NULL}): {g['item2_auc']}")
    W(f"G2b item 3 (TDR 2.5th percentile > FA 97.5th percentile): {g['item3_tdr_vs_fa']}")
    W(f"G2b: {g['pass']}")
    W(f"Outcome (E2-14): {d['outcome']}")
    for c in d["conclusions"]:
        W(f"   frozen conclusion: \"{c}\"")
    W("")
    for tag in ("p100", "p075"):
        c = res["ceiling"][tag]["pooled"]
        W(f"Ceiling table {tag} ({res['ceiling'][tag]['role']}): drops {c['drops']}, observable {f(c['frac_observable'])} "
          f"(O=U {f(c['frac_observable_O_eq_U'])}, O!=U {f(c['frac_observable_O_ne_U'])}); active-malicious (seed, X) "
          f"{c['active_malicious_seed_X']} {c['active_classification_counts']}; inactive {c['inactive_malicious_seed_X']}; "
          f"honest judged {c['honest_judged']}/{c['honest_nodes']}; system coverage {f(c['system_coverage'])}")
    W("")
    W("E3 does not start automatically after E2; it requires explicit approval after review (E2-14).")
    return "\n".join(L) + "\n"


def main(argv):
    args = list(argv)
    opt = lambda k: (args[args.index(k) + 1] if k in args else None)
    dev = "--dev" in args
    roots = {"p075": opt("--p075"), "p100": opt("--p100")}
    out = opt("--out") or (None if dev else HERE)
    if None in roots.values() or out is None:
        raise SystemExit(__doc__)
    roots = {k: os.path.abspath(os.path.expanduser(v)) for k, v in roots.items()}
    out = os.path.abspath(os.path.expanduser(out))
    if dev:
        if opt("--seeds") is None:
            raise SystemExit("--dev requires --seeds")
        seeds = tuple(int(s) for s in opt("--seeds").split(","))
        if os.path.commonpath([out, HERE]) == HERE:
            raise SystemExit("development output must not be written inside analysis/stageE/e2")
    else:
        if "--seeds" in args:
            raise SystemExit("E2 seeds are fixed to 2-11 (E2-1); --seeds is development only")
        seeds = SEEDS_E2
    targets = [os.path.join(out, "e2_results.json"), os.path.join(out, "e2_report.txt")]
    if any(os.path.exists(t) for t in targets):
        raise SystemExit(f"{out} already holds E2 outputs; refusing to overwrite")
    try:
        res = evaluate(roots, seeds, dev)
    except Stop as e:
        print(f"STOP (no gate interpreted): {e}", file=sys.stderr)
        return 2
    os.makedirs(out, exist_ok=True)
    with open(targets[0], "x") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    txt = report(res)
    with open(targets[1], "x") as fh:
        fh.write(txt)
    print(txt, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
