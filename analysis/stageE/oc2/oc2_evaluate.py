#!/usr/bin/env python3
"""Stage E OC-2 — standalone EAQTE operating characterization (frozen ../OC2_SPEC.md revision 2, commit a984fc7;
D-23, D-24).

Offline rescoring of the fixed 40-dB E1 traces (clean seeds 12-21) across the Eb/N0 scoring grid. It does not
characterize newly simulated network behavior at other Eb/N0 values. Descriptive only: no pass/fail gate, not a
revived G3/G4 gate, no secure-routing, G5/G6 or PACT claim. No Arm C. NumPy only.

Implements OC2_SPEC.md exactly:
- §2  inputs (observer-side only), md5 check against e1/e1_calibration_rev4.json; O1 table rebuilt by the exact
      observer.observe() event loop and checked against O1's own xpos/age for every opportunity.
- §3  E-1..E-9: p(d), d, own position/velocity row at floor(t0), outcome-blind p-history (window 10, append then
      compute, population variance in C++ summation order), CCQ, SS, EE, freeze iff EE < 0.3.
- §4  S-1..S-4, S-12; §5 S-5..S-11 (Mantel-Haenszel OR with the S-6a orientation; stratum fixed-effects logistic
      model fitted by IRLS; OC-2's own cluster bootstrap with the E2-8 occurrence-sum rule and one shared draw
      sequence for every (g, k) point and both statistics).
- §6  S-13 / S-13a / S-13b (revision 2, D-24): observed-data failures stop OC-2; in bootstrap replicates a
      single-outcome stratum is non-informative (S-8c: omitted from that replicate's logistic fit; zero MH terms by
      formula) and a replicate stops only when the requested statistic itself is non-identifiable or non-finite.
      No fallback, substitution, discard or redraw. D-24 was fixed from development-only behavior before any OC-2
      data were read; it is pre-specified, not tuned from real results.
- §7  P-1 parity harness (C++ log lines used only here, never as OC-2 inputs).
- §8  R-1/R-1b/R-1c/R-2/R-3: fixed outputs, overwrite refusal, committed-code guard, input md5s.
Writes <out>/oc2_results.json and <out>/oc2_report.txt; a stop writes no result file and reports to stderr.

usage:
  oc2_evaluate.py [--e1-root DIR] [--out DIR] [--workers N]            OC-2 (clean seeds 12-21; DIR/run_N)
  oc2_evaluate.py --dev --seeds 1 --e1-root DIR --out DIR [--B N]       development only (never OC-2)
"""
import sys, os, csv, json, math, hashlib, subprocess, datetime, platform, multiprocessing
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE_E = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(STAGE_E, "..", ".."))
sys.dont_write_bytecode = True                   # never leave caches next to frozen helpers
sys.path.insert(0, os.path.join(STAGE_E, "e1"))
sys.path.insert(0, os.path.join(STAGE_E, "e2"))
from observer import load_inputs, KV, vec        # O1 inputs and parsers, unchanged
from geom import res6                            # O1 tie rule and print resolution, unchanged
from calibrate import name, CELLS                # stratum cell names, unchanged
from e2_evaluate import draw_replicate           # E2-8 occurrence-specific draw rule (OC2_SPEC S-7), unchanged

# ---------------------------------------------------------------- frozen constants (OC2_SPEC.md) ----------
SEEDS_OC2 = tuple(range(12, 22))                                     # §2
GRID = (15.0, 20.0, 24.5, 27.5, 31.1, 34.5, 37.5, 40.0, 45.0, 50.0)  # §3, README §10 (dB)
K_PRIMARY, K_SECONDARY = 1.5, (1.0, 2.0)                             # S-4, S-10
F_KHZ, M_BITS = 25.0, 640.0                                          # E-1
HIST_WINDOW = 10                                                     # E-4
DT_MIN, NORM_MIN = 0.05, 1e-6                                        # E-6a, E-8
XI = 0.3                                                             # E-9
N_REF = 14                                                           # S-3 (J1)
B_BOOT, BOOT_SEED = 10000, 12345                                     # S-7
PCT = (2.5, 97.5)                                                    # S-7 (linear)
IRLS_MAX_IT, IRLS_TOL, SEP_EPS, COND_MAX = 100, 1e-10, 1e-12, 1e12   # S-13a
SS_CCQ_EDGES = np.linspace(0.0, 1.0, 11)                             # S-12 (bin width 0.1)
EE_EDGES = np.linspace(0.0, 1.0, 21)                                 # S-12 (bin width 0.05)
PARITY_EBN0, PARITY_K = 40.0, 1.5                                    # P-1 (C++ compiled values)
OUT_JSON, OUT_REPORT = "oc2_results.json", "oc2_report.txt"         # R-1
FROZEN_MD5 = {                                                       # R-1c and §2
    "analysis/stageE/OC2_SPEC.md": "f0b83d29395972982e7ce34c389b77d7",            # revision 2 (D-24)
    "analysis/stageE/OPTION_C_TRANSITION.md": "a40cfc87d84e67e2c16ca99541d37a4b",
    "analysis/stageE/e1/e1_calibration_rev4.json": "0ca88a0e4c8fc56f63e6b44b496b65fd",
    "analysis/stageE/e1/observer.py": "45d79f770c13f151bddee86b09bf96f6",
    "analysis/stageE/e1/geom.py": "413d4f60b4efcdb125bf00c65d792e09",
    "analysis/stageE/e1/calibrate.py": "17b4b39af32b64cbb7eaaeb003216069",
    "analysis/stageE/e1/calibrate_rev3.py": "03a6ff9cb9b4bcfbc4dd6423b78aaa48",
    "analysis/stageE/e1/calibrate_rev4.py": "830a3733f378fb04a4680e43d0c60cf6",
    "analysis/stageE/e1/truth.py": "203dbb7046bb1ad4323fdc222dfbacc8",
    "analysis/stageE/e2/e2_evaluate.py": "e65000be640e4153809ed31a4d5cd647"}
