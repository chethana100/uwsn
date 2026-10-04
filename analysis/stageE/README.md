# Stage E — frozen specification (pre-implementation)

**Status.**
- **Revision 3** (2026-10-04). It supersedes revision 2, which was frozen at commit `c0d2cec`. Revision 3 is frozen when it is committed. Revision history is in §14; every revision-2 passage that revision 3 replaces is kept verbatim in §17.
- **E1 was run under revision 2 and failed G1** (V3 separation; V6 false-alarm rate). The historical record is commit `58cc50c` and `../../EXPERIMENT_LOG.md` E-32; its files are kept unchanged.
- Revision 3 changes only the O2 calibration (§7 steps 3–6 and freezing), V3, V5 and V6. **No revision-3 code exists yet, and E1 has not been re-evaluated under revision 3.**
- The logging-only `[RXHDR]` change and its validation are in §15 (`../../EXPERIMENT_LOG.md` E-31).

**Change control.**
- This document is the reference for E1–E5.
- Any change after freezing must be a separately approved, dated revision recorded in §14. Never edit silently.
- The open points P1–P4 were resolved in revision 2. Open point P5 (Arm B/C binning) must be resolved before E3 (§13).
- The final pre-implementation consistency check (2026-10-04) produced three corrections (C1–C3). They are folded into §6 and §8 and marked where they apply.

Contents:
1. Source layers
2. Arms
3. Scope constraints S1, S2
4. Seed allocation
5. Information boundary
6. O1: opportunity construction
7. O2: per-pair statistic and frozen baseline
8. Common evidence layer per arm
9. Observability ceiling (p = 1.0)
10. EAQTE operating-point grid
11. Experiment sequence E1–E5
12. Decision gates G1–G6
13. Open points and revision-3 decisions
14. Revision log
15. D1(ii) `[RXHDR]` validation
16. EAQTE Eb/N0 landmark arithmetic
17. Superseded revision-2 text (verbatim)

---

## 1. Source layers

Every item used in Stage E belongs to exactly one layer. Never attribute an item to a layer that does not state it.

| Layer | Items used in Stage E |
|---|---|
| **Published HH-VBF** (Nicolaou et al.) | Hop-by-hop routing pipe from the previous forwarder toward the target.<br>Desirableness α′ = (R − d·cosθ)/R (Def. 2).<br>Holding time "computed the same way as in VBF"; the formula T = √α·T_delay + (R − d)/v₀ comes from VBF 2006, which is not in the attached set.<br>Receiver-based forwarding with no named next hop and no location exchange (project record).<br>Broadcast MAC: back off, drop after 4 attempts.<br>Duplicate suppression by β distance plus "self-adaptation", with the combination under-specified. |
| **EAQTE specification** (Khoshvaght et al. 2026) | Eqs. 6–10: spreading/Thorp → SNR = (Eb/N0)/A → BPSK-Rayleigh BER → p = (1 − Pe)^m.<br>Eqs. 14–17: variance of p. Eq. 18: CCQ = p(1 − tanh var).<br>Eqs. 25–26: SS = ½(1 + cos) on 2D velocity. EE = ψ·CCQ + (1 − ψ)·SS with **ψ = 0.5**.<br>Freeze when **EE < ξ_th = 0.3**, applied per time slot to direct trust (Eq. 41).<br>k ∈ [1, 2]. MCM Eqs. 1–5. §3.1: nodes exchange location.<br>**Not specified by EAQTE:** Eb/N0, f, the exact k, units of d and A0, m, n_p and its sampling, slot length. |
| **Aqua-Sim-NG implementation** | `AquaSimVBF` α = p/W + (R − d·cosθ)/R (VBF Def. 1). Self-adaptation thresholds 1.5 and 1.5/2^(n−1). `MAX_NEIGHBOR` 10. `DELAY` = 1.0 s.<br>`AquaSimRangePropagation` (decoding is distance-independent within range).<br>VBHeader serializes positions to the mm. `d` wraps as uint32 when negative.<br>VBHeader `token`, `ts`, `range` are uninitialised (§15).<br>`AquaSimBroadcastMac`. Trace `r` fires only for packets that passed the collision check. |
| **Project choices** | `AquaSimTrustQVBF` subclass. W = 400 m, R = 1000 m. MCM at a fixed 0.3 m/s. Sink fixed. Pinned RNG streams.<br>Range propagation everywhere (D-01). Published hold time with α′ for the hold only; Aqua-Sim α for the thresholds (D-06, D-07).<br>Borrowed EAQTE constants: f = 25 kHz (EAQTE ref [48]) and k = 1.5 (ref [47] / DOIDS). Own choices: m = 640 bits; Eb/N0, previously fixed at 40 dB and swept in Stage E (§10).<br>Overhearing observer. ε = 25 m, 60 s freshness, 8 s timing rule. Strata, bars and seeds.<br>Attacker models (`AttackMode` 0/1, `AdversarialMotion`). `[DIAG]` and `[RXHDR]` logging. S1/S2. |
| **Research contribution** (as recorded; no effectiveness claimed) | Oracle-free, opportunity-conditioned evidence layer (D-04, D-13).<br>The EAQTE → environment-masked attack → PACT question.<br>PACT = Peer-referenced Attenuated Continuous Trust (S-07), used **unchanged**.<br>Observability-ceiling reporting. |

## 2. Arms (mandatory labels everywhere)

| Arm | Definition |
|---|---|
| **Arm 0** | plain HH-VBF |
| **Arm A** | observer-based trust, **no** environmental gate |
| **Arm B** | observer-based trust + **EAQTE gate** |
| **Arm C** | observer-based trust + **PACT** |

Opportunity construction (O1), outcomes, strata and the frozen baseline (O2) are **identical** in Arms A, B and C. EAQTE and PACT may only change how an otherwise valid opportunity is weighted or excluded (§8).

## 3. Scope constraints

**S1.** For all of E1–E5:
- `PriorityScale = 0` and `ObservedTrustWeight = 0`. Trust never affects forwarding or routing.
- Arms 0, A, B and C therefore share identical packet traces.
- Arms A, B and C are evaluated by **offline replay on identical traces**.
- E1–E5 are **security-mechanism validation only**. They must not be described as showing that observer trust improves HH-VBF forwarding performance. Trust-driven routing is a later, separate stage.

