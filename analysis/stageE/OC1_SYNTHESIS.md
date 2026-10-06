# Stage E — OC-1: Oracle-free evidence and observability characterization (synthesis)

**Status:** written synthesis under C-β (`OPTION_C_TRANSITION.md` §5, D-22; form and path approved in D-23, `OC2_SPEC.md` row OC-1). **It is not an experiment and not a gate.** It recomputes nothing: every number below is quoted from a committed record cited by commit and md5. Raw simulation data outside the repository are used only through those committed records (`OPTION_C_TRANSITION.md` §8). In this document `README.md` means the Stage E specification `analysis/stageE/README.md`, not the repository-root README.

Contents:
1. Provenance
2. Evidence layer and `[RXHDR]` logging
3. E1 calibration record, revisions 2–4
4. C-d and G1′
5. E2 held-out evaluation
6. Observability ceiling and limitations
7. Supported methodological findings
8. Claim limits
9. Relation to OC-2
10. Limitations
11. Revision log

---

## 1. Provenance

**Specification and decision records** (they define rules and record decisions; they contain no experimental result):

| Record | Commit | md5 |
|---|---|---|
| `analysis/stageE/README.md`, revision 4 (frozen specification; revision 2 frozen at `c0d2cec`, revision 3 at `e9ddf04`; superseded text kept verbatim in its §17 and §18) | `8a0ff2f` | `5d1dc27a2bab14ae590e93c3ee2cc3fa` |
| `analysis/stageE/CD_EVALUATION_FRAMEWORK.md` (C-d) | `362cda7` | `e2005a103015ccadfd365a2d1f4785bf` |
| `analysis/stageE/E2_SPEC.md` | `a87ffbc` | `7f37d81dbc8cc4b823c2036e80190960` |
| `analysis/stageE/OPTION_C_TRANSITION.md` (C-β) | `27f98ad` | `a40cfc87d84e67e2c16ca99541d37a4b` |
| `analysis/stageE/OC2_SPEC.md`, revision 2 (cited only for the OC-1 form and path) | `a984fc7` | `f0b83d29395972982e7ce34c389b77d7` |
| `analysis/stageE/e1/diagnostics_rev3/README.md` (revision-3 design-basis diagnostics, provenance only) | `e9ddf04` | `6d1586c99e1a2a3b41cc11ea1a04d919` |
| `analysis/stageE/e1/diagnostics_rev3/v6_diag2_output.txt` (provenance only; determines no threshold, bin or n_min) | `e9ddf04` | `a715c562b8e034d440756c576e3fa369` |

Decision rows in `RESEARCH_DECISIONS.md`, cited by the commit that introduced each row: D-13 to D-16 `46594aa`; D-17 `e9ddf04`; D-18 `c2a5077`; D-19 `362cda7`; D-20 `a87ffbc`; D-21 `3eba654`; D-22 `27f98ad`; D-23 `98bfcf2`. D-13 is cited for its decision context only; the implementation and result state of revision 4 is taken from E-34 (`103e671`).

**Experimental-result records** (outputs of executed runs and evaluations):