CODE_FILES = ("analysis/stageE/oc2/oc2_evaluate.py", "analysis/stageE/oc2/test_oc2_evaluate.py")   # R-1b
OUTCOME = {"MATCH": 0, "SILENT": 1, "OTHER-UP": 2}


class Stop(Exception):
    """A frozen precondition or check failed: OC-2 stops and reports; no result file is written."""


class ObservedFailure(Stop):
    """S-13: statistical failure in the observed data."""


class ReplicateFailure(Stop):
    """S-13b: a degenerate bootstrap replicate; the interval is not evaluable under the frozen specification."""


class FitFailure(Exception):
    """An S-13a criterion was met by one fit (observed data or one replicate)."""


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- E-1: p(d) ----------------------------------
def p_of_d(d_m, ebn0_db, k):
    """Coded Eqs. 6-10 exactly as AquaSimTrustQVBF::TransmissionProbability (Eb/N0 = ebn0_db, spreading k)."""
    d_m = np.asarray(d_m, dtype=float)
    d_km = d_m / 1000.0
    f2 = F_KHZ * F_KHZ
    alpha_db = 0.11 * (f2 / (1.0 + f2)) + 44.0 * (f2 / (4100.0 + f2)) + 2.75e-4 * f2 + 0.003
    alpha_linear = 10.0 ** (alpha_db / 10.0)
    ebn0_linear = 10.0 ** (ebn0_db / 10.0)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        a = np.power(d_km, k) * np.power(alpha_linear, d_km)
        snr = ebn0_linear / a
        pe = 0.5 * (1.0 - np.sqrt(snr / (1.0 + snr)))
        p = np.power(1.0 - pe, M_BITS)
    p = np.where(d_km <= 0.0, 1.0, p)
    return np.clip(p, 0.0, 1.0)


# ---------------------------------------------------------------- §2: inputs and O1 table rebuild ------------
def read_velocities(path):
    """Own velocity rows: node address -> {floor(time): (vx, vy)} (E-7; the O1 keying of the mobility log)."""
    vel = {}
    with open(path) as fh:
        next(fh)
        for ln in fh:
            t, n, x, y, z, vx, vy = ln.split(",")[:7]
            vel.setdefault(int(n) + 1, {})[int(math.floor(float(t)))] = (float(vx), float(vy))
    return vel


def read_opportunities(path):
    rows = []
    for r in csv.DictReader(open(path)):
        rows.append({"o": int(r["o"]), "x": int(r["x"]), "u": int(r["u"]), "s": int(r["s"]), "p": int(r["p"]),
                     "t0": float(r["t0"]), "own": int(r["own"]), "age": float(r["age"]),
                     "cell": (int(r["k1"]), int(r["k2"]), int(r["k3"])), "out": OUTCOME[r["out"]],
                     "xpos": vec(r["xpos"])})
    return rows


def rebuild_tables(rows, dec, own):
    """X's (last t, last f, previous t, previous f) in O's neighbour table at each opportunity's event, by the exact
    O1 event loop (observer.observe): events sorted by (key, kind, u, s, p); decodes enter the table only when the
    key changes (strictly before). Every row must match O1's own xpos and age exactly."""
    out = [None] * len(rows)
    order, seen = [], {}
    for i, r in enumerate(rows):
        if r["o"] not in seen:
            seen[r["o"]] = []
            order.append(r["o"])
        elif seen[r["o"]][-1] != i - 1:
            raise Stop(f"opportunity rows of observer {r['o']} are not contiguous")
        seen[r["o"]].append(i)
    for o in order:
        idxs = seen[o]
        events = [(t, 1, tx, s, p, t, f) for (t, tx, s, p, f, d, tgt) in dec.get(o, [])]
        events += [(t0 - res6(t0), 0, o, s, p, t0, f) for (t0, s, p, f) in own.get(o, [])]
        events.sort(key=lambda e: (e[0], e[1], e[2], e[3], e[4]))
        table, pending, cur, ptr = {}, [], None, 0
        for key, kind, u, s, p, t0, fu in events:
            if key != cur:
                for (y, ty, fy) in pending:
                    prev = table.get(y)
                    table[y] = (ty, fy, prev[0] if prev else None, prev[1] if prev else None)
                pending, cur = [], key
            while ptr < len(idxs):
                r = rows[idxs[ptr]]
                if not (r["own"] == int(kind == 0) and r["u"] == u and r["s"] == s and r["p"] == p and r["t0"] == t0):
                    break
                entry = table.get(r["x"])
                if entry is None or entry[1] != r["xpos"] or (r["t0"] - entry[0]) != r["age"]:
                    raise Stop(f"O1 table rebuild disagrees with e1_opportunities.csv at o={o} x={r['x']} t0={r['t0']!r}")
                out[idxs[ptr]] = entry
                ptr += 1
            if kind == 1:
                pending.append((u, t0, fu))
        if ptr != len(idxs):
            raise Stop(f"observer {o}: {len(idxs) - ptr} opportunity rows not matched to O1 events")
    return out


