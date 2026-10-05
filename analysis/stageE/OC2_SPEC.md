# Stage E — OC-2 specification: standalone EAQTE operating characterization

**Status:** approved 2026-10-05; frozen when committed together with `../../RESEARCH_DECISIONS.md` D-23. **Not implemented:** no OC-2 code, run or output exists, and no seed 12–21 data has been read for OC-2.

This document resolves every proposed interpretation [P] left open in `OPTION_C_TRANSITION.md` (C-β, D-22, commit `27f98ad`) §11. It does not modify that document, `README.md` (revision 4, `8a0ff2f`), C-d (`CD_EVALUATION_FRAMEWORK.md`, `362cda7`) or `E2_SPEC.md` (`a87ffbc`). Where a frozen source and this document differ, the frozen source wins and OC-2 stops for review. The two approved departures from the transition document's proposals (E-7 and S-4 reclassified as [L]; S-12 bins changed) are listed in §9.

Contents:
1. Scope, limitation and claim restrictions
2. Data and inputs
3. EE computation per opportunity
4. Characterization quantities
5. EE–evidence relationship (descriptive)
6. Failure handling
7. Parity validation
8. Procedure, outputs and reproducibility
9. Resolution audit
10. Tests required before any OC-2 run
11. Execution sequence
12. Revision log

---

## 1. Scope, limitation and claim restrictions

- **OC-2 is an offline operating characterization of the EAQTE environment gate by replaying the fixed 40-dB E1 traces (clean seeds 12–21) across the specified Eb/N0 scoring grid.** The traces were generated once under the existing simulation condition (C++ EAQTE compiled at Eb/N0 40 dB; S1; range propagation). Only the offline EE score changes across the grid. **OC-2 does not characterize newly simulated network behavior at those Eb/N0 values.**
- **Descriptive only.** OC-2 reports effect estimates with uncertainty intervals. It has no pass/fail gate and is not a revived G3 or G4 gate.
- **OC-2 does not claim:** any secure-routing (or forwarding) improvement; G5 or G6 validation; PACT validation or end-to-end PACT improvement; revival of the E3/E4/E5 roadmap; network behavior at Eb/N0 values other than the simulated condition; that "EAQTE fails".
- **No new simulation, no attacker-seed data.** Seeds 22–31 and 41–50 stay sealed; seeds 32–40 stay unused; seed 1 is used only for development tests.
- **No Arm C (PACT).** C-d, including its open §4.1 multiplicity wording, is neither used nor modified.

## 2. Data and inputs

- **Runs:** `~/uwsn-runs/stageE/E1/run_12` … `run_21`, read-only. Before any computation, `stderr.log`, `v1_N.tr` and `e1_opportunities.csv` of every run must match the md5s recorded in `e1/e1_calibration_rev4.json` (`0ca88a0e…`); any mismatch is a hard stop.
- **Observer-side inputs only** [F `README.md` §5]: `[RXHDR]` lines decoded by O (X's decoded positions f and heard times), O's own mobility rows (`v1_N_mobility.csv`: x, y, z, vx, vy), O's own trace `t` records, and the existing O1 opportunity files (event order and X's last-known position `xpos`).
- **Strata:** the 9 frozen merged O2 strata of `e1_calibration_rev4.json`, via its merge map.
- **C++ EAQTE log lines** (`[EAQTE-CCQ]`, `[EAQTE-SS]`, `[EE]`, `[SSCCQ]`) are **never OC-2 inputs**; they are used only by the parity harness (§7).

## 3. EE computation per opportunity

For every O1 opportunity event (MATCH, SILENT and OTHER-UP), at every (g, k) with g ∈ {15, 20, 24.5, 27.5, 31.1, 34.5, 37.5, 40, 45, 50} dB and k ∈ {1.5 (primary), 1.0, 2.0 (secondary)}:

| ID | Rule | Tag |
|---|---|---|
| E-1 | p(d) by the coded Eqs. 6–10 exactly as `AquaSimTrustQVBF::TransmissionProbability` (Thorp absorption per km, spreading d_km^k, SNR = (Eb/N0)/A, BPSK-Rayleigh Pe, p = (1 − Pe)^m, clamped to [0, 1]); f = 25 kHz, m = 640; Eb/N0 = g, k as above | [F] `README.md` §1, §8, §10; [L] coded |
| E-2 | d = 3D Euclidean distance between pos_O(t₀) and x = X's last-known decoded position (`xpos`) | [F] §8, §6; [L] 3D as coded |
| E-3 | pos_O(t₀) = O's own mobility row at ⌊t₀⌋, the O1 convention (including its whole-second tie rule) | [L] |
| E-4 | p-history: one sample per (O, X) per O1 opportunity event, in O1 event order (row order of `e1_opportunities.csv`); the current sample is appended before the variance is computed; window 10; recomputed independently for each (g, k) | [F] §8; [L] outcome-blind, coded order |
| E-5 | CCQ = p(1 − tanh var), var = population variance of the history; CCQ = p with fewer than 2 samples; clamped to [0, 1] | [F] §1, §12 V7; [L] coded |
| E-6 | SS = ½(1 + cos θ) on 2D (x, y) velocities; X's velocity from its last two decoded positions with heard times strictly before t₀; cos θ clamped to [−1, 1] | [F] §1, §5, §8; [L] clamp coded |
| E-6a | SS = 0.5 when X has fewer than two such positions or their dt < 0.05 s | [F] §8 (dt); [L] coded default |
| E-7 | O's own velocity = (vx, vy) of the same mobility row as E-3. Source-verified exact reconstruction of the C++ `GetVelocity()`: MCM state changes only in `Update()` at whole seconds, and the log samples at k + 0.5 s with 17 significant digits | **[L]** (source-verified; listed [P] in the transition document) |
| E-8 | SS = 0.5 when either velocity norm < 1e-6 | [L] coded (`ComputeStabilityScore`) |
| E-9 | EE = 0.5 CCQ + 0.5 SS; **freeze iff EE < 0.3** | [F] §1, §8 |

## 4. Characterization quantities

Per (g, k), reported for every grid value; nothing is selected afterwards [F §10].

| ID | Rule | Tag |
|---|---|---|
| S-1 | **Primary freeze fraction** = frozen / (MATCH + SILENT) opportunities. **Descriptive** freeze fraction over all O1 opportunities (MATCH + SILENT + OTHER-UP), labelled as such | [P] **resolved** |
| S-2 | Inert: zero freezes across all MATCH + SILENT opportunities | [F] §10; [L] population |
| S-3 | Saturated: honest pairs judged in Arm B < ½ × honest pairs judged in Arm A; Arm A judged iff n ≥ 14; Arm B judged iff n_eff ≥ 14, n_eff = number of unfrozen MATCH + SILENT opportunities of the pair | [F] §10; C-d §2, §3 |
| S-4 | Active = neither inert nor saturated. **Activity finding** = at least one active grid value **at k = 1.5**. Its negative wording: "In offline replay of the fixed 40-dB E1 traces, no value of the Eb/N0 scoring grid is active" | [F] definition; **[L]** primary k (`README.md` §1 k = 1.5; §10 k ∈ {1.0, 2.0} secondary) |
| S-12 | Distributions per (g, k), with **fixed, data-independent bins**: SS and CCQ histograms and their joint 2D histogram with bin width 0.1 on [0, 1] (10 × 10 bins; the value 1.0 falls in the last bin); EE histogram with bin width 0.05 on [0, 1] (20 bins; the value 1.0 falls in the last bin); and the count of opportunities with the default SS = 0.5 under E-6a or E-8 | [P] **resolved** |

## 5. EE–evidence relationship (descriptive)

Computed at every active (g, k); the primary statement uses k = 1.5 only.