| Record | Commit | md5 |
|---|---|---|
| `analysis/stageE/rxhdr_validation/validation_output.txt` (`[RXHDR]` validation, E-31) | `46594aa` | `579e8fae50ee8042a01644c939ed0d6f` |
| `analysis/stageE/rxhdr_validation/checksums.txt` (E-31) | `46594aa` | `5f421aba55e801a629edd022f0be18b7` |
| `analysis/stageE/e1/e1_calibration.json` (revision 2, E-32) | `58cc50c` | `6504d1df09d5daaeef4e835611e424d4` |
| `analysis/stageE/e1/e1_calibration_report.txt` (revision 2, E-32) | `58cc50c` | `72dac4fa0e28fb424031e40ceee09755` |
| `analysis/stageE/e1/e1_validation.txt` (revision 2, E-32) | `58cc50c` | `fc56479f83fd740bf4be7a880530263f` |
| `analysis/stageE/e1/e1_calibration_rev3.json` (E-33) | `b016a9a` | `f49e6f764088bd500ef302dc01a281c1` |
| `analysis/stageE/e1/e1_calibration_report_rev3.txt` (E-33) | `b016a9a` | `ed55425aa2efaf9c0c27db09c36a36d7` |
| `analysis/stageE/e1/e1_validation_rev3.txt` (E-33) | `b016a9a` | `8b67d376761e067c99fa8c120f9441c4` |
| `analysis/stageE/e1/e1_calibration_rev4.json` (E-34) | `103e671` | `0ca88a0e4c8fc56f63e6b44b496b65fd` |
| `analysis/stageE/e1/e1_calibration_report_rev4.txt` (E-34) | `103e671` | `747b54274791da544a9c9d50c3856230` |
| `analysis/stageE/e1/e1_validation_rev4.txt` (E-34) | `103e671` | `6b3086e3657dffb8fe40986b9f1fa69d` |
| `analysis/stageE/e2/e2_results.json` (E-35) | `ca1edc7` | `efd14b3b9f9398318deccaf9f969ac97` |
| `analysis/stageE/e2/e2_report.txt` (E-35) | `ca1edc7` | `75ef38a6852dcdd7825289579ce81c57` |

Experiment-log entries in `EXPERIMENT_LOG.md`, cited by the commit that introduced each entry: E-31 `46594aa`; E-32 `58cc50c`; E-33 `b016a9a`; E-34 `103e671`; E-35 `ca1edc7`; E-36 `4dd4962` (§9 only).

**Frozen code that produced the E2 result** (committed before any E2 data existed, E-35): `analysis/stageE/e2/e2_evaluate.py` `e65000be640e4153809ed31a4d5cd647` and `analysis/stageE/e2/test_e2_evaluate.py` `4da0069fa158f1f3e74c58be62ac1f11`, commit `36655b7`. C++ state for all Stage E runs: aqua-sim-ng submodule `41c67c3` (`[RXHDR]` logging only).

E2 raw-data manifests, as recorded in E-35 (outside the repository; not recomputed here): Phase-1 manifest of 160 files `1616648ba5211a947bb834f31d51aaec`; original `E2/` (180 files) `f32617b3b56f590d35039ac558758ca2`; `E2_repeat/` (180 files) `713e3ca240997063735f23a6fd6dbc9a`.

## 2. Evidence layer and `[RXHDR]` logging

**Framework** (D-13, D-15, D-16; `README.md` §5–§7). The evidence layer is common to the trust arms and oracle-free. Arm labels are as frozen in D-13 (Arm 0 plain HH-VBF; Arm A observer-based trust, no environmental gate). Under S1 (`PriorityScale=0`, `ObservedTrustWeight=0`) trust never affects forwarding. Under S2 (D-15) one logging-only C++ change is permitted solely to expose the exact receiver-decoded header fields; no behaviour-changing C++ change is permitted.

**Information boundary** (`README.md` §5). The observer O may use only: `[RXHDR]` lines of copies O decoded; O's own position, velocity and own transmissions; O's neighbour table built from copies decoded strictly before the event; and public protocol constants. The custody tag, `[DECISION]`/`[HOLD]`/`[VERDICT]`/`[OBSERVER] DROP` lines, the malicious list, other nodes' true positions, and any reception or transmission O did not decode are ground truth for evaluation only. Ground-truth fields live in an evaluation module the observer module cannot import; check V5 audits this statically.