**S2.**
- One approved logging-only C++ change is permitted, solely to expose the exact receiver-decoded header fields (`[RXHDR]`, submodule `41c67c3`).
- No behaviour-changing C++ changes are permitted during E1–E5.
- The legacy custody-tag observer stays in the code, untouched, and plays no part in any Stage E arm.

## 4. Seed allocation

| Seeds | Use |
|---|---|
| 12–21 | Clean calibration (E1, E3; all thresholds) |
| 2–11 | E2 held-out observer test |
| 22–31 | E4 attacker arms |
| 41–50 | E5 confirmatory |
| 1 | Development only (never used for calibration or thresholds) |
| 32–40 | Unused (D-08) |

## 5. Information boundary

**Observer evidence.** O may use only these:

| Source | What O may use |
|---|---|
| `[RXHDR]` lines where `node` = O (copies O decoded) | tx, src, pk, f, d (unwrapped: v > 2147483.648 ⇒ v − 4294967.296), tgt, reception time t |
| O's own information | own position and velocity at an event (the mobility-log rows for O only); own transmissions = O's own trace `t` records (the header O itself serialized, printed to 6 significant digits; see §6 step 1) |
| O's neighbour table | per node Y: last and previous f with heard-times, from copies O decoded **strictly before** the event |
| Public protocol constants | R = 1000 m, W = 400 m, m_priority = 1.5, T_delay = 1.0 s, v₀ = 1500 m/s |

**Ground truth only.** Used for evaluation labels; never observer input:
- the **custody tag**;
- `[DECISION]`, `[HOLD]`, `[VERDICT]`, `[OBSERVER] DROP`;
- the malicious list;
- other nodes' true positions (other nodes' mobility-log rows);
- every reception or transmission O did not decode.

**Code rule.** Ground-truth fields live in an evaluation module the observer module cannot import. E1 check V5 audits this statically.

## 6. O1: opportunity construction

O1 is exactly as validated in Stage D. **O1-H (self-transmission exclusion) is OFF.**

1. **Source event at t₀.**
   - Either O decodes U's copy c of packet (s, p), with f_U = c's decoded f;
   - or O itself transmits P. Then O = U; f_U is the f in O's own trace `t` record of that transmission, and t₀ is that record's time.
     - Both are printed to 6 significant digits (f within ±0.005 m, t₀ within ±0.005 s when t ≥ 1000 s). This cannot change any outcome: ε = 25 m, recovery error ≤ 0.601 m, nearest other transmitter ≥ 136 m.
     - Tie rule: a copy O decoded counts as "before" this event only if its `[RXHDR]` time is less than t₀ − res6(t₀), where res6 is half a unit in the 6th significant digit. E1 reports how many decodes fall within ±res6(t₀).
     - Receivers' `[RXHDR]` records of O's transmission are never an observer source; they are used only in check V8.
   - Each distinct upstream copy O decodes is its own source event.
2. **Candidates.** X is a candidate if:
   - X is in O's table;
   - X was last heard ≤ **60 s** before t₀;
   - X ∉ {O, U, sink, s}.
3. **Eligibility,** estimated from X's last-known position x. All three must hold:
   - |x − f_U| ≤ R;
   - the perpendicular distance from x to the line f_U → t is ≤ W;
   - **Aqua-Sim α**(x) = projection/W + (R − D·cosθ)/R ≤ 1.5, with D = |x − f_U| and θ the angle between x − f_U and t − f_U. This is the single-copy rule, deviation D-07.
4. **Ranking (C3).**
   - α′ = (R − D·cosθ)/R (HH-VBF Def. 2).
   - Hold time T(x) = √max(0, α′)·T_delay + (R − D)/v₀.
   - Rank X among **all** eligible candidates, **before** the hearing filter in step 5.
   - The rank is used only to set stratum K2.
5. **Hearing filter.** |pos_O(t₀) − x| ≤ R.
6. **Outcome, by the Stage D rule (C3).**
   - **MATCH:** O decodes, at any time in the run, a copy of (s, p) transmitted by X whose recovered upstream û = f_X − unwrap(d_X) satisfies |û − f_U| ≤ **ε = 25 m**.
   - **OTHER-UP:** O decodes X's copy but |û − f_U| > 25 m. Excluded: never blamed, never credited.
   - **SILENT:** O decodes no copy of P from X.
7. **8 s timing rule (C3).**
   - Updates are timestamped at the response's reception time (MATCH, OTHER-UP) or at t₀ + 8 s (SILENT). These timestamps serve only the secondary time-to-flag measure.
   - 8 s is the existing C++ watch window. It exceeds the analytic maximum: about 2.08 s hold (√2 + 0.667) + ≤ 0.67 s propagation + ≤ 0.4 s MAC backoff.
   - E1 check V4 reports any response that arrives after t₀ + 8 s. **The Stage D outcome governs either way.**

## 7. O2: per-pair statistic and frozen baseline

**Unit of judgement.** The observer–neighbour pair (O, X). Trust is a local belief; node-level summaries are secondary.

**Strata.** Observable features only. They handle geometry and rank differences.

| Stratum | Levels |
|---|---|
| K1: role | O = U, or O ≠ U |
| K2: predicted α′ rank of X | 1, 2, or ≥ 3 |
| K3: age of X's table entry at t₀ | ≤ 20 s, 20–40 s, 40–60 s |

That is 18 cells.
- **Minimum cell size N_s = 2,401** calibration opportunities: the worst-case (q = 0.5) size for a ±0.02 half-width at 95% confidence.
- ±0.02 is under one tenth of the smallest effect to be detected: p_min·(1 − q) ≥ 0.15 for any q ≤ 0.8.
- **Merge rule** for an undersized cell: merge K3 levels first, then merge rank 2 with ≥ 3.

**Per opportunity i of pair (O, X):**
- y_i = 1 for SILENT, 0 for MATCH. OTHER-UP is excluded.
- w_i is the arm weight (§8).
- n_eff = (Σw)² / Σw².

**Statistic:**

  **Z = Σ w_i (y_i − q_{s_i}) / √( Σ w_i² q_{s_i} (1 − q_{s_i}) )**

