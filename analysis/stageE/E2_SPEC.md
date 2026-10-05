# Stage E — E2 specification (held-out Arm-A test, seeds 2–11)

**Status:** approved 2026-10-05; frozen when committed. Decision record: `../../RESEARCH_DECISIONS.md` D-20. **E2 has not been run:** no E2 simulation, opportunity file or analysis exists, and seeds 2–11 are unopened.

This document fixes, before any E2 data exist, every E2 detail that the frozen sources leave open. It changes nothing in them:
- the revision-4 specification `README.md` (commit `8a0ff2f`);
- the C-d framework `CD_EVALUATION_FRAMEWORK.md` (commit `362cda7`, D-19);
- the revision-4 Arm-A calibration `e1/e1_calibration_rev4.json` (md5 `0ca88a0e4c8fc56f63e6b44b496b65fd`);
- O1 code and E1 artefacts.

Where the frozen sources and this document differ, the frozen sources win and E2 stops for review.

Contents:
0. Classification tags
1. Classification audit
2. Specification E2-1 to E2-14
3. Source note: C-d §4.1 multiplicity wording
4. Direction of the proposed interpretations
5. Revision log

---

## 0. Classification tags

Every rule below is tagged:
- **[F]** explicitly frozen in `README.md` (revision 4) or C-d; the source is cited.
- **[L]** logically implied: the frozen text admits no other reading.
- **[P]** proposed interpretation, approved 2026-10-05 and frozen by this document. It is not a frozen rule of revision 4 or C-d.

## 1. Classification audit

Items earlier classified as "directly implied", audited strictly. An inference is not upgraded to [F] or [L] merely because it yields a plausible derivation.

**Downgraded to [P]:**

| Item | Why it is not frozen or implied |
|---|---|
| The resampled node is X | `README.md` §7 says only "nodes within seeds", which could mean O or X. C-d §4.1 names X, but for G5/G6 only. |
| The FA test's level is 95% | The FA bar states no level. The 95% used in the other bars is suggestive, not binding. |
| The TDR bound is two-sided | See below. |
| "FA upper bound" means E2's held-out upper confidence bound | The phrase could also be read as the 0.05 bar itself. |
| Distinct nodes counted as (seed, X) | §7 defines pairs as (seed, O, X) but never defines node identity across seeds. |
| G2's "10 nodes" counts active-malicious nodes only | Only G2's 43-pair figure is tied to TDR. C-d §4.6 applies 43/10 to D_k, but that is C-d's precision minimum, not a redefinition of G2. |
| Inactive-malicious pairs are excluded from AUC | §7 excludes them from "TDR and FA" only; "AUC over judged pairs" is silent. |
| A lower bound exactly 0.05 counts as a pass | A convention. The V6-A code uses ≤, but that is implementation, not frozen text. |

**Confirmed as [L]:**

| Item | Why it is implied |
|---|---|
| FA test direction: the one-sided lower bound is compared with 0.05 | A one-sided test of "significantly above 0.05" rejects only when the one-sided lower bound exceeds 0.05. |
| G2's 43 pairs counts judged active-malicious pairs only | G2 ties the 43 to the "TDR 95% CI half-width", and the TDR denominator excludes inactive-malicious pairs [F §7]. |
| Pairs whose observer O is malicious are included | "honest: X not configured malicious" [F §7] makes (malicious O, honest X) an honest pair. FA is over "honest pairs" [F §7]. O1 excludes no observer [F §6]. |

**The TDR two-sided bound is an inference only, [P].**
- 43 is the smallest n with 1.96·√(0.25/n) ≤ 0.15, the worst-case two-sided normal-approximation interval. "Half-width" also implies a two-sided interval.
- But `README.md` states no formula, and other rules could also produce 43.
- More importantly, that sentence is G2's sample-size rationale: a planning calculation that assumes independent pairs. It does not define G2b's cluster-bootstrap "95% lower bound", which the frozen text leaves unqualified.
- Two-sided is adopted (E2-9) as the stricter choice: the 2.5th percentile instead of the 5th.

## 2. Specification

### E2-1 Scope

- **Arm A only** [F `README.md` §11].
- **Seeds 2–11 only** [F §4, D-14]. No other seed is simulated, characterised or inspected in E2.
- **p = 0.75 runs feed G2 and G2b; p = 1.0 runs feed only the ceiling table** [F §9, §11; C-d §10].