| ID | Rule | Tag |
|---|---|---|
| S-5 | Population: clean MATCH + SILENT opportunities at the active point; outcome SILENT; exposure EE < 0.3 | [F] §12 G4 |
| S-6 | Mantel–Haenszel common odds ratio over the 9 frozen merged strata; strata with n_i = 0 contribute nothing to either sum | [P] **resolved**; [L] empty strata |
| S-6a | **Orientation, fixed:** a_i = #(EE < 0.3, SILENT), b_i = #(EE < 0.3, MATCH), c_i = #(EE ≥ 0.3, SILENT), d_i = #(EE ≥ 0.3, MATCH), n_i = a_i + b_i + c_i + d_i; OR_MH = Σ_i (a_i d_i / n_i) / Σ_i (b_i c_i / n_i). **OR > 1 means low EE (EE < 0.3) is associated with greater odds of SILENT.** In bootstrap replicates the counts are multiplicity-weighted | [F] orientation (§12 G4); [L] formula |
| S-8 | Logistic model: logit P(SILENT) = α_s + β·EE, one intercept α_s per merged stratum s and no global intercept; β per unit EE (EE ∈ [0, 1]); **β < 0 means higher EE is associated with lower odds of SILENT** (the same direction as OR > 1). Maximum likelihood by Newton/IRLS in NumPy (no SciPy), weighted by bootstrap multiplicities in replicates | [P] **resolved** |
| S-8b | A stratum with zero total weight (observed or in a replicate) has no α column; its intercept is unidentified and does not affect the estimate of β. The S-13a checks apply to the reduced design | [P] **resolved**; [L] β invariance |
| S-7 | Intervals for OR_MH and β: OC-2's own, separately approved cluster bootstrap with the occurrence-sum rule of `E2_SPEC.md` E2-8 (**not** C-d §4.1). Seeds S = (12, …, 21) ascending; node universe U_s = X values with at least one MATCH/SILENT opportunity in seed s, ascending; one `numpy.random.Generator(PCG64(12345))`; B = 10,000; per replicate: `integers(0, 10, 10)` seed occurrences, then for each occurrence in order `integers(0, \|U_s\|, \|U_s\|)` (no call if \|U_s\| = 0); multiplicity of (s, X) = sum of X's counts over all occurrences of s; every opportunity of (s, ·, X) carries that multiplicity. Two-sided 95% percentile interval: 2.5th and 97.5th percentiles, linear interpolation over all 10,000 values | [P] **resolved** |
| S-7c | **One shared draw sequence:** the B = 10,000 replicate draws are generated once and reused for every (g, k) point and for both statistics (OR_MH and β). Since U_s does not depend on (g, k), the replicates are identical across points | [P] **resolved** |
| S-7a | "Interval excluding 1" for OR_MH = lower endpoint > 1; "negative" for β = upper endpoint < 0 | [L] |
| S-9 | **Descriptive rule only:** the statement "EE is associated with SILENT at every active point" is made only if, at every active point at k = 1.5, OR_MH's lower endpoint > 1 and β's upper endpoint < 0; otherwise the per-point estimates are reported without that statement. No pass/fail, no gate, no downstream consequence; no multiplicity adjustment; every active point reported. Negative wording: "In the replayed E1 traces of this simulator, EE is not associated with how reliable the evidence is" | [F] "at every active point" (§12); [L] no adjustment |
| S-10 | **Secondary k (1.0, 2.0):** all §4–§5 quantities computed with the same rules and shared draws, reported in separate tables labelled "secondary (k = 1.0)" and "secondary (k = 2.0)", in full whatever they show. They never enter the activity finding or the S-9 statement and are never used to select a k, a g or a presentation | [F] §10 (one at a time); [P] **resolved** role |
| S-11 | If no grid value is active at a given k, the EE–evidence relationship at that k is "not evaluable" | [L] |