def load_run(rundir, seed, cal_lab):
    for f in ("stderr.log", f"v1_{seed}.tr", f"v1_{seed}_mobility.csv", "e1_opportunities.csv"):
        if not os.path.exists(os.path.join(rundir, f)):
            raise Stop(f"{rundir}: missing {f}")
    rows = read_opportunities(os.path.join(rundir, "e1_opportunities.csv"))
    dec, own, mob = load_inputs(rundir, seed)
    vel = read_velocities(os.path.join(rundir, f"v1_{seed}_mobility.csv"))
    tables = rebuild_tables(rows, dec, own)
    n = len(rows)
    d = np.empty(n); vi = np.empty((n, 2)); vj = np.zeros((n, 2)); has_vj = np.zeros(n, bool)
    for i, (r, (lt, lf, pt, pf)) in enumerate(zip(rows, tables)):
        sec = int(math.floor(r["t0"]))                                   # E-3 / E-7
        po, vo = mob.get(r["o"], {}).get(sec), vel.get(r["o"], {}).get(sec)
        if po is None or vo is None:
            raise Stop(f"{rundir}: no own mobility row for o={r['o']} at second {sec}")
        x = r["xpos"]
        d[i] = math.sqrt((po[0] - x[0]) ** 2 + (po[1] - x[1]) ** 2 + (po[2] - x[2]) ** 2)   # E-2
        vi[i] = vo
        vx, vy, has = neighbor_velocity(lt, lf, pt, pf)                  # E-6 / E-6a
        vj[i] = (vx, vy)
        has_vj[i] = has
    return {"seed": np.full(n, seed), "o": np.array([r["o"] for r in rows]), "x": np.array([r["x"] for r in rows]),
            "out": np.array([r["out"] for r in rows]), "stratum": np.array([cal_lab[r["cell"]] for r in rows]),
            "d": d, "vi": vi, "vj": vj, "has_vj": has_vj, "n_rows": n}


def concat_runs(runs):
    keys = ("seed", "o", "x", "out", "stratum", "d", "vi", "vj", "has_vj")
    return {k: np.concatenate([r[k] for r in runs]) for k in keys}


# ---------------------------------------------------------------- E-4..E-9: EE --------------------------------
def history_lags(seed, o, x):
    """lags[L][i] = index of the row L events earlier in row i's (seed, O, X) group (O1 row order), else -1."""
    n = len(seed)
    gid = np.unique(np.stack([seed, o, x], axis=1), axis=0, return_inverse=True)[1].ravel()
    order = np.argsort(gid, kind="stable")
    g_sorted = gid[order]
    start = np.r_[0, np.flatnonzero(g_sorted[1:] != g_sorted[:-1]) + 1]
    pos_in_group = np.arange(n) - np.repeat(start, np.diff(np.r_[start, n]))
    lags = np.full((HIST_WINDOW, n), -1, dtype=np.int64)
    for L in range(HIST_WINDOW):
        ok = pos_in_group >= L
        src = np.full(n, -1, dtype=np.int64)
        src[ok] = order[np.flatnonzero(ok) - L]
        lags[L][order] = src
    return lags


def ccq_from_history(p, lags):
    """E-4/E-5 as ComputeChannelQuality: append the current p, keep the last 10, population variance summed
    oldest to newest, CCQ = p(1 - tanh var) (p itself with fewer than 2 samples), clamped to [0, 1]."""
    valid = lags >= 0
    cnt = valid.sum(axis=0).astype(float)
    total = np.zeros(len(p))
    for L in range(HIST_WINDOW - 1, -1, -1):                          # oldest first, as the C++ vector
        total = total + np.where(valid[L], p[np.maximum(lags[L], 0)], 0.0)
    mean = total / cnt
    var = np.zeros(len(p))
    for L in range(HIST_WINDOW - 1, -1, -1):
        diff = p[np.maximum(lags[L], 0)] - mean
        var = var + np.where(valid[L], diff * diff, 0.0)
    var = var / cnt
    tanh_var = np.fromiter((math.tanh(v) for v in var), dtype=float, count=len(var))   # C-library tanh, as std::tanh
    ccq = np.where(cnt < 2, p, np.clip(p * (1.0 - tanh_var), 0.0, 1.0))
    return ccq


def neighbor_velocity(lt, lf, pt, pf):
    """E-6/E-6a as EstimateNeighborVelocity: 2D velocity from X's last two decoded positions; (0, 0, False) without a
    previous position or when dt < 0.05 s."""
    if pt is None:
        return 0.0, 0.0, False
    dt = lt - pt
    if dt < DT_MIN:
        return 0.0, 0.0, False
    return (lf[0] - pf[0]) / dt, (lf[1] - pf[1]) / dt, True


def ss_values(vi, vj, has_vj):
    """E-6/E-6a/E-8 as ComputeStabilityScore: 2D cosine similarity, clamped; 0.5 by default. Returns (SS, default)."""
    vix, viy, vjx, vjy = vi[:, 0], vi[:, 1], vj[:, 0], vj[:, 1]
    norm_i = np.sqrt(vix * vix + viy * viy)
    norm_j = np.sqrt(vjx * vjx + vjy * vjy)
    default = (~has_vj) | (norm_i < NORM_MIN) | (norm_j < NORM_MIN)
    with np.errstate(divide="ignore", invalid="ignore"):
        vsim = (vix * vjx + viy * vjy) / (norm_i * norm_j)
    vsim = np.clip(np.where(default, 0.0, vsim), -1.0, 1.0)
    return np.where(default, 0.5, 0.5 * (1.0 + vsim)), default


def ee_and_freeze(ccq, ss):
    ee = 0.5 * ccq + 0.5 * ss                                            # E-9
    return ee, ee < XI