**Calibration (E1),** from clean seeds **12–21** only (all nodes honest), with Arm A weights (w = 1).
A pair is (seed, O, X); pairs never span seeds. The procedure is deterministic and uses no attacker data.

1. **Stratum rates.** Apply the merge rule, then q_s = SILENT ÷ (MATCH + SILENT) per merged stratum.
   If any merged stratum has q_s ∈ {0, 1}, E1 stops and reports; no smoothing.
2. **Reference size n_ref** (fixed before τ_A and independent of power):
   - q̄ = pooled SILENT ÷ (MATCH + SILENT) over all calibration opportunities.
   - n_ref = ⌈5 / min(q̄, 1 − q̄)⌉. This is the standard normal-approximation convention that both
     outcomes have an expected count of at least 5.
3. **n-bins and per-bin thresholds τ_A,b** (revision 3). Z is unchanged; the threshold now depends on n,
   because honest silence propensity is persistent per pair and var(Z) grows with n (E-32: var(Z) 10.5 at
   n 14–27, 40.3 at n ≥ 70).
   - **Reference set:** the honest calibration pairs with n ≥ n_ref (Arm A, so n is an integer).
   - **Construction:**
     1. Let v₁ < v₂ < … < v_m be the distinct values of n in the reference set, with c_j pairs at v_j.
     2. Scan v₁, v₂, … in ascending order, adding the whole group of pairs at each value to the current bin.
        **Pairs with equal n are never split between bins.** As soon as the current bin holds at least
        **M = 200** pairs, close it. Start the next bin at the next distinct value.
     3. After the scan, if the last bin holds fewer than M pairs and there is an earlier bin, merge it into
        the immediately preceding bin. If there is only one bin, keep it whatever its size and report its size.
   - **Edges and interval convention:**
     - L₁ = n_ref. For b ≥ 2, L_b = the smallest n in bin b.
     - Bin b covers the half-open interval [L_b, L_{b+1}). The last bin K covers [L_K, ∞).
     - Every pair with n ≥ n_ref therefore falls in exactly one bin, including n values not seen in
       calibration and n above the calibration maximum.
     - Pairs with n < n_ref fall in no bin: they are not judged and are not part of the reference set.
   - **Thresholds:** τ_A,b = Z₍⌈0.95·N_b⌉₎, the nearest rank among the N_b reference pairs in bin b, sorted
     ascending. A pair is flagged when Z > τ_A,b for the bin whose interval contains its n.
   - The threshold is empirically calibrated within each bin at the nominal 0.05 level; nearest rank does not
     guarantee an exact 0.05 false-alarm rate. Transfer of that calibration to unseen seeds is tested by V6,
     with seeds 2–11 providing the independent G2b assessment.
   - Bins may hold more than M pairs, because ties are kept together. Each bin's size is reported.
4. **Power by thinning, then n_min,** with every τ_A,b already fixed:
   - One generator, NumPy PCG64 seed 12345 (= BASE_SEED); bins in ascending order. For bin b:
     1. Draw R = 10,000 indices uniformly with replacement from the bin's pairs, ordered by (seed, O, X).
     2. Then, in replicate order and in each pair's stored opportunity order, draw one uniform per MATCH
        opportunity. A MATCH becomes SILENT when its uniform is < p_min = 0.75. This is the declared attacker,
        q₁ = 1 − (1 − q)(1 − p_min), applied to real honest pairs, so their heterogeneity is kept.
     3. Compute Z with the calibration q_s. power_b = the fraction with Z > τ_A,b.
   - **n_min** = L_b of the smallest bin with power_b ≥ 0.80. This lower edge is n_ref when the qualifying
     bin is bin 1. Power is not assumed to be monotone in n; the definition still takes the smallest
     qualifying bin, and every bin's power is reported.
   - **If no bin reaches power_b ≥ 0.80, n_min is undefined and G1 fails.** No adjustment is permitted:
     n_min is not replaced by n_ref or any other value, and neither the 0.80 target nor p_min may be
     changed. Failing to reach the declared power is recorded as a methodological result.
5. **Reported, never tuned:** the bin edges and sizes; τ_A,b; the calibration FA per bin and among honest
   pairs with n ≥ n_min; power_b per bin; the over-dispersion of Z, overall and per bin.
   - **Diagnostic only:** the model-based power ceiling — about 0.41 under Beta(0.90, 1.48) honest
     heterogeneity (strata only, p_min = 0.75, FA 0.05; derived from the E1 clean data). It is reported and
     never used to change G1, the 0.80 target or p_min.