## 6. Failure handling (no fallback of any kind)

| ID | Rule | Tag |
|---|---|---|
| S-13 | **Observed-data failure is a hard stop.** If the observed data at an active point give an undefined or zero-denominator OR_MH (Σ_i b_i c_i / n_i = 0), complete or quasi-complete separation, a singular design, IRLS non-convergence, or any non-finite odds ratio, coefficient or slope: stop and report. In the observed data no merged stratum has only one outcome (every q_s ∈ (0, 1), `README.md` §7 step 1) | [P] **resolved** |
| S-13b | **Bootstrap-replicate failure.** If the observed data are identifiable but any replicate meets an S-13a criterion: no value is substituted and no replicate is discarded or redrawn; the affected interval is reported as **not evaluable under the frozen bootstrap specification**, and OC-2 stops and reports instead of producing intervals. Such a replicate is a property of the resampling, **not a substantive finding about the data**. Non-finite interval endpoints are treated the same way | [P] **resolved** |
| S-13a | **Detection criteria, fixed, applied after S-8b:** IRLS from β = 0 and all α_s = 0, at most 100 iterations, converged when max \|Δ(coefficients)\| < 1e-10; separation if any fitted probability is within 1e-12 of 0 or 1 at termination, or any positive-weight stratum has only SILENT or only MATCH; singular if the design-matrix condition number exceeds 1e12 or EE is constant; OR_MH undefined if Σ_i b_i c_i / n_i = 0 | [P] **resolved** |
| — | **Never:** continuity corrections, regularization, alternative estimators, altered model specifications, substitute values, discarded or redrawn replicates, or tuning, without a separate approved decision | — |

## 7. Parity validation (procedural, not a result)

| ID | Rule | Tag |
|---|---|---|
| P-1 | Before any result is produced, a parity harness compares, on the E1 runs: (a) offline p(d) at Eb/N0 40 dB and k = 1.5 with each logged first-hearing `[EAQTE-CCQ]` value (the C++ history is reset when a neighbour entry is overwritten, so at first hearing it holds one sample and CCQ = p); (b) offline SS computed with **the C++ input convention** (X's two most recent positions **including** the decode being logged; the observer's own velocity from E-7) with the logged `[EAQTE-SS]` value. Tolerance: the 6-significant-digit print resolution of the log lines; events within print resolution of a whole second (E-3/E-7 tie rule) are counted and reported separately. `[EE]` and `[SSCCQ]` are not compared (they carry the C++ history reset). **Any unexplained mismatch is a hard stop.** Parity cannot validate the E-4/E-5 history rule; that is covered by unit tests only (§10) | [P] **resolved** |

## 8. Procedure, outputs and reproducibility

| ID | Rule | Tag |
|---|---|---|
| R-1 | Outputs: `analysis/stageE/oc2/oc2_results.json` and `analysis/stageE/oc2/oc2_report.txt`; the evaluator refuses to overwrite either; a stop writes no result file and reports to stderr | [P] **resolved** |
| R-1b | Code: `analysis/stageE/oc2/oc2_evaluate.py` and `analysis/stageE/oc2/test_oc2_evaluate.py`. The evaluator refuses to run on seeds 12–21 unless both are committed and unmodified | [P] **resolved** |
| R-1c | Recorded md5s: per run `stderr.log`, `v1_N.tr`, `v1_N_mobility.csv`, `e1_opportunities.csv`; `e1_calibration_rev4.json`; this document; `OPTION_C_TRANSITION.md`; the evaluator and test file; plus parent and submodule commits, Python and NumPy versions | [P] **resolved** |
| R-2 | An independent second evaluation, written to a separate location, must give a canonical JSON identical apart from `created_utc`; otherwise hard stop | [P] **resolved** |
| R-3 | No regime, Eb/N0 value, k or presentation selected after results | [F] §10 |
| OC-1 | OC-1 is a written synthesis at `analysis/stageE/OC1_SYNTHESIS.md` citing committed records by commit and md5; it recomputes nothing | [P] **resolved** |
| Labels | OC-1 and OC-2 as defined in `OPTION_C_TRANSITION.md`; E3, E4 and E5 are not reused | [P] **resolved** |
| Scope | No Arm C; C++ EAQTE log lines used only by P-1 | [P] **resolved** |