# ---------------------------------------------------------------- S-1..S-4, S-12 -------------------------------
def characterize(data, ee, ccq, ss, freeze, ss_default):
    ms = data["out"] != OUTCOME["OTHER-UP"]
    n_all, n_ms = int(len(ee)), int(ms.sum())
    fr_all, fr_ms = int(freeze.sum()), int(freeze[ms].sum())
    pair = np.unique(np.stack([data["seed"][ms], data["o"][ms], data["x"][ms]], axis=1), axis=0, return_inverse=True)[1].ravel()
    n_pair = np.bincount(pair)
    unfrozen = np.bincount(pair, weights=(~freeze[ms]).astype(float))
    a_judged = int((n_pair >= N_REF).sum())                              # S-3, Arm A
    b_judged = int((unfrozen >= N_REF).sum())                            # S-3, Arm B (n_eff = unfrozen count)
    inert = fr_ms == 0                                                   # S-2
    saturated = b_judged < 0.5 * a_judged                                # S-3
    hist = {}
    for lab, m in (("match_silent", ms), ("all_opportunities", np.ones(n_all, bool))):
        hist[lab] = {"SS": np.histogram(ss[m], SS_CCQ_EDGES)[0].tolist(),
                     "CCQ": np.histogram(ccq[m], SS_CCQ_EDGES)[0].tolist(),
                     "SS_CCQ_joint": np.histogram2d(ss[m], ccq[m], [SS_CCQ_EDGES, SS_CCQ_EDGES])[0].astype(int).tolist(),
                     "EE": np.histogram(ee[m], EE_EDGES)[0].tolist(),
                     "default_SS_count": int(ss_default[m].sum())}
    return {"n_match_silent": n_ms, "n_all": n_all, "frozen_match_silent": fr_ms, "frozen_all": fr_all,
            "freeze_fraction_primary": fr_ms / n_ms if n_ms else None,
            "freeze_fraction_all_descriptive": fr_all / n_all if n_all else None,
            "arm_a_judged_pairs": a_judged, "arm_b_judged_pairs": b_judged,
            "inert": bool(inert), "saturated": bool(saturated), "active": bool(not inert and not saturated),
            "histograms": hist}


def activity_finding(points_primary):
    """S-4: at least one active grid value at the primary k (points_primary: g -> characterization at k = 1.5)."""
    return any(points_primary[g]["active"] for g in GRID)


# ---------------------------------------------------------------- S-6/S-6a: Mantel-Haenszel ---------------------
def mh_cells(stratum, exposed, silent, weights, n_strata):
    """(n_strata, 4) weighted cells a = (EE < 0.3, SILENT), b = (EE < 0.3, MATCH), c = (EE >= 0.3, SILENT),
    d = (EE >= 0.3, MATCH)  (S-6a orientation)."""
    cell = np.where(exposed, np.where(silent, 0, 1), np.where(silent, 2, 3))
    return np.bincount(stratum * 4 + cell, weights=weights, minlength=n_strata * 4).reshape(n_strata, 4)


def mh_num_den(cells):
    """OR_MH = sum_i a_i d_i / n_i / sum_i b_i c_i / n_i; strata with n_i = 0 contribute nothing (S-6)."""
    cells = np.asarray(cells, dtype=float)
    a, b, c, d = cells[..., 0], cells[..., 1], cells[..., 2], cells[..., 3]
    n = a + b + c + d
    num = np.divide(a * d, n, out=np.zeros_like(n), where=n > 0).sum(axis=-1)
    den = np.divide(b * c, n, out=np.zeros_like(n), where=n > 0).sum(axis=-1)
    return num, den


def mh_or(cells):
    num, den = mh_num_den(cells)
    if den == 0:
        raise FitFailure("Mantel-Haenszel odds ratio undefined: sum_i b_i c_i / n_i = 0")
    orr = num / den
    if not math.isfinite(orr):
        raise FitFailure("non-finite Mantel-Haenszel odds ratio")
    return float(orr)