**O1, opportunity construction** (`README.md` §6; exactly as validated in Stage D, O1-H OFF). A source event at t₀ (O decodes U's copy, or O itself transmits); candidates X last heard ≤ 60 s before t₀; eligibility from X's last-known position (R, W and the Aqua-Sim α ≤ 1.5 rule); ranking by HH-VBF hold time; hearing filter; outcome by the Stage D rule: **MATCH** (X's copy with recovered upstream within ε = 25 m of f_U), **OTHER-UP** (X's copy, upstream > 25 m; excluded, never blamed or credited), **SILENT** (no copy of P from X); 8 s timing rule.

**O2 strata** (`README.md` §7): K1 role (O = U or O ≠ U), K2 predicted α′ rank of X (1, 2, ≥ 3), K3 age of X's table entry (≤ 20 s, 20–40 s, 40–60 s), merged by the frozen merge rule.

**`[RXHDR]` logging and validation** (E-31, D-15; archive `analysis/stageE/rxhdr_validation/`). Purpose: replace the Stage D offline header rebuild, which used simulator ground truth, with the header values each receiver actually decoded. Logging only: 8 inserted lines in `AquaSimTrustQVBF::Recv` (submodule `41c67c3`). Seed/run 1, development/diagnostic.
- Behaviour unchanged: energy, mobility, trust, observed, meta and stdout byte-identical; stderr identical after removing `[RXHDR]` lines; trace 0 differing records after masking `token=`, `ts=`, `range=`.
- Coverage: `[RXHDR]` lines = trace `r` records, one-to-one (26303 / 26180 / 26106).
- Decoded values: 0 mismatches beyond 6-digit print resolution against the printed trace; 0 f and 0 d mismatches against the Stage D rebuild on all non-ambiguous transmissions (the 34–40 ambiguous transmissions per run differ by at most 0.30 m, which cannot change any MATCH/OTHER-UP outcome).
- Upstream recovery from the decoded values alone: **max 0.601 m**, median 0.300 m.
- Status: PASS; accepted as the final D1 change.

**Trace defect** (D-16; E-31). VBHeader `token`, `ts` and `range` are a pre-existing Aqua-Sim-NG trace defect (uninitialised fields). Nothing in VBF/TrustQVBF reads them; they are permanently masked in every behavioural trace comparison and are not fixed.

## 3. E1 calibration record, revisions 2–4

All three evaluations used the clean calibration seeds 12–21 (attackerFraction 0). V6 on seeds 12–21 is development validation; the independent false-alarm assessment is G2b on seeds 2–11 (D-17; E-34).

| | Revision 2 (E-32) | Revision 3 (E-33) | Revision 4 (E-34) |
|---|---|---|---|
| Specification | `c0d2cec` | `e9ddf04` (D-17) | `8a0ff2f` (D-18) |
| Result record | `58cc50c` | `b016a9a` | `103e671` |
| Calibration file md5 | `6504d1df09d5daaeef4e835611e424d4` | `f49e6f764088bd500ef302dc01a281c1` | `0ca88a0e4c8fc56f63e6b44b496b65fd` |
| Failing check | **V3** (minimum separation 39.9 m < 50 m) and **V6** (pooled out-of-seed FA 76/398 = 0.191, one-sided 95% lower bound 0.115 > 0.05) | **V6-B** (in 5/10 folds no bin reaches power 0.80; n_min undefined) | **V6-B** (n_min undefined in the full calibration and in all 10 folds; no bin has lower confidence bound ≥ 0.80; full-calibration maximum 0.668; fold maxima 0.538–0.719) |
| Passing checks | V1, V2, V4, V5, V7, V8 | V1, V2, V4, V7, V8 (carried), V3-a, V5 (extended), **V6-A** (pooled out-of-seed FA 25/476 = 0.0525; one-sided 95% lower bound 0.0156) | V1, V2, V3-a, V4, V5, V7, V8, **V6-A** (pooled out-of-seed FA 110/2,057 = 0.0535, not significantly above 0.05; lower bound 0.0297) |
| G1 | **FAIL** | **FAIL** | **FAIL** |

- **Revision 2** (E-32): 229,309 opportunities (MATCH 108,667, SILENT 66,033, OTHER-UP 54,609); 2,668 (seed, O, X) pairs. Calibration q̄ = 0.377979, n_ref = 14, τ_A = 9.332958 (N = 2,044 pairs), n_min = 98; calibration FA at n ≥ n_min 74/453 = 0.163. **Over-dispersion: var(Z) = 28.98 (1 expected), rising with n.** The V3 failure misclassified no outcome (all nine close separations > ε).
- **Revision 3 design basis** (`README.md` §13 R3-1; provenance-only diagnostics in `e1/diagnostics_rev3/`): var(Z) 29.0 and rising with n; **a pair's silence propensity is persistent (first-half vs second-half residual correlation 0.76)**; in-sample FA at the revision-2 τ_A rises from 0.000 (n 14–27) to 0.339 (n ≥ 250). The diagnostic output records the correlation as 0.759 for 1476 pairs with n ≥ 40.
- **Revision 3** (E-33): n-binned empirical thresholds (9 bins, M = 200); n_min = 76, but power is strongly non-monotone in n (bins 7–9: 0.590, 0.366, 0.600), so the lower edge of the smallest qualifying bin does not guarantee ≥ 0.80 power for the judged population. V6-A / V6-B split as the reporting classification decided on 2026-10-05.
- **Revision 4** (E-34, `103e671`): implemented and evaluated using the frozen specification. G1 fails under revision 4. **The frozen D4-5 stop rule applies:** stop and open the separately scoped Option C discussion; no further redesign aimed at reaching 0.80 power. No attacker seeds were used.

## 4. C-d and G1′

C-d (`CD_EVALUATION_FRAMEWORK.md`, `362cda7`, D-19) is a new evaluation framework adopted after the D4-5 stop as the outcome of the first Option C discussion. It is **not** another calibration redesign aimed at 0.80 power; D4-5 stays in force.

- **G1′ = V1–V5, V7, V8, V3-a and V6-A all pass. This holds already (E-32 to E-34).** G1′ only permits the relative evaluation of C-d; it is not G1, and **G1 remains FAILED (V6-B)** (C-d §5).
- **The V6-B / G1 failure is a permanent revision-4 result. C-d does not retroactively make G1 pass.** Revision 4 remains frozen and unchanged (C-d §0).
- **No power guarantee (0.80 or any other) exists for any arm** (C-d §0).
- C-d fixed the J1 judged population (n ≥ 14, n_ref = 14) used by E2 (D-19, D-20). Its later-stage endpoints were not reached, because E2-14 stopped the roadmap (§5).

## 5. E2 held-out evaluation

**Record:** E-35 (`ca1edc7`), D-21 (`3eba654`). Specification `E2_SPEC.md` (`a87ffbc`, D-20), within C-d (`362cda7`) and revision 4 (`8a0ff2f`). Arm A only. Seeds 2–11; p = 0.75 runs feed G2/G2b, p = 1.0 runs feed only the ceiling table. No recalibration: frozen revision-4 calibration `e1_calibration_rev4.json` (`0ca88a0e4c8fc56f63e6b44b496b65fd`). Evaluator and tests committed at `36655b7` before any E2 data existed.

**Integrity** (E-35):
- Phase 1: 20 simulations. A local run-checker incident (the checker required a non-empty `stdout.log`) was recovered under the approved option (a) by correcting only the checker; the 8 completed runs were verified without rerunning. **No simulation was rerun to hide or replace an output.**
- Phase 2 (O1): 20/20 observer runs exit 0; raw simulation files unchanged.
- Phase 3, reproducibility (E2-12): **PASS** (160/160 CSV and log files byte-identical; 20/20 traces with 0 records differing after masking `token`, `ts`, `range`).
- Phase 4: two evaluations identical apart from `created_utc` (canonical JSON md5 `1d7c88ceac56f63a8a37858c7e927d33` for both). **PASS.** Results: `e2_results.json` `efd14b3b9f9398318deccaf9f969ac97`, `e2_report.txt` `75ef38a6852dcdd7825289579ce81c57`.

**Population (p = 0.75):** judged honest pairs |H| = 1,383; judged active-malicious pairs |D| = 306; 36 distinct (seed, X) in D. Bootstrap: B = 10,000, NumPy PCG64(12345), seeds then X nodes with occurrence-specific draws; zero-denominator replicates 0 (FA, TDR, AUC).

**Gates** (E-35):

| Gate | Value | Criterion | Result |
|---|---|---|---|
| G2 | 306 judged active-malicious pairs; 36 distinct (seed, X) | ≥ 43 and ≥ 10 | **PASS** |
| G2b item 1, FA | point 73/1,383 = 0.0528; 5th percentile 0.0304 | ≤ 0.05 | **PASS** |
| G2b item 2, AUC | point 0.9055; 2.5th percentile 0.8464 | ≥ 0.70 and > 0.5 | **PASS** |
| G2b item 3, TDR vs FA | TDR point 105/306 = 0.3431; TDR 2.5th percentile 0.0846; FA 97.5th percentile 0.0873 | TDR 2.5th > FA 97.5th (strict) | **FAIL** (by 0.0027) |
| **G2b** | | all three | **FAIL** (fully interpretable: G2 passed) |

**Status (E2-14, applied exactly):** **G2b FAIL.** Frozen conclusion: "Oracle-free overhearing evidence does not separate droppers from honest nodes at the declared false-alarm rate." The roadmap stops; the Option C discussion follows; E3, E4 and E5 do not run.

**This result is final under the frozen E2 specification.** The two-sided reading in G2b item 3 was a proposed interpretation frozen in `E2_SPEC.md` before any E2 data existed. The E2 result is not retroactively altered by any alternative statistical interpretation, and none was computed (E-35, D-21).

## 6. Observability ceiling and limitations

**Rules** (`README.md` §9). The ceiling is reported separately from detection metrics. Only **judged and missed** counts as a false negative of the trust algorithm. **Unobservable and insufficient cases are evidence limits, never algorithm errors.** Coverage = TDR × fraction judged is reported separately, labelled as system coverage. p = 1.0 runs appear only in the ceiling table.

**Ceiling table** (E-35, E2-10; descriptive, no gate):

| Pooled over seeds 2–11 | p = 1.0 (ceiling) | p = 0.75 (alongside) |
|---|---|---|
| Ground-truth drops | 4,035 | 3,093 |
| Observable (any / O = U / O ≠ U) | 0.142 / 0.136 / 0.142 | 0.640 / 0.534 / 0.633 |
| Active-malicious (seed, X) | 42 | 46 |
| Unobservable / insufficient / detected / missed | 34 / 0 / 7 / 1 | 2 / 8 / 14 / 22 |
| Inactive-malicious (seed, X) | 158 | 154 |
| Honest nodes judged | 139/790 | 142/790 |
| TDR (pairs); share of active nodes judged; system coverage | 0.531; 0.190; 0.101 | 0.343; 0.783; 0.269 |

- At p = 1.0, seeds 3, 7, 10 and 11 have no observable drop and every active-malicious node is unobservable.
- At p = 0.75, per-seed pair TDR ranges from 0 (seeds 6, 8, 9) to 0.900 (seed 2, 9/10); seed 10 contributes 59/81.

**Limitation.** Observability is a first-order limit (`OPTION_C_TRANSITION.md` §5.2 item 5). The ceiling applies only to the simulated topologies, mobility, range propagation and the declared attacker (`OPTION_C_TRANSITION.md` §5.3).

## 7. Supported methodological findings

These are the findings of `OPTION_C_TRANSITION.md` §5.2, with their records.

1. Oracle-free per-pair evidence can be built from receiver-decoded headers only, with checks V1, V2, V4, V5, V7, V8 and V3-a passing (E-32 to E-34; the revision-2 V3 rule failed and was replaced by V3-a in revision 3).
2. Honest silence propensity is persistent per (O, X) pair and over-dispersed beyond the K1–K3 strata (E-32, E-33). This pair-persistent heterogeneity left no verified 0.80-power region under the declared calibration and validation setup: n_min is undefined in the full calibration and every fold (E-34). Recorded as a limitation of per-pair overhearing evidence (D4-5).
3. The per-bin false-alarm calibration transfers: within the declared 5% bar both in development validation (V6-A, E-34) and on independent held-out seeds (G2b-FA, E-35).
4. On held-out seeds, the evidence ranks droppers above honest nodes (AUC 0.9055; 2.5th percentile 0.8464) but **fails the declared detection bar** at the per-bin thresholds (E-35). Both halves are always reported together.
5. Observability is a first-order limit: at p = 1.0 only 14.2% of drops are observable and 34 of 42 active malicious (seed, X) nodes are never observable; at p = 0.75, 64.0% (E-35).
6. Simulations are deterministic apart from three uninitialised VBHeader fields that nothing reads (E-31, E-35 Phase 3).

**Contribution supported by this evidence** (`OPTION_C_TRANSITION.md` §9, OC-1 items):
- An oracle-free, opportunity-conditioned overhearing evidence layer for beaconless HH-VBF, with a documented validity record and a reproducible held-out evaluation.
- Quantified limits of that evidence: pair-persistent heterogeneity that left no verified 0.80-power region under the declared calibration and validation setup; false-alarm calibration that transfers to held-out seeds; ranking ability (AUC 0.906) that nevertheless fails the declared detection bar; and an observability ceiling dominated by unobservable droppers.

## 8. Claim limits

**Not supported by OC-1** (`OPTION_C_TRANSITION.md` §5.3): any claim of secure-routing improvement; any detection guarantee, power or n_min; that G2b "nearly passed" or any alternative reading of E2; generalization beyond the simulated topologies, mobility, range propagation and the declared attacker.

**C-β does not claim** (`OPTION_C_TRANSITION.md` §9):
- validated secure-routing (or forwarding) improvement by EAQTE, PACT or observer trust;
- successful G5 or G6 validation, or that an EAQTE blind spot exists or does not exist;
- successful end-to-end PACT improvement;
- revival of the original E3/E4/E5 roadmap, or a revived G3 or G4 gate;
- network behavior at Eb/N0 values other than the simulated condition;
- any calibrated power, detection guarantee or n_min (C-d §8);
- that "EAQTE fails";
- that G2b nearly passed, or any alternative reading of E2;
- generalization beyond the simulated network, mobility, range propagation and declared attacker. EE findings under range propagation, where decoding does not depend on distance, say nothing about real acoustic channels.

Scope (D-13): Stage E is security-mechanism validation only and must not be described as showing that observer trust improves HH-VBF forwarding performance.

## 9. Relation to OC-2

OC-2 Evaluation 1 stopped under the frozen S-13b rule and OC-2 produced no result (`EXPERIMENT_LOG.md` E-36, commit `4dd4962`); the stop is procedural and not a substantive finding, and OC-1 draws nothing from it.

## 10. Limitations

- With 10 seeds per family, bootstrap error rates are approximate; the direction of any error (from few clusters versus two-stage resampling) is not known (C-d §11).
- No power guarantee exists for any arm (revision-4 V6-B failure, E-34; C-d §11).
- The calibration and its development validation used clean seeds 12–21, which also informed revisions 3 and 4. The independent false-alarm assessment is G2b on seeds 2–11 (C-d §11).
- Results apply to the simulated topologies and the declared attacker configuration only (C-d §11), under range propagation, where decoding does not depend on distance.
- Seeds 22–31 and 41–50 remain sealed and unused; seeds 32–40 are unused; seed 1 is development only (D-14; `OPTION_C_TRANSITION.md` §3).
- The C-d §4.1 multiplicity inconsistency stays open for any future G5/G6 work; neither E2 nor C-β uses C-d §4.1 (D-20, D-22).

## 11. Revision log

| Date | Revision |
|---|---|
| 2026-10-06 | Written as the OC-1 synthesis under C-β (`OPTION_C_TRANSITION.md` §5; form and path per D-23). Cites committed records only; recomputes nothing |
