# Stage E — Option C transition after E2: the C-β reframing

**Status:** proposed 2026-10-05; frozen only when committed together with `../../RESEARCH_DECISIONS.md` D-22. **Not implemented:** no OC-1 or OC-2 code, run or output exists.

**C-β is a new reframing adopted after the E2 stop. It is not a continuation of E3 and does not resume the original E2 → E3 → E4 → E5 roadmap**, which stays stopped (E2-14).

Contents:
0. Classification tags
1. Provenance
2. Basis: the final E2 result and its frozen consequences
3. What C-β is
4. Stage labels
5. OC-1 — Oracle-free evidence and observability characterization
6. OC-2 — Standalone EAQTE operating characterization
7. Statistical and computational specification
8. Data classes and the need for new simulation
9. Claims
10. Safeguards before any execution
11. Missing code and decisions
12. Commit plan
13. Revision log

---

## 0. Classification tags

- **[F]** explicitly frozen in `README.md` (revision 4), C-d (`CD_EVALUATION_FRAMEWORK.md`) or `E2_SPEC.md`; the section is cited.
- **[L]** logically implied: the frozen text admits no other reading.
- **[P]** proposed interpretation; requires approval before any OC code is written. Each [P] states why it is needed and is the smallest defensible choice.

## 1. Provenance

| Commit | Content |
|---|---|
| `8a0ff2f` | Revision-4 specification (`README.md`), unchanged |
| `362cda7` | C-d evaluation framework freeze (D-19), unchanged, including the open §4.1 multiplicity inconsistency |
| `a87ffbc` | E2 specification freeze (`E2_SPEC.md`, D-20) |
| `36655b7` | E2 evaluator and tests, committed before any E2 data |
| `ca1edc7` | Final E2 record (E-35; `e2_results.json`, `e2_report.txt`) |
| `3eba654` | E2 outcome in project documentation (D-21; `PROJECT_HANDOFF.md`) |

## 2. Basis: the final E2 result and its frozen consequences

- **E2 is final** (E-35, D-21): G2 PASS (306 judged active-malicious pairs; 36 distinct (seed, X)); G2b-FA PASS (73/1,383 = 0.0528; 5th percentile 0.0304); AUC PASS (0.9055; 2.5th percentile 0.8464); TDR-vs-FA FAIL (TDR 2.5th percentile 0.0846 vs FA 97.5th percentile 0.0873; by 0.0027); **G2b FAIL**, interpretable because G2 passed. Nothing here reinterprets, re-tests or statistically rescues it.
- **Frozen consequences:**
  - `README.md` §12 G2b: "The roadmap stops and the Option C discussion follows. A trust comparison between arms is meaningless without this." [F]
  - C-d §10.4: E4 only if G1′, G2, G2b, G3 and G4 pass; E5 only where G5 qualified. G5 and G6 cannot run under C-d. [F]
  - `E2_SPEC.md` E2-14: E3, E4 and E5 do not run. [F]
- **Option C** is defined only as a discussion to "narrow or reframe the contribution" (`README.md` §12). [F] The first Option C discussion (after D4-5) produced C-d; this is the second.

## 3. What C-β is

**C-β = C-α (narrowing) + a standalone EAQTE operating characterization on already-open clean data.**

- It reframes the contribution around what the evidence supports. It does not test whether trust detects attackers, whether EAQTE creates a blind spot, or whether PACT recovers detection.
- **Not part of C-β:**
  - C-γ (any new comparative arm study or G5/G6-type test after the G2b failure), unless explicitly reopened;
  - any attacker-seed data: seeds 22–31 and 41–50 stay sealed; seeds 32–40 stay unused; seed 1 stays development only;
  - any new simulation (§8);
  - Arm C (PACT) [P, §7];
  - any change to C-d. The C-d §4.1 multiplicity inconsistency stays open for any future G5/G6 work; C-β does not use C-d's family bootstrap and does not change it.

## 4. Stage labels

| Label | Name | Relation to the stopped roadmap |
|---|---|---|
| **OC-1** | Oracle-free evidence and observability characterization | None; compiles committed E1/E2 evidence |
| **OC-2** | Standalone EAQTE operating characterization | None. It is **not** E3: it uses some characterization content that E3 would have produced, without any gate role |

E3, E4 and E5 keep their frozen meaning as stopped stages and are not reused or relabelled. [P]

## 5. OC-1 — Oracle-free evidence and observability characterization