# ---------------------------------------------------------------- S-8/S-8b/S-13a: logistic model ----------------
def fit_logit(stratum, ee, silent, weights=None, omit_single_outcome=False):
    """logit P(SILENT) = alpha_s + beta EE, one intercept per positive-weight stratum (S-8b), Newton/IRLS from zero,
    weighted by multiplicities. Observed data (omit_single_outcome=False): a single-outcome stratum is an S-13
    separation failure. Bootstrap replicates (omit_single_outcome=True, S-8c): a positive-weight single-outcome stratum
    is non-informative and omitted (its intercept has no finite MLE and its likelihood contribution tends to 1 for every
    beta); no informative stratum -> beta not identifiable. Raises FitFailure on any S-13a criterion; never
    regularizes or falls back."""
    w = np.ones(len(ee)) if weights is None else np.asarray(weights, dtype=float)
    pos = w > 0
    s_, e_, y_, w_ = stratum[pos], ee[pos], silent[pos].astype(float), w[pos]
    if len(e_) == 0:
        raise FitFailure("singular design: no positive-weight rows")
    if not np.all(np.isfinite(e_)):
        raise FitFailure("non-finite EE value")
    present = np.unique(s_)
    col = np.searchsorted(present, s_)
    m = len(present)
    sil = np.bincount(col, weights=w_ * y_, minlength=m)
    tot = np.bincount(col, weights=w_, minlength=m)
    single = (sil == 0) | (sil == tot)
    omitted = [int(v) for v in present[single]]
    if np.any(single):
        if not omit_single_outcome:
            raise FitFailure("separation: a positive-weight stratum has only SILENT or only MATCH")
        keep = ~single[col]                                              # S-8c: replicate fits only
        if not np.any(keep):
            raise FitFailure("no informative stratum: beta not identifiable (S-8c)")
        s_, e_, y_, w_ = s_[keep], e_[keep], y_[keep], w_[keep]
        present = np.unique(s_)
        col = np.searchsorted(present, s_)
        m = len(present)
    if np.all(e_ == e_[0]):
        raise FitFailure("singular design: EE is constant")

    def gram(v):
        g = np.zeros((m + 1, m + 1))
        g[np.arange(m), np.arange(m)] = np.bincount(col, weights=v, minlength=m)
        cross = np.bincount(col, weights=v * e_, minlength=m)
        g[:m, m] = cross
        g[m, :m] = cross
        g[m, m] = float(np.dot(v, e_ * e_))
        return g

    ev = np.linalg.eigvalsh(gram(w_))                                   # design Gram of the (replicate) dataset
    if not np.all(np.isfinite(ev)) or ev[0] <= 0 or math.sqrt(ev[-1] / ev[0]) > COND_MAX:
        raise FitFailure("singular design: condition number above 1e12")
    coef = np.zeros(m + 1)
    for it in range(1, IRLS_MAX_IT + 1):
        with np.errstate(over="ignore"):
            mu = 1.0 / (1.0 + np.exp(-(coef[col] + coef[m] * e_)))
        v = w_ * mu * (1.0 - mu)
        r = w_ * (y_ - mu)
        grad = np.empty(m + 1)
        grad[:m] = np.bincount(col, weights=r, minlength=m)
        grad[m] = float(np.dot(r, e_))
        try:
            step = np.linalg.solve(gram(v), grad)
        except np.linalg.LinAlgError:
            raise FitFailure("singular design: Hessian not invertible")
        if not np.all(np.isfinite(step)):
            raise FitFailure("non-finite IRLS update")
        coef = coef + step
        if np.max(np.abs(step)) < IRLS_TOL:
            break
    else:
        raise FitFailure("IRLS non-convergence within 100 iterations")
    with np.errstate(over="ignore"):
        mu = 1.0 / (1.0 + np.exp(-(coef[col] + coef[m] * e_)))
    if np.any(mu < SEP_EPS) or np.any(mu > 1.0 - SEP_EPS):
        raise FitFailure("separation: a fitted probability is within 1e-12 of 0 or 1")
    if not np.all(np.isfinite(coef)):
        raise FitFailure("non-finite coefficient")
    return {"beta": float(coef[m]), "alpha": {int(s): float(a) for s, a in zip(present, coef[:m])}, "iterations": it,
            "omitted_single_outcome_strata": omitted}


# ---------------------------------------------------------------- S-7/S-7c: bootstrap ---------------------------
def node_universe(data):
    """U_s = X values with at least one MATCH/SILENT opportunity in seed s, ascending (independent of (g, k))."""
    ms = data["out"] != OUTCOME["OTHER-UP"]
    return {int(s): sorted({int(x) for x in data["x"][ms & (data["seed"] == s)]}) for s in np.unique(data["seed"])}


def bootstrap_multiplicities(S, U, B=B_BOOT, seed=BOOT_SEED):
    """One shared draw sequence (S-7c): M[b, node] = multiplicity of node (s, X) in replicate b, by the E2-8 rule
    (draw_replicate from e2_evaluate.py; sum of X's counts over all occurrences of s)."""
    off, tot = {}, 0
    for s in S:
        off[s] = tot
        tot += len(U[s])
    rng = np.random.Generator(np.random.PCG64(seed))
    M = np.zeros((B, tot), dtype=np.int64)
    for b in range(B):
        _, occ = draw_replicate(rng, S, U)
        for s, nu in occ:
            if nu is not None:
                M[b, off[s]:off[s] + len(U[s])] += np.bincount(nu, minlength=len(U[s]))
    index = {(s, x): off[s] + i for s in S for i, x in enumerate(U[s])}
    return M, index


_W = {}


def _beta_chunk(bs):
    out = []
    for b in bs:
        w = _W["M"][b][_W["node"]].astype(float)
        try:
            fit = fit_logit(_W["stratum"], _W["ee"], _W["silent"], w, omit_single_outcome=True)
            out.append((b, fit["beta"], None, bool(fit["omitted_single_outcome_strata"])))
        except FitFailure as e:
            out.append((b, None, str(e), None))
    return out


def bootstrap_beta(stratum, ee, silent, node, M, workers=1, chunk=100):
    """beta* for every replicate (same draws for every point; S-8c in every replicate). Returns (beta*, number of
    replicates in which S-8c omitted at least one stratum). Results do not depend on `workers`."""
    _W.update({"stratum": stratum, "ee": ee, "silent": silent, "node": node, "M": M})
    chunks = [range(i, min(i + chunk, len(M))) for i in range(0, len(M), chunk)]
    if workers > 1:
        with multiprocessing.get_context("fork").Pool(workers) as pool:
            parts = pool.map(_beta_chunk, chunks)
    else:
        parts = [_beta_chunk(c) for c in chunks]
    res = [r for part in parts for r in part]
    for b, beta, err, _ in res:
        if err is not None:
            raise ReplicateFailure(f"bootstrap replicate {b + 1}: {err}; the beta interval is not evaluable under the "
                                   "frozen bootstrap specification (S-13b); OC-2 stops (not a substantive finding)")
    return np.array([r[1] for r in res]), int(sum(r[3] for r in res))