## 9. Resolution audit

| Item in `OPTION_C_TRANSITION.md` §11 | Status here |
|---|---|
| E-7 | **[L]**, source-verified (approved as proposed); no longer a proposed interpretation |
| S-1 | [P] resolved |
| S-4 (primary k) | **[L]** (`README.md` §1, §10); approved as proposed |
| S-6 (with S-6a) | [P] resolved; orientation [F] |
| S-7 (with S-7c) | [P] resolved |
| S-8 (with S-8b) | [P] resolved |
| S-10 (role) | [P] resolved |
| S-12 | [P] resolved, **with fixed-width bins replacing the deciles proposed in the transition document** (approved change: bin edges no longer depend on the data) |
| S-13, S-13a, S-13b | [P] resolved |
| R-1 (with R-1b, R-1c), R-2 | [P] resolved |
| Labels; OC-1 form and path; no Arm C; parity-only C++ log lines (P-1) | [P] resolved |

No [P] item remains open for OC-2. Items confirmed from source as [L] beyond the transition document: E-2 (3D distance), E-4 (append-then-compute; O1 event order), E-5 (population variance; clamp), E-6 (cos clamp), E-8 (norm threshold 1e-6).

## 10. Tests required before any OC-2 run

On synthetic data and development seed 1 only (`~/uwsn-runs/rxhdr_seed1/c_tq_a`, clean); never seeds 12–21:
1. p(d) against `eaqte_operating_point/ee_bound.py` across g and k; E-1 to E-9 on hand-constructed cases (history order and window, append-then-compute, population variance, CCQ = p with one sample, SS defaults, cos clamp, freeze threshold strict).
2. Regimes S-2 to S-4 on constructed populations.
3. OR_MH on a known stratified table with OR > 1 against an exact rational calculation with the S-6a orientation, and its reversal giving 1/OR; empty strata.
4. Logistic fit against a brute-force likelihood maximum; S-8b (an empty stratum leaves β unchanged).
5. The E2-8 worked example (multiplicities (3, 1, 1), FA\* = 0.500) for the S-7 draw rule; S-7c (identical draws reused across points and statistics; determinism).
6. Every S-13 failure (zero-denominator OR, complete and quasi-complete separation, constant EE, iteration cap, non-finite values) stops; the S-13b distinction (identifiable observed data with a constructed degenerate replicate: observed estimate returned, interval not evaluable, stop, no interval).
7. Percentiles by linear interpolation; refusal to overwrite; R-1b guard; JSON determinism.
8. The P-1 harness on development seed 1 (parity against its own C++ log lines).

## 11. Execution sequence

1. Commit this document and D-23.
2. Write and test the OC-2 evaluator and tests (§10); commit them by explicit path before they read seeds 12–21.
3. Verify the input md5s (§2); run P-1 parity; then Evaluation 1 (R-1) and Evaluation 2 (R-2).
4. Record the results with an `EXPERIMENT_LOG.md` entry; then OC-1.

Each step stops for approval. Nothing is pushed without a separate instruction (submodule first).

## 12. Revision log

| Date | Revision |
|---|---|
| 2026-10-05 | Approved: all [P] items of `OPTION_C_TRANSITION.md` §11 resolved (E-7 and S-4 as [L]; S-12 fixed-width bins; S-6a orientation; S-7/S-7c shared OC-2 bootstrap; S-8/S-8b; S-10; S-13/S-13a/S-13b; R-1/R-1b/R-1c; R-2; P-1; OC-1 path; labels; no Arm C). Not implemented |