### E2-2 Simulation

20 runs, using the existing scenario binary `build/scratch/ns3.41-uwsn-trustq-attack-default` (md5 `54e444ed2ade8baf1c5fc3f54be5ad36`) and library `libns3.41-aqua-sim-ng-default.so` (md5 `871c50fc90cc613513ce25211cc8e450`, submodule `41c67c3`). For N = 2, …, 11:
```
analysis/runargs.sh ~/uwsn-runs/stageE/E2/p075/run_N --run=N --routing=trustq --priorityScale=0 --attackerFraction=0.2 --dropProbability=0.75
analysis/runargs.sh ~/uwsn-runs/stageE/E2/p100/run_N --run=N --routing=trustq --priorityScale=0 --attackerFraction=0.2 --dropProbability=1.0
```
- **Attacker settings [F §11 attacker table]:** AttackStart 0, AttackMode 0, adversarialMotion false.
- **Trust settings [F S1]:** ObservedTrustWeight 0, PriorityScale 0.
- **Network settings [F §1 project choices]:** range propagation, fixed sink, pinned RNG streams (`stream_base` 1000).
- **Environment:** `EAQTE_XI` and `RX_RANGE_M` unset.
- Each run's `_meta.csv` is checked against these values before any analysis.
- No C++ or scenario change [F S2].

### E2-3 O1

- The unchanged `e1/observer.py` (md5 `45d79f770c13f151bddee86b09bf96f6`) is run on each run directory, with the unchanged `e1/geom.py` (md5 `413d4f60b4efcdb125bf00c65d792e09`) [F §6].
- It writes `e1_opportunities.csv` into the E2 run directory. The name is kept so that O1 is the byte-identical code that passed G1′; the run path identifies the stage [P].

### E2-4 Statistic and judging

Everything comes from the frozen `e1/e1_calibration_rev4.json` [F C-d §1]. **No recalibration:** q_s, the merge map, n_ref, the bins and the thresholds are never re-estimated [F §7: "No attacker data is used to determine q_s, n_ref, bins, thresholds…"].
- Stratum rates q_s via the frozen merge map, which covers all 18 cells (9 merged strata).
- r = (K − E)/n over the pair's MATCH and SILENT opportunities; OTHER-UP is excluded [F §7].
- A pair is **judged iff n ≥ n_ref = 14** [F C-d §3, J1].
- Its bin is [L_b, L_{b+1}) with L = [14, 23, 34, 46, 61, 76, 89, 95, 139]; the last bin is [139, ∞) [F §7 step 3].
- A pair is **flagged iff r > τ_A,b** [F §7 step 3].
- Pairs with n > n_max = 554 are judged with τ_A,9 and reported separately [F §7 step 3], labelled only "above calibration n_max", since no power claim exists [F C-d §0].

### E2-5 Labels

From the unchanged `e1/truth.py` (md5 `203dbb7046bb1ad4323fdc222dfbacc8`), for evaluation only [F §5, §7]:
- **malicious:** X is in `_meta.csv` `malicious_nodes`;
- **active malicious:** malicious with at least one `[DECISION] act=DROP` in that run;
- **honest:** X not malicious;
- **inactive malicious:** malicious with no DROP in that run.

The label is a property of X within its run, not of the pair [F §7].

### E2-6 Populations and point statistics (p = 0.75 runs)

- **H** = judged honest pairs; **D** = judged active-malicious pairs.
- **All observers O are included,** whether malicious or not [L].
- **Inactive-malicious pairs are excluded** from FA and TDR [F §7] and from AUC [P].

| Statistic | Definition |
|---|---|
| FA | flagged pairs in H / \|H\| [F §7, C-d §3 D-Cd-6] |
| TDR | flagged pairs in D / \|D\| [F §7] |
| AUC | Mann–Whitney AUC with D as positives and H as negatives, score r [F §7]; ties count ½ [P]. AUC = Σ_{i∈D} Σ_{j∈H} [1(r_i > r_j) + ½·1(r_i = r_j)] / (\|D\|·\|H\|) |

### E2-7 G2: observability sufficiency

G2 passes iff both:
- **|D| ≥ 43** [F number §12; L population];
- **at least 10 distinct judged active-malicious nodes,** each counted as **(seed, X)** [P].

### E2-8 Cluster bootstrap (corrected)