def bootstrap_or(stratum, exposed, silent, node, M, n_nodes, n_strata):
    """OR_MH* for every replicate: multiplicity-weighted cells (S-6a) from the shared draws. A single-outcome stratum
    contributes zero terms by the formula (S-6); a replicate stops only if sum_i b_i c_i / n_i = 0 or a value is
    non-finite (S-13b). Returns (OR_MH*, number of replicates with at least one positive-weight single-outcome stratum)."""
    cnode = mh_cells(node * n_strata + stratum, exposed, silent, None, n_nodes * n_strata)
    rep = (M.astype(float) @ cnode.reshape(n_nodes, n_strata * 4)).reshape(len(M), n_strata, 4)
    num, den = mh_num_den(rep)
    bad = np.flatnonzero((den == 0) | ~np.isfinite(num) | ~np.isfinite(den))
    if len(bad):
        raise ReplicateFailure(f"bootstrap replicate {bad[0] + 1}: Mantel-Haenszel odds ratio undefined; the OR interval "
                               "is not evaluable under the frozen bootstrap specification (S-13b); OC-2 stops "
                               "(not a substantive finding)")
    orr = num / den
    if not np.all(np.isfinite(orr)):
        raise ReplicateFailure("non-finite bootstrap odds ratio; interval not evaluable (S-13b); OC-2 stops")
    n_s = rep.sum(axis=-1)
    silent_w = rep[..., 0] + rep[..., 2]
    single = (n_s > 0) & ((silent_w == 0) | (silent_w == n_s))
    return orr, int(np.any(single, axis=-1).sum())


def interval(values):
    lo, hi = np.percentile(values, PCT, method="linear")
    if not (math.isfinite(lo) and math.isfinite(hi)):
        raise ReplicateFailure("non-finite interval endpoint; interval not evaluable (S-13b); OC-2 stops")
    return [float(lo), float(hi)]


# ---------------------------------------------------------------- §5: one active point ------------------------
def observed_relationship(stratum, ee, silent, n_strata):
    exposed = ee < XI
    try:
        cells = mh_cells(stratum, exposed, silent, None, n_strata)
        orr = mh_or(cells)
        fit = fit_logit(stratum, ee, silent)
    except FitFailure as e:
        raise ObservedFailure(f"observed data: {e} (S-13); OC-2 stops")
    return {"OR_MH": orr, "cells_by_stratum": cells.astype(int).tolist(), "beta": fit["beta"],
            "alpha_by_stratum": fit["alpha"], "irls_iterations": fit["iterations"]}


def s9_statement(rel_primary):
    """S-9 (descriptive rule): made only if every active point at k = 1.5 has OR lower > 1 and beta upper < 0."""
    if not rel_primary:
        return None
    return all(r["OR_MH_interval"][0] > 1.0 and r["beta_interval"][1] < 0.0 for r in rel_primary.values())


# ---------------------------------------------------------------- P-1: parity -----------------------------------
def parity_run(rundir, seed):
    """Compare logged first-hearing [EAQTE-CCQ] (= p(d) at 40 dB, k = 1.5) and [EAQTE-SS] (C++ input convention:
    X's two most recent decodes including the one being logged; own velocity row at floor(t)) with offline values,
    within 6-significant-digit print resolution. [EE]/[SSCCQ] are not compared."""
    _, _, mob = load_inputs(rundir, seed)
    vel = read_velocities(os.path.join(rundir, f"v1_{seed}_mobility.csv"))
    last, cur = {}, None
    st = {"ccq_compared": 0, "ss_compared": 0, "not_comparable": 0, "whole_second_mismatch": 0, "unexplained": []}
    with open(os.path.join(rundir, "stderr.log"), errors="ignore") as fh:
        for ln in fh:
            if ln.startswith("[RXHDR] "):
                k = dict(KV.findall(ln))
                node, tx, t, f = int(k["node"]), int(k["tx"]), float(k["t"]), vec(k["f"])
                cur = (node, tx, t, f, last.get((node, tx)))
                last[(node, tx)] = (t, f)
            elif ln.startswith("[EAQTE] TX "):
                cur = None                                               # origination at the source: no decode
            elif ln.startswith("[EAQTE-CCQ] ") or ln.startswith("[EAQTE-SS] "):
                k = dict(KV.findall(ln))
                is_ccq = ln.startswith("[EAQTE-CCQ] ")
                logged = float(k["CCQ" if is_ccq else "SS"])
                if cur is None:
                    st["not_comparable"] += 1
                    continue
                node, tx, t, f, prev = cur
                if int(k["neighbor"]) != tx:
                    st["unexplained"].append((seed, ln.strip(), "neighbor differs from the decoded transmitter"))
                    continue
                sec = int(math.floor(t))
                po, vo = mob.get(node, {}).get(sec), vel.get(node, {}).get(sec)
                if po is None or vo is None:
                    st["unexplained"].append((seed, ln.strip(), "no own mobility row"))
                    continue
                if is_ccq:
                    dd = math.sqrt((po[0] - f[0]) ** 2 + (po[1] - f[1]) ** 2 + (po[2] - f[2]) ** 2)
                    off = float(p_of_d(dd, PARITY_EBN0, PARITY_K))
                    st["ccq_compared"] += 1
                else:
                    vx, vy, h = neighbor_velocity(t, f, prev[0] if prev else None, prev[1] if prev else None)
                    off = float(ss_values(np.array([vo]), np.array([[vx, vy]]), np.array([h]))[0][0])
                    st["ss_compared"] += 1
                if abs(off - logged) > res6(logged) * (1.0 + 1e-9):     # 6-significant-digit print resolution
                    if abs(t - round(t)) < 1e-9:
                        st["whole_second_mismatch"] += 1
                    else:
                        st["unexplained"].append((seed, ln.strip(), f"offline {off!r} vs logged {logged!r}"))
    return st