6. **Other arms.** τ_B,b and τ_C,b use the step-3 nearest-rank rule with their own weights (n_eff in place
   of n) on the same clean seeds. **How the bins are formed for n_eff is open point P5 (§13), to be decided
   before E3.** n_min is common to all arms (Arm A's, from step 4), applied to n_eff.

Pairs with n_eff < n_min are **"not judged"**. They are never counted as negatives.

**Status of this calibration (revision 3).**
- Revision 3 was designed after inspecting the clean E1 data (seeds 12–21). Its calibration and V6 on those
  seeds are therefore **recalibration and development validation**, not an independent test.
- **The independent false-alarm assessment is the held-out honest data from seeds 2–11, under G2b.**
- No attacker data is used to determine q_s, n_ref, bins, thresholds or n_min.

**Freezing.** Before any attacker run is generated, write one versioned JSON file,
`e1/e1_calibration_rev3.json`, containing: q_s and the merge map; q̄ and n_ref; M, the bin edges L_b and
sizes N_b; τ_A,b per bin; power_b per bin; n_min (or "undefined"); the RNG specification (NumPy PCG64,
seed 12345, R = 10,000, draw order as in step 4); the md5 of every calibration run's `stderr.log`,
`v1_N.tr` and `e1_opportunities.csv`; the code commit hashes and the md5 of the calibration scripts.
Record the file's md5 in `../../EXPERIMENT_LOG.md`. The revision-2 file `e1/e1_calibration.json` is kept
unchanged as the historical record.

**Evaluation labels** (ground truth, evaluation only):
- **active malicious:** X configured malicious with ≥ 1 ground-truth drop;
- **honest:** X not configured malicious;
- **inactive malicious:** configured but never dropped. Excluded from TDR and FA, and listed in the ceiling table.

**Bars,** fixed before any attacker run:
- **False alarm: 5% per pair.**
  - Justification: the convention, and continuity with the project's earlier rule (flow-level detector threshold = 95th percentile of clean scores).
  - Held-out pass: FA on honest pairs in held-out attacker runs is **not significantly above 0.05** (one-sided, cluster bootstrap).
- **Detection.** All three must hold:
  - AUC (Z as score, over judged pairs) **≥ 0.70**. This reuses the project's earlier pre-set observer bar (`../../PROJECT_HANDOFF.md` §6.2).
  - The AUC's 95% lower bound > 0.5.
  - The TDR at the per-bin thresholds τ_A,b has a 95% lower bound **above** the FA upper bound.
- **CIs:** cluster bootstrap, resampling seeds, then nodes within seeds.

## 8. Common evidence layer per arm

| Arm | w_i | Threshold |
|---|---|---|
| A | 1 | τ_A,b |
| B | 0 if EE_{O,X}(t₀) < 0.3, otherwise 1 (the published freeze, applied per opportunity as a stand-in for the per-slot gate; a gated opportunity is excluded) | τ_B,b(Eb/N0) |
| C | min(1, EE_X / median EE of O's peers): the existing PACT formula (S-07), unchanged | τ_C,b(Eb/N0) |

**EE,** computed by O at t₀ with the coded equations (ξ = 0.3, ψ = 0.5, history window 10):
- **CCQ:** from |pos_O(t₀) − x|. The p-history gains **one sample per (O, X) per opportunity event, in every arm.** This fixes the C++ sampling confound.
- **SS:** O's own velocity, against X's velocity estimated from X's last two overheard positions (dt ≥ 0.05 s; otherwise SS = 0.5).

**PACT peers (C2).**
- The peer set is **all** entries in O's table except X, with no freshness filter, exactly as in the C++.
- Fewer than 2 peers → use X's own EE.
- Median ≤ 1e-9 → weight 1.

**Peer evaluation is read-only (C1).**
- A peer's EE uses its stored history plus its current p, but stores nothing.
- So the p-history is identical in Arms B and C.

**Thresholds.** τ_B,b and τ_C,b use the per-bin nearest-rank rule of §7 step 3 on the same clean seeds 12–21, per grid point; how their bins are formed for n_eff is open point P5. Arms are therefore compared at equal false-alarm rate on clean runs.

**Trust update.**
- Each pair's sufficient statistics (Σw(y − q), Σw²q(1 − q), Σw, Σw²) are updated. The trust state is Z.
- The legacy EWMA trust (TrustDecay) is not part of Stage E.
- EAQTE's b = s/(s + f + 1) may be reported as a secondary descriptive figure.

**Leakage rule.**
- **Arm C is not computed on any attacker seed (2–11 or 22–31) until E5 confirmatory validation on 41–50 is complete.**
- τ_C is calibrated on clean seeds 12–21 when E5 is prepared.

## 9. Observability ceiling (p = 1.0)

The ceiling is reported per run and per arm, separately from detection metrics.

1. **Drops observable:** the fraction of ground-truth drops with ≥ 1 valid opportunity, split O = U / O ≠ U. For Arms B and C, also the fraction with ≥ 1 opportunity of weight > 0.
2. **Active malicious nodes,** each classified as:
   - **unobservable:** zero opportunities at any observer;
   - **observable but insufficient:** no pair reaches n_eff ≥ n_min;
   - **judged:** then either detected or missed.
3. **Honest nodes:** the fraction judged.

**Rules:**
- Only **judged and missed** counts as a false negative of the trust algorithm.
- Unobservable and insufficient cases are **evidence limits, never algorithm errors**.
- Coverage = TDR × fraction judged is reported separately, labelled as system coverage.
- **p = 1.0 runs appear only in the ceiling table.** Stage D: 0/218 drops were observable; the droppers never transmitted.

## 10. EAQTE operating-point grid

**Eb/N0 grid, fixed:**

**{15, 20, 24.5, 27.5, 31.1, 34.5, 37.5, 40, 45, 50} dB**

| Value | Role |
|---|---|
| 15 | Beyond the saturated end |
| 20 | The original pre-recalibration value |
| **24.5** | Landmark: freeze feasible at 1 km when SS = 0.5 |
| 27.5 | Midpoint |
| **31.1** | Landmark: SS = 0, var = 0 |
| **34.5** | Landmark: worst case, SS = 0, var = ¼ |
| 37.5 | Midpoint |
| **40** | Previous value (gate inert) |
| 45, 50 | Beyond the inert end |

- The landmarks are computed from f = 25 kHz, m = 640 bits, R = 1000 m (k has no effect at exactly 1 km). The derivation is in §16; it uses no outcome data.
- **Fixed:** ξ = 0.3, ψ = 0.5, f = 25 kHz, m = 640.
- **Secondary, one at a time:** k ∈ {1.0, 2.0}, the ends of the published range.
- Under S1, Eb/N0 changes only the offline EE computation. Every grid point replays the same traces.

**Regimes,** from clean seeds 12–21 only:
- **Inert:** zero freezes across all calibration opportunities.
- **Saturated:** Arm B judges fewer than half the honest pairs that Arm A judges (majority convention).
- **Active:** everything else.

**Rules:**
- Gate activity is measured on clean runs first (E3).
- Results for Arms B and C are reported at **every** active grid point, with Holm correction across grid points.
- **No regime or Eb/N0 value is selected afterwards, and none for a favourable PACT result.**

## 11. Experiment sequence

Each stage ends with a stop-and-report.

| Stage | Content | Seeds |
|---|---|---|
| **E1** | Clean simulation runs; offline O1/O2; checks V1–V8 (G1); calibrate and freeze q_s, merge map, bins, τ_A,b, n_min. Under revision 3, E1 is re-evaluated from the existing E1 simulation outputs and O1 opportunity files; nothing is re-simulated | 12–21 |
| **E2** | **Arm A only** (no EAQTE, no PACT); naive attacker at p = 0.75, plus p = 1.0 for the ceiling table only; FA, AUC, TDR, observability | 2–11 |
| **E3** | Offline replay of the EAQTE gate on the E1 traces across the grid: freeze fraction, joint SS/CCQ distribution, regimes, τ_B,b per grid point (binning: P5); evidence/EE causal test (G4) | 12–21 |
| **E4** | Only if G1–G4 pass. Arms A and B against three attackers (below); blind-spot test at every active grid point | 22–31 |
| **E5** | Only if G5 passes. PACT offline (existing formula, no tuning), Arm C vs B vs A at the grid points where G5 passed | 41–50 |

**E4 attackers:**
- `AttackMode=1` (environment-masked);
- `AdversarialMotion`;
- a matched plain control with the same nominal attack parameters (AttackMode=0, dropProbability=0.75, adversarialMotion=false). This replaces the earlier rule that matched the control to the masked attacker's realised drops per forwarding win (revision 2).

**Attacker configuration.**

| Setting | E1, E3 (clean) | E2 | E4 `AttackMode=1` arm | E4 AdversarialMotion arm | E4 matched plain |
|---|---|---|---|---|---|
| attackerFraction | 0 | 0.2 | 0.2 | 0.2 | 0.2 |
| AttackStart | — | 0 | 0 | 0 | 0 |
| AttackMode | — | 0 | 1 | 0 | 0 |
| dropProbability | — | 0.75 (plus 1.0 for the ceiling table only) | 0.75 | 0.75 | 0.75 |
| adversarialMotion | false | false | false | true (1.5 s reversal at each drop, fixed in code) | false |

- attackerFraction 0.2 and AttackStart 0 are established by Stage D (E-27 metadata).
- The historical 500 s onset belonged to the flow-level detector and does not apply here.
- The AdversarialMotion arm uses AttackMode=0 so that it isolates the motion mechanism rather than combining two attack mechanisms.
- `_meta.csv` does not record `adversarialMotion`. Run-directory names and the `EXPERIMENT_LOG.md`
  command lines must record it; the scenario is not changed (S2).

**E5 grid points** come from G5, which compares Arm B with Arm A and **never** involves Arm C.

## 12. Decision gates and predefined failure conclusions

**G1: Evidence-layer validity (E1).** Fails if any check fails.

| Check | Requirement |
|---|---|
| V1 | MATCH = 100% FWD_TX. Any exception must be individually explained |
| V2 | OTHER-UP = 100% DIFF_UP |
| V3 | Upstream recovery error ≤ 12.5 m (the Stage D acceptance rule); minimum separation between a recovered upstream and any other transmitter of the same packet **> ε + 12.5 m = 37.5 m** (revision 3). This is the smallest separation at which every recovery error within the accepted bound still classifies correctly: f_U is decoded exactly, so only û carries error. Separations below 2ε = 50 m are reported descriptively |
| V4 | Responses arriving after t₀ + 8 s are reported (none expected) |
| V5 | Static audit: no ground-truth field reachable from observer code. Revision 3: the audit also covers the revision-3 calibration script |
| V6 | Leave-one-seed-out: for each seed in 12–21, rerun §7 steps 1–4 (stratum rates, n_ref, bins, τ_A,b, power by thinning, n_min) on the other nine seeds with the identical deterministic procedure and that fold's own n_ref; assign the left-out seed's pairs by that fold's intervals; measure FA on its judged honest pairs. Pooled FA is not significantly above 0.05 (one-sided; cluster bootstrap over seeds, then nodes; B = 10,000, NumPy PCG64 seed 12345 — fixed reproducibility parameters of revision 3, not tunable from V6 results). FA per bin per fold is reported. **This is recalibration and development validation (§7); the independent false-alarm assessment is G2b on seeds 2–11** |
| V7 | Offline p(d) agrees with the C++ values logged where the history has < 2 samples (there CCQ = p) |
| V8 | (Evaluation only.) For every transmission decoded by at least one receiver, the f in the transmitter's own `t` record agrees with the receivers' `[RXHDR]` f within print resolution |

- **If G1 fails:** the evidence layer is invalid. Stop and report. Fix it in a new, separately approved design. No later stage runs.

**G2: Observability sufficiency (E2).**
- Requires **≥ 43 judged malicious pairs** (TDR 95% CI half-width ≤ 0.15) **and ≥ 10 distinct judged malicious nodes**.
- **If G2 fails:** conclusion: "With overhearing-only evidence in beaconless HH-VBF, the attacker is not observable often enough to evaluate trust." That is a finding, not an algorithm failure.
  - One extension to further held-out seeds is allowed. It needs a seed allocation approved at that time.
  - If the extension also fails → Option C discussion (narrow or reframe the contribution).

**G2b: Detection (E2).** The FA bar and detection bar of §7. The FA part of G2b, on the held-out honest pairs of seeds 2–11, is the independent false-alarm assessment of the revision-3 calibration.
- **If G2b fails:** conclusion: "Oracle-free overhearing evidence does not separate droppers from honest nodes at the declared false-alarm rate." The roadmap stops and the Option C discussion follows. A trust comparison between arms is meaningless without this.

**G3: EAQTE activity (E3).** Requires at least one active, non-saturated grid point.
- **If G3 fails:** conclusion: "Across the unspecified parameter range, EAQTE's gate cannot be exercised in this network and mobility model." The SS distribution is reported as the explanation, and B ≡ A.
  - This is **not** "EAQTE fails".
  - The masked-attack question cannot be answered here → Option C discussion.

**G4: Evidence/EE causal relationship (E3).** Clean seeds; all nodes honest; no oracle needed. At every active point:
- the stratified odds ratio of SILENT for EE < 0.3 vs EE ≥ 0.3 must be > 1, with its CI excluding 1;
- for the continuous case, the logistic slope of SILENT on EE must be negative.
- **If G4 fails:** conclusion: "In this simulator, EE does not track how reliable the evidence is." (Plausible here, because decoding does not depend on distance.) Gating then removes evidence; it does not denoise it.
  - E4 may still test the blind spot, which is about evidence removal.
  - PACT's claim to keep false alarms low becomes untestable here. That must be reported, and the claim must not be made.

**G5: Masked-attack blind spot (E4).** Both of these must hold at some active point, for at least one of the two masked attackers:
- **(a)** P(w = 0 | malicious-drop opportunity) / P(w = 0 | honest opportunity) > 1, with the CI excluding 1. This uses ground truth for evaluation only.
- **(b)** Arm B's TDR against the masked attacker is significantly below Arm A's, and that drop is larger than for the matched plain attacker.
- **Reported alongside (b), as context only:** for every E4 arm (`AttackMode=1`, AdversarialMotion, matched plain) and each of Arms A and B:
  - the realised malicious drop count (ground truth);
  - the number of judged malicious pairs;
  - the number of flagged malicious pairs.

  These make the realised attack budget transparent. They are diagnostic, not part of the pass criterion. G5(b) stays defined on the judged malicious-pair detection metric (TDR); it is never redefined around raw drop counts.
- **If G5 fails:** conclusion: "The EAQTE gate creates no exploitable blind spot for the tested masked attackers in this configuration." That is a robustness result in EAQTE's favour.
  - E5 does not run. PACT is reported as **moot (not replaced)**, and the Option C discussion follows.

**G6: PACT effectiveness (E5, confirmatory seeds 41–50).** Requires both:
- **(a)** TDR_C − TDR_B against the masked attacker has a 95% lower bound > 0, at equal clean FA;
- **(b)** held-out honest FA for C is no worse than for A.
- **If (a) passes and (b) fails:** conclusion: "PACT recovers what the gate lost, but adds nothing over having no gate."
- **If (a) fails:** conclusion: "PACT in its current form does not close the blind spot." Any redesign would be a new pre-registered study on new seeds.
- No claim that PACT works may be made before G6 passes.

## 13. Open points and revision-3 decisions

**Open point (revision 3):**
- **P5: open — decide before E3.** How bins are formed for Arms B and C, whose weights give n_eff rather than n:
  - (a) reuse Arm A's edges L_b (some bins may then hold fewer than M pairs), or
  - (b) rebuild bins by the §7 step-3 algorithm on each arm's own n_eff.

  E1 uses Arm A only and gives no evidence for either choice. P5 is decided before E3, from the actual n_eff distribution after Arm B/C weighting.

**Revision-3 decisions (2026-10-04):**
- **R3-1 (V6 design):** n-conditioned empirical calibration (candidate C-1) — §7 step 3 deterministic bins with M = 200, per-bin nearest-rank τ_A,b; §7 step 4 power by thinning. Basis (E-32 data, clean seeds only): var(Z) 29.0 and rising with n; a pair's silence propensity is persistent (first-half vs second-half residual correlation 0.76); in-sample FA at the revision-2 τ_A rises from 0.000 (n 14–27) to 0.339 (n ≥ 250).
- **R3-2 (power target, option i):** if no bin reaches power ≥ 0.80, n_min is undefined and G1 fails; the 0.80 target and p_min are not changed. The ~0.41 model-based ceiling is a diagnostic only.
- **R3-3 (V3-a):** minimum separation > ε + 12.5 m = 37.5 m, replacing the underived 2ε = 50 m rule; separations below 50 m are reported.
- **R3-4 (status of validation):** V6 on seeds 12–21 is recalibration/development validation; the independent false-alarm assessment is G2b on seeds 2–11.
- **R3-5 (reuse):** the existing E1 simulation outputs and O1 opportunity files are reused; the revision-2 calibration and validation files are kept unchanged as the historical record.
- **R3-6 (diagnostic provenance):** the scripts that produced the design-basis diagnostics behind R3-1 and R3-3 are archived in `e1/diagnostics_rev3/` with their outputs. They are provenance only, not the revision-3 calibration implementation; the revision-2 diagnostics in `e1/diagnostics/` are unchanged.
- **Unchanged by revision 3:** the O1 information boundary (§5, §6), opportunity construction for Arms A/B/C, the strata and merge rule, n_ref, the Z statistic, and checks V1, V2, V4, V7, V8 (V5 is extended, not changed).

**Revision-2 points** — all four were resolved in revision 2 (2026-10-04). They are kept here as a record.

- **P1: resolved** (revision 2): §7 calibration steps 1–6.
- **P2: resolved** (revision 2): §11 attacker configuration. Q1: the `AttackMode=1` arm uses dropProbability 0.75. Q2: the AdversarialMotion arm uses AttackMode=0, dropProbability 0.75, adversarialMotion=true.
- **P3: resolved** (revision 2): §5 and §6 step 1. Own transmissions come from O's own `t` record only; check V8.
- **P4: resolved** (revision 2): the D-13 status in `../../RESEARCH_DECISIONS.md` and the Stage E item in `../../PROJECT_HANDOFF.md` §10 point here.

## 14. Revision log

| Date | Revision |
|---|---|
| 2026-10-04 | Frozen specification written. Includes consistency-check corrections C1 (read-only peer EE), C2 (PACT peer set = all table entries) and C3 (Stage D outcome rule; rank before the hearing filter; 8 s timing rule). Open points P1–P4 recorded |
| 2026-10-04 | Revision 2: P1 resolved (n_ref, nearest-rank τ_A, then n_min by Monte Carlo power at fixed τ_A; freezing before any attacker run is generated). P2 resolved: attackerFraction 0.2, AttackStart 0; `AttackMode=1` arm p = 0.75; AdversarialMotion arm AttackMode=0, p = 0.75, adversarialMotion=true (1.5 s reversal, fixed in code); matched plain control AttackMode=0, p = 0.75, adversarialMotion=false, replacing the realised-drop-budget matching rule. P3 resolved (own `t` record; check V8). P4 cross-links added. V6 made explicit. Final amendments: G5(b) is reported together with the realised malicious drop count, judged malicious-pair count and flagged malicious-pair count per E4 arm, as context only; the status block marks the specification frozen at revision 2 |
| 2026-10-04 | E1 run under revision 2 (E-32; historical record commit `58cc50c`): **G1 failed** on V3 (minimum separation 39.9 m < 50 m) and V6 (pooled out-of-seed FA 0.191, one-sided lower bound 0.115) |
| 2026-10-04 | Revision 3: decisions R3-1 to R3-6 (§13). §7 steps 3–6 and freezing replaced (deterministic n-bins, M = 200, per-bin τ_A,b, power by thinning, n_min with option (i), new JSON `e1_calibration_rev3.json`); bars and §8 thresholds made per-bin; V3 rule replaced (V3-a); V5 extended to the revision-3 calibration script; V6 rewritten for the binned procedure, with its bootstrap specification stated and its development-validation status; G2b named as the independent false-alarm assessment; per-bin calibration described as empirical at the nominal 0.05 level (not an exact guarantee); V6 bootstrap B = 10,000 and PCG64 seed 12345 fixed as reproducibility parameters; §11 E3 row made per-bin (binning: P5); open point P5 (Arm B/C binning) added, to be decided before E3; design-basis diagnostics archived in `e1/diagnostics_rev3/`. Superseded revision-2 text kept verbatim in §17 |

---

## 15. D1(ii): `[RXHDR]` receiver-side decoded-header logging (done, validated)

**Change.**
- aqua-sim-ng commit `41c67c3`: 8 inserted lines in `AquaSimTrustQVBF::Recv`, on the received-packet branch, immediately after the existing `packet->PeekHeader (vbh)`.
- Each received copy logs the following, at 17 significant digits:

```
[RXHDR] node=<receiver> tx=<forwardAddr> src=<senderAddr> pk=<pkNum> f=x:y:z d=x:y:z tgt=x:y:z t=<time>
```

- `d` is logged exactly as decoded, i.e. still wrapped as uint32/1000.
- The line reads only the already-decoded header and changes no simulation behaviour.
- **No further changes to this patch.**

**Why.** The trace prints header values to 6 significant digits, so Stage D rebuilt f and d offline from simulator-side ground truth (true positions, `[HOLD]` times, `[DECISION] up`). With `[RXHDR]` the observer input is the decoded bytes themselves.

**Code state.**

| File | MD5 |
|---|---|
| `src/aqua-sim-ng/model/aqua-sim-routing-trustq-vbf.cc` | `953629a5e75c1bc7ae5352ba0fb015cd` |
| `build/lib/libns3.41-aqua-sim-ng-default.so` | `871c50fc90cc613513ce25211cc8e450` |
| `build/scratch/ns3.41-uwsn-trustq-attack-default` | `54e444ed2ade8baf1c5fc3f54be5ad36` (unchanged) |

**Runs.** The three Stage D configurations (`c_tq_a`, `d_p100`, `d_p075`; arguments in `../STAGE_D_README.md` §3) were rerun with the patched library into `~/uwsn-runs/rxhdr_seed1/`, outside the repo (181 MB, not archived), and compared with `~/uwsn-runs/stageCD_seed1/`.

**Results** (`rxhdr_validation/validation_output.txt`, identical pattern in all three runs):

- **Behaviour unchanged.**
  - energy, mobility, trust, observed, meta, stdout: byte-identical;
  - stderr: identical after removing `[RXHDR]` lines;
  - trace: 0 differing records after masking `token=`, `ts=`, `range=`.
- **Trace masking is permanent (D-16).** VBHeader's constructor initialises only `m_messType`, so `m_token`, `m_ts` and `m_range` are serialized from uninitialised memory. This is a pre-existing Aqua-Sim-NG defect and is **deliberately not fixed**.
  - The patch moved the stack garbage in `token` (30 → 0 / 2799601 / 4083687). `ts` also differs in 25 records of each attacker run.
  - Nothing in VBF/TrustQVBF reads the token; `GetToken` has no caller in aqua-sim-ng.
  - **All behavioural trace comparisons mask token, ts and range.**
- **Coverage.** `[RXHDR]` lines = trace `r` records, one-to-one (26303 / 26180 / 26106).
  - The trace `r` event fires in `AquaSimPhyCmn::SendPktUp`, which the signal cache calls only for packets with status RECEPTION. The broadcast MAC passes every such copy to routing `Recv`.
- **Agreement with the printed trace.** 0 component mismatches beyond 6-digit print resolution. All values lie on the mm grid. The target is always (1500, 1500, 0). Every receiver of a transmission decoded identical f, d.
- **Agreement with the Stage D reconstruction.**
  - Non-ambiguous transmissions (2476 / 2375 / 2397): 0 f and 0 d mismatches.
  - The 34–40 transmissions Stage D flagged ambiguous: 7 f and 15 d mismatches, at most 0.3005 m (one MCM second of drift). This cannot change any MATCH/OTHER-UP outcome (ε = 25 m, nearest other transmitter ≥ 136 m).
- **Upstream recovery from the decoded values alone:** max error 0.601 m, median 0.300 m, 0 above 25 m. This reproduces Stage D, and is now independent of the ground-truth upstream used in the Stage D rebuild.

**Files in `rxhdr_validation/`.**

| File | Purpose |
|---|---|
| `cmp_masked.py` | record-wise trace comparison, reports which of token/ts/range differ, compares the rest |
| `rxhdr_check.py` | `[RXHDR]` vs printed trace, vs Stage D reconstruction, and upstream recovery |
| `amb_size.py` | size of the mismatches in Stage-D-ambiguous transmissions |
| `validation_output.txt` | output of the three scripts for the three runs |
| `checksums.txt`, `build_rxhdr.log` | code state and build log (only the known `-Wreorder` warnings) |

These are the original scripts (not rebuilds). They use absolute paths to `analysis/d_common.py` and to the run directories. Rerun with:

```
python3 -B cmp_masked.py   ~/uwsn-runs/stageCD_seed1/<run>/v1_1.tr ~/uwsn-runs/rxhdr_seed1/<run>/v1_1.tr
python3 -B rxhdr_check.py  ~/uwsn-runs/rxhdr_seed1/<run> ~/uwsn-runs/stageCD_seed1/<run>
python3 -B amb_size.py     ~/uwsn-runs/rxhdr_seed1/<run> ~/uwsn-runs/stageCD_seed1/<run>
```

## 16. EAQTE Eb/N0 landmark arithmetic (`eaqte_operating_point/`)

`ee_bound.py` mirrors `AquaSimTrustQVBF::TransmissionProbability` (EAQTE Eqs. 6–10) and evaluates it offline. Output: `ee_bound_output.txt`.

This is arithmetic only: no simulator run, no seed, no outcome data. It is kept solely to preserve the derivation of the fixed landmarks in §10, and is not an experiment. It gives:

- **The EE bound.** EE ≥ 0.5·(1 − tanh ¼)·p(1000 m) = 0.3537 > ξ = 0.3 at 40 dB, so the gate is inert for every in-range neighbour at the previous operating point.
- **The landmarks** at 1000 m:

  | Eb/N0 | Condition for a freeze to become possible |
  |---|---|
  | 34.5 dB | SS = 0, var = ¼ (worst case) |
  | 31.1 dB | SS = 0, var = 0 |
  | 24.5 dB | SS = 0.5 (no-velocity default) |

- **A structural fact.** With the published ψ = 0.5 and ξ = 0.3, a freeze requires both SS < 0.6 and CCQ < 0.6.
- **A correction.** The handoff's historical values at 100 m — p = 0.913 at 20 dB and 0.057 at 5 dB — do not reproduce with the current formula, which gives 0.943 and 0.161.

---

## 17. Superseded revision-2 text (verbatim)

Every passage of revision 2 (commit `c0d2cec`) that revision 3 replaced, copied verbatim from that commit,
in document order. Line numbers refer to the revision-2 file.

**Revision 2, Stage E — frozen specification (pre-implementation) (lines 4–6):**

````text
- **Frozen, revision 2** (2026-10-04; approved in session; decisions `../../RESEARCH_DECISIONS.md` D-13 to D-16; revision history in §14).
- **Nothing is implemented:** no O1/O2 code, and E1 has not been run.
- The only Stage E work done so far is the logging-only `[RXHDR]` change and its validation (§15, `../../EXPERIMENT_LOG.md` E-31).
````

**Revision 2, Stage E — frozen specification (pre-implementation) (lines 11–11):**

````text
- The open points P1–P4 are all resolved in revision 2 (§13).
````

**Revision 2, Stage E — frozen specification (pre-implementation) (lines 27–27):**

````text
13. Open points to decide before E1
````

**Revision 2, 7. O2: per-pair statistic and frozen baseline (lines 170–184):**

````text
3. **τ_A.** Compute Z for every honest calibration pair with n ≥ n_ref and sort ascending (N pairs).
   τ_A = Z₍⌈0.95·N⌉₎ (nearest rank). A pair is flagged when Z > τ_A.
4. **n_min,** with τ_A already fixed:
   - For n = n_ref, n_ref + 1, …, n_cap (n_cap = the largest n of any honest calibration pair), estimate
     power(n) by Monte Carlo with R = 10,000 synthetic pairs.
   - Each synthetic pair has n opportunities. Strata are drawn i.i.d. from the empirical stratum mix of all
     honest calibration opportunities; y ~ Bernoulli(q₁,s) with q₁,s = 1 − (1 − q_s)(1 − p_min), p_min = 0.75;
     Z is computed with the calibration q_s.
   - power(n) = the fraction with Z > τ_A. RNG: NumPy PCG64, seed 12345 (= BASE_SEED).
   - n_min = the smallest n with power(n) ≥ 0.80.
   - If no n ≤ n_cap qualifies, n_min is undefined and G1 fails (no adjustment).
5. **Reported, never tuned:** the full power curve, the calibration FA among honest pairs with n ≥ n_min
   at τ_A, and the over-dispersion of Z.
6. **Other arms.** τ_B and τ_C use step 3 with their own weights (n_eff in place of n, n_eff ≥ n_ref) on the
   same clean seeds. n_min is common to all arms (Arm A's, from step 4), applied to n_eff.
````

**Revision 2, 7. O2: per-pair statistic and frozen baseline (lines 188–191):**

````text
**Freezing.** Before any attacker run is generated, write one versioned JSON file containing:
q_s, the merge map, q̄, n_ref, τ_A, the power curve, n_min, the Monte Carlo seed and R,
the md5 of every calibration run's `stderr.log` and `v1_1.tr`, and the code commit hashes.
Record the file's md5 in `../../EXPERIMENT_LOG.md`.
````

**Revision 2, 7. O2: per-pair statistic and frozen baseline (lines 205–205):**

````text
  - The TDR at τ_A has a 95% lower bound **above** the FA upper bound.
````

**Revision 2, 8. Common evidence layer per arm (lines 212–214):**

````text
| A | 1 | τ_A |
| B | 0 if EE_{O,X}(t₀) < 0.3, otherwise 1 (the published freeze, applied per opportunity as a stand-in for the per-slot gate; a gated opportunity is excluded) | τ_B(Eb/N0) |
| C | min(1, EE_X / median EE of O's peers): the existing PACT formula (S-07), unchanged | τ_C(Eb/N0) |
````

**Revision 2, 8. Common evidence layer per arm (lines 229–229):**

````text
**Thresholds.** τ_B and τ_C use the τ_A rule on the same clean seeds 12–21, per grid point. Arms are therefore compared at equal false-alarm rate on clean runs.
````

**Revision 2, 11. Experiment sequence (lines 296–296):**

````text
| **E1** | Clean simulation runs; offline O1/O2; checks V1–V7 (G1); calibrate and freeze q_s, merge map, τ_A, n_min | 12–21 |
````

**Revision 2, 12. Decision gates and predefined failure conclusions (lines 333–333):**

````text
| V3 | Upstream recovery error ≤ 12.5 m (the Stage D acceptance rule); minimum separation ≥ 50 m |
````

**Revision 2, 12. Decision gates and predefined failure conclusions (lines 335–336):**

````text
| V5 | Static audit: no ground-truth field reachable from observer code |
| V6 | Leave-one-seed-out: for each seed in 12–21, rerun §7 steps 1–4 on the other nine seeds and measure FA on the left-out seed's judged honest pairs. Pooled FA is not significantly above 0.05 |
````

**Revision 2, 12. Decision gates and predefined failure conclusions (lines 348–348):**

````text
**G2b: Detection (E2).** The FA bar and detection bar of §7.
````

**Revision 2, 13. Open points to decide before E1 (lines 382–382):**

````text
## 13. Open points to decide before E1
````

**Revision 2, 13. Open points to decide before E1 (lines 384–384):**

````text
All four points were resolved in revision 2 (2026-10-04). They are kept here as a record.
````

**Revision 2, 11. Experiment sequence (line 298; replaced in the final revision-3 edits):**

````text
| **E3** | Offline replay of the EAQTE gate on the E1 traces across the grid: freeze fraction, joint SS/CCQ distribution, regimes, τ_B per grid point; evidence/EE causal test (G4) | 12–21 |
````