### 5.1 Evidence retained (all committed; nothing recomputed)

| Evidence | Record |
|---|---|
| Information boundary, O1/O2 design, strata | `README.md` §5–§7; D-13 to D-16 |
| `[RXHDR]` logging and its validation; VBHeader `token`/`ts`/`range` uninitialised (trace defect) | E-31; D-15, D-16 |
| E1 revision 2: G1 fail (V3 separation, V6 FA 0.191) | E-32 (`58cc50c`) |
| E1 revision 3: G1 fail (V6-B; V6-A pass) | E-33 (`b016a9a`) |
| E1 revision 4: V6-A pass (0.0535; lower bound 0.0297), V6-B fail (n_min undefined everywhere), G1 fail, D4-5 stop | E-34 (`103e671`) |
| C-d adoption; G1′ holds | D-19 (`362cda7`) |
| E2 held-out Arm-A result, reproducibility pass, Phase-1 checker incident | E-35, D-21 (`ca1edc7`, `3eba654`) |
| Observability ceiling, p = 1.0 and p = 0.75 | E-35 |

### 5.2 Methodological findings it supports

1. Oracle-free per-pair evidence can be built from receiver-decoded headers only, with checks V1, V2, V4, V5, V7, V8 and V3-a passing (E-32 to E-34; the revision-2 V3 rule failed and was replaced by V3-a in revision 3).
2. Honest silence propensity is persistent per (O, X) pair and over-dispersed beyond the K1–K3 strata (E-32, E-33). This pair-persistent heterogeneity left no verified 0.80-power region under the declared calibration and validation setup: n_min is undefined in the full calibration and every fold (E-34). Recorded as a limitation of per-pair overhearing evidence (D4-5).
3. The per-bin false-alarm calibration transfers: within the declared 5% bar both in development validation (V6-A, E-34) and on independent held-out seeds (G2b-FA, E-35).
4. On held-out seeds, the evidence ranks droppers above honest nodes (AUC 0.9055; 2.5th percentile 0.8464) but **fails the declared detection bar** at the per-bin thresholds (E-35). Both halves are always reported together.
5. Observability is a first-order limit: at p = 1.0 only 14.2% of drops are observable and 34 of 42 active malicious (seed, X) nodes are never observable; at p = 0.75, 64.0% (E-35).
6. Simulations are deterministic apart from three uninitialised VBHeader fields that nothing reads (E-31, E-35 Phase 3).

### 5.3 Not supported by OC-1

Any claim of secure-routing improvement; any detection guarantee, power or n_min; that G2b "nearly passed" or any alternative reading of E2; generalization beyond the simulated topologies, mobility, range propagation and the declared attacker.

### 5.4 Form

A written synthesis citing the records above by commit and md5; it recomputes nothing. [P]

## 6. OC-2 — Standalone EAQTE operating characterization

**Scope.** OC-2 is an **offline operating characterization of the EAQTE environment gate by replaying the fixed 40-dB E1 traces across the specified Eb/N0 scoring grid.** The traces were generated once, under the existing simulation condition (C++ EAQTE compiled at Eb/N0 40 dB; S1; range propagation); only the offline EE score changes across the grid. **OC-2 does not characterize newly simulated network behavior at those Eb/N0 values.**

**Descriptive only.** OC-2 reports effect estimates with uncertainty intervals. It has no pass/fail gate: none of its quantities is a security-performance gate, a revived G3 or G4 gate, or evidence about G5 or G6.

### 6.1 Data