def parity(runs_dirs):
    tot = {"ccq_compared": 0, "ss_compared": 0, "not_comparable": 0, "whole_second_mismatch": 0, "unexplained": []}
    for seed, rundir in runs_dirs:
        r = parity_run(rundir, seed)
        for k in tot:
            tot[k] = tot[k] + r[k]
    if tot["unexplained"]:
        raise Stop(f"P-1 parity: {len(tot['unexplained'])} unexplained mismatches, first {tot['unexplained'][0]}")
    tot["unexplained"] = 0
    return tot


# ---------------------------------------------------------------- evaluation ------------------------------------
def git(*a, cwd=REPO):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True).stdout.strip()


def frozen_calibration():
    cal = json.load(open(os.path.join(REPO, "analysis/stageE/e1/e1_calibration_rev4.json")))
    labels = sorted(set(cal["merge_map"].values()))
    lab = {c: labels.index(cal["merge_map"][name(c)]) for c in CELLS}
    return cal, lab, labels


def evaluate(root, seeds, dev, B=B_BOOT, workers=1):
    prov = {f: md5(os.path.join(REPO, f)) for f in FROZEN_MD5}
    bad = [f for f, h in FROZEN_MD5.items() if prov[f] != h]
    if bad:
        raise Stop(f"frozen inputs changed: {bad}")
    if not dev:
        for f in CODE_FILES:
            if git("ls-files", "--error-unmatch", f) != f or git("status", "--porcelain", "--", f):
                raise Stop(f"{f} is not committed and unmodified (R-1b)")
    cal, lab, labels = frozen_calibration()
    n_strata = len(labels)
    dirs = [(s, os.path.join(root, f"run_{s}")) for s in seeds]
    inputs = {}
    for s, rd in dirs:
        files = ["stderr.log", f"v1_{s}.tr", f"v1_{s}_mobility.csv", "e1_opportunities.csv"]
        if any(not os.path.exists(os.path.join(rd, f)) for f in files):
            raise Stop(f"{rd}: missing input files")
        inputs[f"run_{s}"] = {f: md5(os.path.join(rd, f)) for f in files}
        if not dev:
            rec = cal["inputs_md5"][str(s)]
            for f, h in rec.items():
                if inputs[f"run_{s}"].get(f) != h:
                    raise Stop(f"run_{s}/{f} md5 differs from e1_calibration_rev4.json (§2)")
    runs = [load_run(rd, s, lab) for s, rd in dirs]
    data = concat_runs(runs)
    ms = data["out"] != OUTCOME["OTHER-UP"]
    if not dev:                                                          # consistency with the frozen calibration
        if int(ms.sum()) != sum(cal["cell_counts"].values()):
            raise Stop("MATCH+SILENT count differs from the frozen calibration cell counts")
    par = parity(dirs)                                                   # P-1 before any result

    ss, ss_default = ss_values(data["vi"], data["vj"], data["has_vj"])
    lags = history_lags(data["seed"], data["o"], data["x"])
    ks = (K_PRIMARY,) + K_SECONDARY
    points, ee_ms = {}, {}
    for k in ks:
        for g in GRID:
            p = p_of_d(data["d"], g, k)
            ccq = ccq_from_history(p, lags)
            ee, freeze = ee_and_freeze(ccq, ss)
            points[(k, g)] = characterize(data, ee, ccq, ss, freeze, ss_default)
            if not dev and k == K_PRIMARY and g == GRID[0] and points[(k, g)]["arm_a_judged_pairs"] != cal["pairs_ge_n_ref"]:
                raise Stop("Arm-A judged pairs differ from the frozen calibration (pairs_ge_n_ref)")
            if points[(k, g)]["active"]:
                ee_ms[(k, g)] = ee[ms]
    stratum, silent = data["stratum"][ms], data["out"][ms] == OUTCOME["SILENT"]
    observed = {kg: observed_relationship(stratum, e, silent, n_strata) for kg, e in ee_ms.items()}   # S-13 first

    S = list(seeds)
    U = node_universe(data)
    for s in S:
        U.setdefault(s, [])
    M, index = bootstrap_multiplicities(S, U, B=B)                        # S-7c: once, shared
    node = np.array([index[(int(s), int(x))] for s, x in zip(data["seed"][ms], data["x"][ms])])
    for kg, e in ee_ms.items():
        orr, n_or = bootstrap_or(stratum, e < XI, silent, node, M, M.shape[1], n_strata)
        beta, n_beta = bootstrap_beta(stratum, e, silent, node, M, workers=workers)
        observed[kg]["OR_MH_interval"] = interval(orr)
        observed[kg]["beta_interval"] = interval(beta)
        observed[kg]["replicates_with_single_outcome_strata"] = {"OR_MH": n_or, "beta": n_beta}   # S-13b transparency

    def table(k):
        return {f"{g:g}": dict(points[(k, g)], relationship=observed.get((k, g))) for g in GRID}

    prim_rel = {g: observed[(K_PRIMARY, g)] for g in GRID if (K_PRIMARY, g) in observed}
    act = activity_finding({g: points[(K_PRIMARY, g)] for g in GRID})
    secondary = {}
    for k in K_SECONDARY:
        rel_k = {g: observed[(k, g)] for g in GRID if (k, g) in observed}
        secondary[f"secondary (k = {k:g})"] = {
            "points": table(k), "any_active": any(points[(k, g)]["active"] for g in GRID),
            "relationship": "not evaluable (no active value)" if not rel_k else "reported per active point"}
    return {
        "spec": "analysis/stageE/OC2_SPEC.md revision 2 (frozen at commit a984fc7; D-23, D-24)",
        "status": ("DEVELOPMENT ONLY - not OC-2; no finding" if dev else
                   "OC-2 offline operating characterization of the EAQTE environment gate (descriptive only)"),
        "limitation": ("offline rescoring of the fixed 40-dB E1 traces across the Eb/N0 scoring grid; not newly "
                       "simulated network behavior at those Eb/N0 values"),
        "created_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seeds": S, "root": root,
        "frozen": {"grid_db": list(GRID), "k_primary": K_PRIMARY, "k_secondary": list(K_SECONDARY), "xi": XI,
                   "history_window": HIST_WINDOW, "n_ref": N_REF, "B": B, "generator": "numpy.random.PCG64",
                   "bootstrap_seed": BOOT_SEED, "percentiles": list(PCT), "percentile_method": "linear",
                   "irls": {"max_iterations": IRLS_MAX_IT, "tol": IRLS_TOL, "separation_eps": SEP_EPS,
                            "condition_max": COND_MAX},
                   "bins": {"SS_CCQ_width": 0.1, "EE_width": 0.05}, "strata": labels},
        "parity": par,
        "primary (k = 1.5)": {"points": table(K_PRIMARY), "activity_finding": act,
                              "active_values_db": [g for g in GRID if points[(K_PRIMARY, g)]["active"]],
                              "s9_statement": s9_statement(prim_rel),
                              "relationship": "not evaluable (no active value)" if not prim_rel else "reported per active point"},
        **secondary,
        "bootstrap": {"node_universe_sizes": {str(s): len(U[s]) for s in S}, "shared_draws": True},
        "provenance": {"frozen_md5": prov, "inputs_md5": inputs,
                       "code_md5": {f: md5(os.path.join(REPO, f)) for f in CODE_FILES if os.path.exists(os.path.join(REPO, f))},
                       "parent_commit": git("rev-parse", "HEAD"),
                       "submodule_commit": git("-C", "src/aqua-sim-ng", "rev-parse", "HEAD"),
                       "python": platform.python_version(), "numpy": np.__version__}}