**Basis:**
- The hierarchy, seeds then nodes within seeds, is [F `README.md` §7 "CIs"].
- Everything else here is [P]. B, the generator and the draw order are frozen only for V6 (§12) and for G5/G6 (C-d §4.1), not for G2b.
- No source contradiction requires changing B, the generator or the hierarchy.

**Units:**
- Seed list S = (2, 3, …, 11), ascending.
- Per seed s, the node universe U_s = the distinct X appearing in H ∪ D for seed s, sorted ascending (the observed X-node universe) [P].
- The resampled node is X [P]. **O is not resampled.**

**Generator:** one fresh `numpy.random.Generator(numpy.random.PCG64(12345))`, used for nothing else. **B = 10,000** replicates.

**Replicate b = 1, …, B, in order:**
1. **Seed occurrences:** σ = `integers(0, 10, 10)`, giving occurrences t = 1, …, 10.
2. **Within-seed node draw, separately for every occurrence:**
   - For t = 1, …, 10 in order, let s = S[σ_t].
   - If |U_s| > 0, draw ν_t = `integers(0, |U_s|, |U_s|)`.
   - If |U_s| = 0, make no draw and no generator call.
   - A seed drawn twice gets two independent node draws.
3. **Node multiplicity:** m_b(s, X) = Σ over occurrences t with S[σ_t] = s of #{j : U_s[ν_t,j] = X}.
   - That is, the **sum of X's counts across all occurrences of s**, and 0 if s is not drawn.
   - Check: Σ_X m_b(s, X) = c_b(s)·|U_s|, where c_b(s) is the number of occurrences of s.
4. **Pair multiplicity:** every pair (s, O, X) carries m_b(s, X).

**Replicate statistics** (sums over pairs i, with multiplicities m_i):
- FA\* = Σ_{i∈H} m_i·flag_i / Σ_{i∈H} m_i.
- TDR\* = Σ_{i∈D} m_i·flag_i / Σ_{i∈D} m_i.
- AUC\* = Σ_{i∈D} Σ_{j∈H} m_i·m_j·[1(r_i > r_j) + ½·1(r_i = r_j)] / (Σ_{i∈D} m_i · Σ_{j∈H} m_j).

**Zero denominators [P]:** a replicate whose denominator for a statistic is 0 takes the value least favourable to passing:
- FA\* = 1;
- TDR\* = 0;
- AUC\* = 0.

**No replicate is ever discarded.** The number of replicates in which this was applied is reported per statistic.

**Percentiles [P]:** linear interpolation (`numpy.percentile` default) over all 10,000 values.

**Consistency with V6-A:** the committed V6-A implementation (`e1/calibrate_rev4.py`, the bootstrap loop at lines 266–272) draws nodes inside the loop over seed occurrences and accumulates across occurrences. The corrected definition is therefore what V6-A computed; E-34 is unaffected.

**Worked example** (toy with 3 seeds, so `integers(0, 3, 3)`; E2 itself uses 10):
- **Universes:** U₂ = [5, 9], U₃ = [7], U₄ = [3].
- **Seed draw:** σ = [0, 0, 1], so seed 2 occurs twice and seed 3 once.
  - Occurrence 1 (seed 2): ν = [0, 0] → X5 ×2.
  - Occurrence 2 (seed 2): ν = [0, 1] → X5 ×1, X9 ×1.
  - Occurrence 3 (seed 3): ν = [0] → X7 ×1.
- **Corrected multiplicities:** m(2,5) = 2 + 1 = **3**, m(2,9) = 0 + 1 = **1**, m(3,7) = **1**, m(4,3) = 0.
  - Check: seed 2 gets 3 + 1 = 4 = 2·|U₂|, and seed 3 gets 1.
- **Honest pairs:** (2,1,5) flagged; (2,4,5) not flagged; (2,1,9) not flagged; (3,2,7) flagged.
- **Corrected FA\*** = (3·1 + 3·0 + 1·0 + 1·1) / (3 + 3 + 1 + 1) = 4/8 = **0.500**.

The rejected product formula, "(count of seed) × (count of X within that seed)", gives different answers depending on how it is read:

| Reading | Multiplicities (2,5), (2,9), (3,7) | FA\* |
|---|---|---|
| Uses occurrence 1's X counts | 4, 0, 1 | 5/9 = 0.556 |
| Uses occurrence 2's X counts | 2, 2, 1 | 3/7 = 0.429 |
| Uses X counts pooled over both occurrences (seed 2 effectively counted c² times) | 6, 2, 1 | 7/15 = 0.467 |

None of them equals the corrected 0.500.

### E2-9 G2b: false alarm and detection

G2b passes iff all three hold:
1. **False alarm:** the **one-sided 95% lower bound** of FA, i.e. the 5th percentile of FA\*, is **≤ 0.05**.
   - [F §7: "not significantly above 0.05 (one-sided, cluster bootstrap)"]
   - [L for comparing the lower bound with 0.05]
   - [P for the 95% level and for the ≤ boundary]
2. **AUC:** AUC ≥ 0.70 [F §7], **and** the **two-sided 95% lower bound** of AUC, i.e. the 2.5th percentile of AUC\*, is **> 0.5** [F bar; P for two-sided].
3. **TDR above FA:** the **two-sided 95% lower bound** of TDR (2.5th percentile of TDR\*) is **>** the **two-sided 95% upper bound** of FA (97.5th percentile of FA\*).
   - [F §7 bar]
   - [P for two-sided, and for reading "FA upper bound" as E2's held-out FA upper confidence bound]

The FA part (item 1) is the independent false-alarm assessment of the calibration [F §12 G2b].

**If G2 fails:**
- items 2 and 3 are computed and reported as **"not interpretable"** (below the 43/10 precision minimum) [P];
- item 1 is still decided [P].

**Observed-data zero denominator:** if H is empty, G2b-FA cannot be evaluated. G2b does not pass, and E2 stops and reports [P].

### E2-10 Ceiling table (descriptive; enters no gate)

- **p = 1.0** is the ceiling table [F §9]. The same quantities for **p = 0.75** are reported alongside, labelled separately [P].
- Per run:
  - **Drops observable:** the fraction of ground-truth drops (X, s, p) with at least one MATCH or SILENT opportunity at any observer, split O = U / O ≠ U [F §9.1].
  - **Active-malicious nodes,** each classified [F §9.2] as one of:
    - **unobservable:** zero MATCH or SILENT opportunities at any observer [P];
    - **observable but insufficient:** no pair with n ≥ 14 [F C-d §9];
    - **judged,** and then **detected** if at least one of its judged pairs is flagged [P], otherwise **missed**.
  - **Inactive-malicious nodes:** listed [F §7].
  - **Honest nodes:** the fraction judged, i.e. with at least one judged pair [F §9.3].
  - **Coverage** = TDR × the share of active-malicious (seed, X) nodes that are judged, labelled "system coverage" [F formula §9; P denominator].
- Only "judged and missed" counts as an algorithm false negative. Unobservable and insufficient cases are evidence limits [F §9].

### E2-11 Inputs and outputs

**Inputs, all read-only:**
- `e1/observer.py`, `e1/geom.py`, `e1/truth.py`;
- `e1/e1_calibration_rev4.json`;
- helpers imported from the existing calibration scripts, unchanged.

**Outputs:**
- **Raw runs, outside the repository:**
  - `~/uwsn-runs/stageE/E2/p075/run_N/`;
  - `~/uwsn-runs/stageE/E2/p100/run_N/`.

  Each holds `v1_N.*`, `stderr.log`, `stdout.log` and `e1_opportunities.csv`.
- **Analysis:** a new `analysis/stageE/e2/e2_evaluate.py`, written only after this specification is committed.
  - It refuses to overwrite existing outputs.
  - It writes `analysis/stageE/e2/e2_results.json` and `e2_report.txt`.
  - The JSON records the md5 of every input file, the code hashes (parent and submodule commits, library, binary, scripts) and the md5 of the frozen calibration JSON.
- **Log:** results are recorded as a new `../../EXPERIMENT_LOG.md` entry after review.

### E2-12 Reproducibility

- **Simulations:** determined by `--run` and the pinned streams. All 20 runs are re-simulated into `~/uwsn-runs/stageE/E2_repeat/`. Required:
  - identical `_energy`, `_mobility`, `_trust`, `_observed` and `_meta` CSVs, `stdout.log` and `stderr.log`;
  - traces identical after masking the uninitialised VBHeader `token`, `ts` and `range` [F D-16; `rxhdr_validation/cmp_masked.py`];
  - identical `e1_opportunities.csv`.
- **Analysis:** a second evaluation run gives an identical `e2_results.json` apart from its creation timestamp.
- **Ordering:**
  - pairs sorted by (seed, O, X);
  - seeds ascending;
  - one generator for the bootstrap (E2-8).
- Output hashes cannot be known in advance; they are recorded in `e2_results.json` and the log entry.

### E2-13 Pre-execution checks (all must pass before the first E2 run)

1. HEAD contains the commit of this specification and D-20.
2. `README.md` is identical to `8a0ff2f`.
3. `CD_EVALUATION_FRAMEWORK.md` and D-19 are unchanged.
4. Every E1 artefact (revisions 2, 3 and 4, including `e1_calibration_rev4.json` `0ca88a0e…`) matches its committed md5.
5. The submodule is clean at `41c67c3`; library and binary md5s are as in E2-2.
6. `~/uwsn-runs/stageE` contains only `E1`. No data exist for seeds 2–11, 22–31 or 41–50.
7. `EAQTE_XI` and `RX_RANGE_M` are unset.
8. Nothing is staged.
   - The pre-existing churn is never added: `build/`, `cmake-cache/`, `.lock-ns3_linux_build`, `trustq_1_*`, `trustq_1.tr`, `vbf-smoke.*` and `energy-HH-VBF-smoke.csv`.
   - Any commit uses explicit paths only.

### E2-14 Gate handling

- **G2 and G2b both pass:** stop and report [F §11]. E3 (clean seeds 12–21) starts only with approval [P].
- **G2 fails:**
  - Frozen conclusion [F §12]: "With overhearing-only evidence in beaconless HH-VBF, the attacker is not observable often enough to evaluate trust."
  - One extension to further held-out seeds is allowed, with a seed allocation approved at that time [F]. The extension re-evaluates the union of seeds 2–11 and the new seeds with the identical procedure, without re-simulating 2–11 [P].
  - If the extension also fails → Option C discussion [F].
  - E3 is on hold meanwhile [P].
- **G2b-FA fails, or G2b fails while interpretable:**
  - Frozen conclusion [F §12]: "Oracle-free overhearing evidence does not separate droppers from honest nodes at the declared false-alarm rate."
  - The roadmap stops, and the Option C discussion follows. E3–E5 do not run.
- **E4 requires G1′, G2, G2b, G3 and G4** [F C-d §10]. The order E2 → E3 → E4 → E5 is unchanged [F].

## 3. Source note: C-d §4.1 multiplicity wording (outside E2's scope; nothing changed)

Frozen C-d §4.1 draws node positions "for each drawn seed position" but defines multiplicity as "(count of its seed) × (count of X within that seed)". That is internally inconsistent whenever a seed is drawn more than once (the E2-8 example).

E2 does not use C-d §4.1. Before E4, a separately approved clarification of C-d is required. Presumably it would be the same occurrence-sum rule, but it is not decided here.

## 4. Direction of the proposed interpretations

Recorded so that the effect of each [P] choice on passing is transparent.

**Stricter for passing:**
- the observed node universe rather than the fixed 99 addresses (fewer empty clusters, a narrower FA interval);
- two-sided AUC and TDR lower bounds and FA upper bound;
- "FA upper bound" read as E2's upper confidence bound rather than 0.05;
- least-favourable values for zero-denominator replicates.

**More lenient:**
- (seed, X) node counting, which counts more nodes than counting by address alone;
- inactive-malicious pairs excluded from AUC, since counting them as positives would lower AUC;
- a lower bound exactly equal to 0.05 counting as a pass;
- G2b detection reported as "not interpretable" when G2 fails, rather than as a failure that stops the roadmap.

**Neutral or procedural:**
- the node is X;
- B = 10,000 and PCG64(12345);
- linear percentiles;
- ties counted as ½;
- the opportunity file name;
- the p = 0.75 ceiling table;
- the ceiling definitions;
- holding E3;
- the union rule for the extension.

## 5. Revision log

| Date | Revision |
|---|---|
| 2026-10-05 | E2 specification approved: E2-1 to E2-14 with the classification audit; corrected occurrence-specific hierarchical bootstrap (multiplicity = sum of X counts across repeated occurrences of a seed) with worked example; C-d §4.1 wording noted for clarification before E4. Frozen when committed (D-20). E2 not run; seeds 2–11 unopened |