- **Already existing, clean:** `~/uwsn-runs/stageE/E1/run_12` … `run_21` (attackerFraction 0, PriorityScale 0, ObservedTrustWeight 0, `EAQTE_XI` and `RX_RANGE_M` unset). Verified 2026-10-05: all 30 inputs recorded in `e1/e1_calibration_rev4.json` (`stderr.log`, `v1_N.tr`, `e1_opportunities.csv`) are present and md5-identical; every run also holds `v1_N_mobility.csv` with columns x, y, z, vx, vy.
- **Observer-side inputs only** [F `README.md` §5]: `[RXHDR]` lines (X's decoded positions f and heard times), O's own mobility rows, O's own trace `t` records, and the existing O1 opportunity files.
- C++ `[EAQTE-CCQ]`, `[EAQTE-SS]`, `[EE]` and `[SSCCQ]` lines (compiled at Eb/N0 40 dB) serve **only** for parity validation of the offline code (§10), never as inputs. [P]
- Seeds 12–21 also informed revisions 3 and 4; OC-2 characterizes these topologies and is not an independent confirmation. [F `README.md` §7; C-d §11]

### 6.2 Computed quantities

For each value g of the offline Eb/N0 scoring grid {15, 20, 24.5, 27.5, 31.1, 34.5, 37.5, 40, 45, 50} dB [F §10], applied to the fixed 40-dB traces, at k = 1.5 (primary) and separately at k = 1.0 and k = 2.0 (secondary) [F §10]:
1. EE per opportunity and the freeze indicator (§7 E-1 to E-9);
2. freeze fraction (S-1);
3. joint SS/CCQ distribution (S-12);
4. regime: inert, saturated or active (S-2 to S-4);
5. activity finding (S-4);
6. EE–evidence relationship at every active point (S-5 to S-9, S-11).

### 6.3 G3/G4 material: retained or discarded

| Material | Original role | In OC-2 |
|---|---|---|
| Freeze fraction; joint SS/CCQ distribution; SS distribution | E3 characterization [F §11] | Retained, descriptive |
| Regimes inert / saturated / active | E3 [F §10] | Retained, descriptive |
| G3: "at least one active, non-saturated grid point" | Gate to E4 | Retained **only as a descriptive finding**, not a gate. The frozen E3 sentence "Across the unspecified parameter range, EAQTE's gate cannot be exercised in this network and mobility model" [F §12] is cited, not adopted, because it would describe network behavior across Eb/N0. OC-2 negative wording: "In offline replay of the fixed 40-dB E1 traces, no value of the Eb/N0 scoring grid is active"; never "EAQTE fails" [F §12] |
| G3 routing: "masked-attack question cannot be answered → Option C" | Roadmap | Discarded (already in Option C) |
| G4: stratified odds ratio and logistic slope at every active point | Gate to E4; basis for PACT's false-alarm claim | Retained **only as descriptive effect estimates with intervals** about the replayed traces; no pass/fail and **not a revived G4 gate**. Negative wording, adapted from the frozen G4 sentence [F §12]: "In the replayed E1 traces of this simulator, EE is not associated with how reliable the evidence is" (plausible because decoding does not depend on distance) |
| G4 consequences: "E4 may still test the blind spot"; "PACT's claim … untestable" | E4/E5 routing | Discarded (E4/E5 stopped; no PACT claim is made) |
| τ_B,b(g) and P5 bins | Arm-B detection thresholds for E4 | Discarded; the regime rule counts judged pairs and needs no bins [L] |
| Holm across grid points for Arms B/C | E4/E5 inference | Not applicable (S-9) |
| Arm C weights | E5 | Not computed [P] |

## 7. Statistical and computational specification

| ID | Quantity / choice | Tag | Source, or why the [P] is needed |
|---|---|---|---|
| E-1 | p(d) by the coded Eqs. 6–10, exactly as `AquaSimTrustQVBF::TransmissionProbability` (mirrored by `eaqte_operating_point/ee_bound.py`); f = 25 kHz, m = 640 | [F] | `README.md` §1, §8, §10 |
| E-2 | d = \|pos_O(t₀) − x\|, x = X's last-known decoded position | [F] | §8, §6 |
| E-3 | pos_O(t₀) = O's own mobility row at ⌊t₀⌋, as in O1 (`observer.py`) | [L] | the O1 convention for the same quantity |
| E-4 | p-history: one sample per (O, X) per opportunity event, time order, window 10; every O1 opportunity event counts (MATCH, SILENT, OTHER-UP); recomputed per (g, k) | [F] one sample per event, window 10 (§8); [L] outcome-blind and per-(g, k) | EE is computed at t₀ before any outcome exists; p depends on (g, k) |
| E-5 | Variance of p by coded Eqs. 14–17; CCQ = p(1 − tanh var); CCQ = p with < 2 samples | [F] | §1; §12 V7 |
| E-6 | SS = ½(1 + cos θ) on 2D velocities; X's velocity from its last two decoded positions strictly before t₀; SS = 0.5 when dt < 0.05 s | [F] | §1, §5, §8 |
| E-6a | SS = 0.5 when X has fewer than two decoded positions | [L] | coded "no reliable velocity estimate" default |
| E-7 | O's own velocity from its mobility row at ⌊t₀⌋ (vx, vy) | [P] | the C++ uses instantaneous velocity, which offline data hold only at 1 s resolution; the same row as E-3 is the minimal consistent choice |
| E-8 | Zero-length velocity vector handled exactly as in `ComputeStabilityScore` (read before coding) | [L] | "coded equations" |
| E-9 | EE = 0.5 CCQ + 0.5 SS; freeze iff EE < 0.3 | [F] | §1, §8 |
| S-1 | Freeze fraction = frozen / (MATCH + SILENT) opportunities; the fraction over all O1 opportunities shown alongside | [P] | "freeze fraction" has no defined denominator; MATCH + SILENT is the O2 population, the one the inert rule counts (S-2) |
| S-2 | Inert: zero freezes across all calibration (MATCH + SILENT) opportunities | [F] rule; [L] population | §10; §7 step 2 defines calibration opportunities as MATCH + SILENT |
| S-3 | Saturated: Arm B judges fewer than half the honest pairs Arm A judges; judged = n ≥ 14 (A), n_eff ≥ 14 (B); Arm-B n_eff = count of unfrozen MATCH + SILENT opportunities | [F] | §10; C-d §2, §3 (J1) |
| S-4 | Active = neither inert nor saturated; activity finding = at least one active point at k = 1.5 | [F] definition; [P] primary k | §10, §12; restricting the finding to the primary k avoids choosing among k after the fact |
| S-5 | EE–evidence population: clean MATCH + SILENT opportunities at an active point; outcome SILENT; exposure EE < 0.3 vs ≥ 0.3 | [F] | §12 G4 |
| S-6 | Stratified odds ratio: strata = the 9 frozen merged O2 strata (`e1_calibration_rev4.json`); Mantel–Haenszel common odds ratio | [P] | G4 says "stratified" without strata or estimator; the frozen evidence strata are the only strata already defined, and MH is the standard estimator for stratified 2×2 tables |
| S-6a | **2×2 orientation, fixed:** exposure-positive = EE < 0.3, exposure-negative = EE ≥ 0.3; outcome-positive = SILENT, outcome-negative = MATCH. Per stratum i: a_i = #(EE < 0.3, SILENT), b_i = #(EE < 0.3, MATCH), c_i = #(EE ≥ 0.3, SILENT), d_i = #(EE ≥ 0.3, MATCH), n_i = a_i + b_i + c_i + d_i. OR_MH = Σ_i (a_i d_i / n_i) / Σ_i (b_i c_i / n_i) (multiplicity-weighted counts in bootstrap replicates). **OR > 1 means low EE (EE < 0.3) is associated with greater odds of SILENT** | [F] orientation; [L] cell formula | §12 G4 "odds ratio of SILENT for EE < 0.3 vs EE ≥ 0.3" fixes the orientation; the cell formula follows from it and S-6; writing it out prevents an implementation from reversing the direction |
| S-7 | Interval for S-6 and S-8: cluster bootstrap, seeds then X nodes within each seed occurrence, multiplicity = sum over occurrences (the E2-8 rule, not C-d §4.1); node universe = X with ≥ 1 MATCH/SILENT opportunity in the seed; B = 10,000; PCG64(12345); two-sided 95% percentile (2.5th/97.5th, linear); a non-identifiable replicate is handled by S-13b (never discarded, redrawn or given a substitute value) | [P] | G4 requires a CI but specifies no method; this reuses the project's cluster hierarchy (§7 "CIs: cluster bootstrap, resampling seeds, then nodes") with the already-frozen E2 implementation, adding nothing new |
| S-7a | "CI excluding 1" = lower endpoint > 1 | [L] | used only in the S-9 descriptive statement |
| S-8 | Logistic regression of SILENT on EE (continuous) with merged-stratum fixed effects, maximum likelihood (IRLS, NumPy); "negative" = upper endpoint of the S-7 interval < 0 | [P] | G4 names a logistic slope but no model or test; stratum adjustment matches S-6 |
| S-9 | Descriptive characterization rule only: the statement "EE is associated with SILENT at every active point" is made only if S-6/S-7a and S-8 hold at every active point; otherwise the per-point estimates are reported without it. No pass/fail, no gate, no downstream consequence; no multiplicity adjustment; every active point reported | [F] "at every active point" (§12); [L] no adjustment | an intersection over points cannot inflate the error of the joint statement |
| S-10 | k = 1.0 and 2.0: same computations, reported separately, outside the primary finding | [F] one at a time (§10); [P] role | §10 makes them secondary but does not say how they enter findings |
| S-11 | No active point → EE–evidence relationship "not evaluable"; only the activity finding is reported | [L] | G4 is defined at active points only |
| S-12 | Joint SS/CCQ distribution reported as 2D histograms (deciles of each) per (g, k), with SS-only histogram | [P] | §11 names the distribution but not its summary; fixed bins avoid choosing a display after seeing data |
| S-13 | **Observed-data failure is a hard stop.** If the observed data at a point produce an undefined or zero-denominator Mantel–Haenszel odds ratio (Σ_i b_i c_i / n_i = 0, S-6a notation), complete or quasi-complete separation in the logistic model, a singular design matrix, IRLS/MLE non-convergence, or any non-finite odds ratio, coefficient or slope: stop and report. **No fallback** in this or any other case (S-13b): no continuity correction, regularization, alternative estimator, altered model specification or tuning without separate approval | [P] | the frozen documents give no failure handling for these statistics; stopping is the only choice that adds no new estimator |
| S-13b | **Bootstrap-replicate failure.** If the observed data are identifiable but any bootstrap replicate meets an S-13 failure criterion, no value is substituted and no replicate is discarded or redrawn: the corresponding bootstrap interval is reported as **not evaluable under the frozen bootstrap specification**, and the OC-2 analysis stops and reports rather than producing an interval. Such a replicate is a property of the resampling, **not a substantive finding about the data**. Non-finite interval endpoints are treated the same way | [P] | separates a defect of the data (S-13) from a degenerate resample; the no-fallback rule applies to both |
| S-13a | Detection criteria (S-13 and S-13b), fixed in advance: IRLS from β = 0, at most 100 iterations, converged when max \|Δβ\| < 1e-10; separation if any fitted probability is within 1e-12 of 0 or 1 at termination, or any stratum has only SILENT or only MATCH; singular if the design-matrix condition number exceeds 1e12 or EE is constant | [P] | S-13 needs operational tests that cannot be tuned after seeing data |
| R-1 | Outputs `analysis/stageE/oc2/oc2_results.json` and `oc2_report.txt`; refuse to overwrite; inputs recorded by md5 | [P] | mirrors E2 provenance |
| R-2 | Second run to a separate location identical apart from the timestamp; otherwise hard stop | [P] | mirrors E2-12 / Phase 4 |
| R-3 | No selection after the fact; no regime or Eb/N0 value chosen after results | [F] | §10 |

## 8. Data classes and the need for new simulation

| Class | OC-1 | OC-2 |
|---|---|---|
| Already-existing raw simulation data | E1 and E2 raw runs, outside the repository (used only through committed records) | E1 clean runs 12–21 |
| Offline replay / analysis | None | EE replay and the S-quantities |
| New simulation | **None** | **None** |

**No new simulation is required.** Under S1, Eb/N0 changes only the offline EE computation and every grid point replays the same traces [F `README.md` §10]; every EE input is observer-side data already in the E1 runs (§6.1). The replay therefore characterizes the offline score on fixed traces, not newly simulated network behavior at those Eb/N0 values. Any genuinely new simulation (online replay, the MLAR sweep, other seeds) lies outside C-β and needs a separate decision.

## 9. Claims

**C-β does not claim:**
- validated secure-routing (or forwarding) improvement by EAQTE, PACT or observer trust;
- successful G5 or G6 validation, or that an EAQTE blind spot exists or does not exist;
- successful end-to-end PACT improvement;
- revival of the original E3/E4/E5 roadmap, or a revived G3 or G4 gate;
- network behavior at Eb/N0 values other than the simulated condition (OC-2 rescores fixed traces offline);
- any calibrated power, detection guarantee or n_min (C-d §8);
- that "EAQTE fails" (§12 G3 wording);
- that G2b nearly passed, or any alternative reading of E2;
- generalization beyond the simulated network, mobility, range propagation and declared attacker. EE findings under range propagation, where decoding does not depend on distance, say nothing about real acoustic channels.

**Positive contribution supported by the evidence:**
- An oracle-free, opportunity-conditioned overhearing evidence layer for beaconless HH-VBF, with a documented validity record and a reproducible held-out evaluation (OC-1).
- Quantified limits of that evidence: pair-persistent heterogeneity that left no verified 0.80-power region under the declared calibration and validation setup; false-alarm calibration that transfers to held-out seeds; ranking ability (AUC 0.906) that nevertheless fails the declared detection bar; and an observability ceiling dominated by unobservable droppers (OC-1).
- An offline operating characterization of the EAQTE environment gate by replaying the fixed 40-dB E1 traces across the specified Eb/N0 scoring grid: how often the gate would freeze evidence, its regime per grid value, and whether the environment score is associated with silence in these traces (OC-2). This does not characterize newly simulated network behavior at those Eb/N0 values.

## 10. Safeguards before any execution

1. Every [P] in §4, §5.4 and §7 approved or replaced, recorded with D-22.
2. OC-2 code and dedicated tests written in a new `analysis/stageE/oc2/` and committed by explicit path **before** they read seeds 12–21. Existing e1/e2 code, C-d and `E2_SPEC.md` imported or cited, never modified.
3. Tests on synthetic data and development seed 1 only: p(d) against `ee_bound.py`; E-1 to E-9; regimes; MH odds ratio against an independent calculation, including a known stratified table with OR > 1 computed independently in exact rational arithmetic with the S-6a orientation (and its reversal giving 1/OR); the E2-8 bootstrap worked example; logistic fit against a brute-force likelihood maximum; synthetic cases for every S-13 failure (zero-denominator odds ratio, complete and quasi-complete separation, constant EE, iteration cap reached, non-finite values), each of which must stop; a synthetic dataset whose observed estimates are identifiable while a constructed bootstrap replicate is degenerate (e.g. a resample containing no EE < 0.3 opportunity), which must return the observed estimate, report the interval as not evaluable (S-13b) and stop without an interval; determinism; refusal to overwrite.
4. Parity validation on the E1 runs (procedural, not a result): offline p(d) and first-computation CCQ against `[EAQTE-CCQ]` at 40 dB (as V7); offline SS against `[EAQTE-SS]` where inputs coincide. Any unexplained mismatch is a hard stop.
5. R-1 to R-3; any input md5 mismatch stops the run; no attacker-seed data read.

## 11. Missing code and decisions

- **Code that does not exist:** the offline EAQTE replay (p-history per opportunity event, variance and CCQ, SS from decoded positions and own velocity, EE, freeze) and the OC-2 summaries (freeze fraction, regimes, MH odds ratio, logistic fit, bootstrap, report). Existing reusable code: the O1 opportunity files and `observer.py` conventions; `ee_bound.py` p(d); the E2-8 bootstrap rule in `e2_evaluate.py`. Not to be implemented before approval.
- **Decisions:** E-7, S-1, S-4 (primary k), S-6, S-7, S-8, S-10 (role), S-12, S-13, S-13a, S-13b, R-1, R-2, no Arm C, the labels, the OC-1 form, and the parity-only use of C++ log lines.
- **Constraint:** SciPy is not installed; NumPy only.

## 12. Commit plan

1. This document and D-22 (explicit paths).
2. `PROJECT_HANDOFF.md` sync.
3. OC-2 code and tests, before any OC-2 run.
4. OC-2 results (two identical runs) with an `EXPERIMENT_LOG.md` entry.
5. OC-1 synthesis.

Nothing is pushed without a separate instruction (submodule first).

## 13. Revision log

| Date | Revision |
|---|---|
| 2026-10-05 | Proposed after the E2 G2b failure (D-21): C-β reframing; OC-1 and OC-2 labels; G3/G4 material retained only as descriptive findings; full [F]/[L]/[P] specification; no new simulation, no attacker seeds, C-d unchanged. Not implemented |
| 2026-10-05 | Revised before commit: OC-2 scoped as offline rescoring of the fixed 40-dB E1 traces across the Eb/N0 scoring grid, not newly simulated network behavior; power wording limited to "no verified 0.80-power region under the declared calibration and validation setup"; statistical hard stop S-13/S-13a (replacing the S-7 replicate substitute value); OC-2 stated as descriptive only, S-9 a descriptive rule. Not implemented |
| 2026-10-05 | Final technical corrections before commit: S-13 split into observed-data failure (hard stop) and bootstrap-replicate failure S-13b (interval not evaluable; stop; no substitute value; not a substantive finding), with a synthetic test of the distinction; 2×2 orientation and MH cell notation fixed (S-6a: OR > 1 means low EE is associated with greater odds of SILENT), with a known-table test. Not implemented |