def report(res):
    L = [f"Stage E OC-2 - {res['status']}", f"Specification: {res['spec']}; seeds {res['seeds']}; created {res['created_utc']}",
         f"Limitation: {res['limitation']}", "",
         f"P-1 parity: CCQ {res['parity']['ccq_compared']}, SS {res['parity']['ss_compared']} compared; "
         f"not comparable {res['parity']['not_comparable']}; whole-second {res['parity']['whole_second_mismatch']}; unexplained 0", ""]
    for key in ["primary (k = 1.5)"] + [k for k in res if k.startswith("secondary")]:
        L.append(key)
        for g, pt in res[key]["points"].items():
            reg = "active" if pt["active"] else ("inert" if pt["inert"] else "saturated")
            line = (f"  {g:>5} dB: freeze {pt['frozen_match_silent']}/{pt['n_match_silent']} (all {pt['frozen_all']}/{pt['n_all']}); "
                    f"judged A {pt['arm_a_judged_pairs']} B {pt['arm_b_judged_pairs']}; {reg}")
            r = pt["relationship"]
            if r:
                line += (f"; OR_MH {r['OR_MH']:.4f} [{r['OR_MH_interval'][0]:.4f}, {r['OR_MH_interval'][1]:.4f}]; "
                         f"beta {r['beta']:.4f} [{r['beta_interval'][0]:.4f}, {r['beta_interval'][1]:.4f}]; "
                         f"replicates with single-outcome strata: OR {r['replicates_with_single_outcome_strata']['OR_MH']}, "
                         f"beta {r['replicates_with_single_outcome_strata']['beta']}")
            L.append(line)
    p = res["primary (k = 1.5)"]
    L += ["", f"Activity finding (k = 1.5): {p['activity_finding']}; active values {p['active_values_db']}",
          f"S-9 descriptive statement: {p['s9_statement']}",
          "Descriptive only; not a gate; no secure-routing, G5/G6 or PACT claim."]
    return "\n".join(L) + "\n"


def main(argv):
    args = list(argv)
    opt = lambda k: (args[args.index(k) + 1] if k in args else None)
    dev = "--dev" in args
    root = os.path.abspath(os.path.expanduser(opt("--e1-root") or "~/uwsn-runs/stageE/E1"))
    out = opt("--out") or (None if dev else HERE)
    workers = int(opt("--workers") or 1)
    if out is None:
        raise SystemExit(__doc__)
    out = os.path.abspath(os.path.expanduser(out))
    if dev:
        if opt("--seeds") is None:
            raise SystemExit("--dev requires --seeds")
        seeds = tuple(int(s) for s in opt("--seeds").split(","))
        B = int(opt("--B") or B_BOOT)
        if os.path.commonpath([out, HERE]) == HERE:
            raise SystemExit("development output must not be written inside analysis/stageE/oc2")
    else:
        if "--seeds" in args or "--B" in args:
            raise SystemExit("OC-2 seeds (12-21) and B (10,000) are fixed; --seeds/--B are development only")
        seeds, B = SEEDS_OC2, B_BOOT
    targets = [os.path.join(out, OUT_JSON), os.path.join(out, OUT_REPORT)]
    if any(os.path.exists(t) for t in targets):
        raise SystemExit(f"{out} already holds OC-2 outputs; refusing to overwrite (R-1)")
    try:
        res = evaluate(root, seeds, dev, B=B, workers=workers)
    except Stop as e:
        print(f"STOP (OC-2 not completed; no result file written): {e}", file=sys.stderr)
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
