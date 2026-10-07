# Stage F final-evidence record

**FINAL EVIDENCE: documentation-only promotion (decision D-27).** Recorded 2026-10-07.

- **Nothing re-run:** no experiment, simulation, analysis or computation was re-run or newly performed to produce this
  record.
- **Nothing modified:** no source code, trace, result, specification or development artifact was modified.
- **What this file is:** the committed final-evidence layer for selected Stage F findings. It points, by exact path
  and md5, to development artifacts that stay byte-identical outside the repository (§B, §K).
- **Status of the underlying artifacts:** they keep their banner "DEVELOPMENT-ONLY / FEASIBILITY ANALYSIS — NOT FINAL
  EVIDENCE". This record does not relabel, edit or replace them.

**Gate scope:**
- Every statement concerns the **EAQTE-style environment gate as implemented** in `AquaSimTrustQVBF`.
- The EAQTE paper is not available on the machine where this work was done. No parameter here is attributed to it.
- **Implementation values:** Eb/N0 = 40 dB (hard-coded), f = 25 kHz, k = 1.5, m = 640 bits.
- **Project choices:** R = 1,000 m, VelocityScale 0.3 m/s, reversal window 1.5 s.
- **Gate rule as implemented:** EE = 0.5·CCQ + 0.5·SS, freeze if EE < ξ = 0.3 (implementation default; `EAQTE_XI`
  unset).

No novelty, "first" or state-of-the-art claim is made here. The literature review is a separate pending task.

---

## A. Purpose and evidence-status policy

**Purpose:** make the reviewed Stage F findings citable in the thesis and the project record, at exactly the strength
their underlying artifacts support.

**Status labels** (each promoted claim gets one):

| Label | Meaning |
|---|---|
| **DEMONSTRATED** | Directly established by an executed, audited and reproducible procedure, or by audited source-code control/data flow. Data procedures need a frozen specification, integrity guards and an independent reproduction of the outputs |
| **CONDITIONAL** | Follows from audited code or derivation, but depends on an explicit implementation or configuration condition, stated with the claim |
| **INCONCLUSIVE** | An executed study or audit did not resolve the hypothesis |
| **DESCRIPTIVE** | An observed result, with no formal causal or security claim |

**Rules:**
- "PROVEN IMPOSSIBLE" is not used anywhere.
- No claim may be paraphrased more strongly than its artifact. Where a short form is needed, the "Allowed thesis
  wording" column of §H is authoritative.

## B. Immutable provenance rule

**Location.** The development artifacts live under `/home/aswinlaks/uwsn-runs/stageF_dev/`, outside the repository,
like the E2 raw data (E-35).
- They are cited by absolute path and md5 in §K.
- They are listed in the machine-checkable manifest `analysis/STAGE_F_FINAL_EVIDENCE.md5`; check with
  `md5sum -c analysis/STAGE_F_FINAL_EVIDENCE.md5`.

**Preservation.**
- The artifacts must stay byte-identical, with their development-only banners.
- A mismatch means the cited evidence is no longer the evidence promoted here. The claim must then be treated as
  unsupported until the discrepancy is resolved in a new, separately approved record.

**Source files.** The repository source files cited for code-derived claims are listed with their md5 at promotion
time. A later code change does not alter what was audited.

**Data origin.** The C1 and K1 analyses read existing traces only:
- E1 seeds 12–21;
- E2 p = 0.75 / p = 1.0 seeds 2–11 (the E2 held-out seeds, already used by E2);
- F-0d clean development runs on seeds 2–11.

K2 ran 24 new development simulations on seeds 33–40, subject to the provenance limitation in §E.

## C. K1 final evidence

**Sources:** `K1_REACHABILITY_RECORD_DEVELOPMENT_ONLY.md` (`dceb4e24…`); `results/K1_reachability/k1.json`
(`835a429e…`); code `k1_reachability.py` (`ae6490ce…`); audit §C (`33e3261e…`).

**C.1 — DESCRIPTIVE.**
> "Under the project's main 40 dB / 1000 m configuration, the EAQTE-style environmental freeze condition was not
> reached in the examined traces."
- **Gate evaluations examined:** 271,903 (direct 202,023; blame 34,940; backup 34,940).
- **Data:** 40 main-configuration runs: E1 seeds 12–21, E2 p = 1.0 and p = 0.75 seeds 2–11, F-0d seeds 2–11.
- **Results:**
  - 0 evaluations reached the freeze-required distance;
  - 0 `[EAQTE-FREEZE]` lines (0 freeze events);
  - minimum EE 0.470181;
  - maximum gate distance 1,006.37 m.
- **Run integrity:** md5-verified inputs, strace (0 truth.py opens), and K1's pre-declared method-validity
  criterion (0 violations).
- **Why DESCRIPTIVE:** no independent reproduction run was made.

**C.2 — DEMONSTRATED (code-audited).** A freeze requires a gate distance greater than d* = 1,478.9508 m. The steps:
- freeze ⇒ CCQ < 0.6;
- CCQ ≥ 0.7551·p(d) (population variance of values in [0, 1] is ≤ ¼);
- p(d) is strictly decreasing in d;
- d* is the inverse at 40 dB.

**C.3 — CONDITIONAL.**
> "Under the current implementation and configuration, a freeze is impossible unless a single packet remains in the
> broadcast-MAC backoff loop for at least about 1,527 s on the blame path or 1,595 s on the credit paths."
- **Why CONDITIONAL:** the code imposes no finite upper bound on that MAC residence time T_mac (§F). The audit
  result for the absolute claim is **B — NOT PROVEN**.

**Not promoted:** "the gate is impossible under the current configuration" is not promoted, in any unconditional
form.

## D. C1 final evidence

**Sources:** closure `C1_CLOSURE_RECORD_DEVELOPMENT_ONLY.md` (`2f753b97…`); frozen spec (`6c53952f…`); Amendment A1
(`a4aefcd5…`); code `c1_measure.py` (`b8c86fea…`); outputs (§K).
- An independent verify run (`results/C1_verify/`) reproduced all three output hashes exactly.

**D.1 — DEMONSTRATED.**
> "In the existing E2 traces, the reversal coupled to the blamed drop itself does not reach a freeze-relevant SS
> input before the corresponding gate evaluation."

**D.2 — DEMONSTRATED.**

| Dataset | Blame-of-drop units | N2-REACH | N2-FEASIBLE |
|---|---|---|---|
| p = 0.75 | 1,951 | 0 | 0 |
| p = 1.0 | 432 | 0 | 0 |

**D.3 — DEMONSTRATED. Gates:**
- **Parity PASS:** 8,921 / 8,921 (p = 0.75) and 6,880 / 6,880 (p = 1.0) BLAME lines reproduce the logged SS and age.
- **Ordering PASS:** 11,655 / 11,655 and 3,881 / 3,881 same-copy rows have t_d ≥ t0.
- **Amendment A1 epoch matching:** 2,069 + 510 unique; 0 missing; 0 non-unique.

**D.4 — Frozen outcome: C1 final status = CLOSE C1** (N2-FEASIBLE = 0 in both datasets).

**D.5 — DESCRIPTIVE (additional exposure limitation; not the reason for closure).**
- **p = 0.75, seed 2:** active attackers, but no attacker with a blame-of-drop event, so M-N3 fails.
- **p = 0.75:** 46 / 200 configured attackers were active; 22 / 200 had ≥ 1 blame-of-drop.
- **p = 1.0:** 42 / 200 were active; 3 / 200 had ≥ 1 blame-of-drop.

**D.6 — DESCRIPTIVE: SECONDARY / OUTSIDE THE FROZEN DECISION RULE.**

| Dataset | Cumulative N2-FEASIBLE events | Attackers |
|---|---|---|
| p = 0.75 | 79 | 7 |
| p = 1.0 | 37 | 2 |

- **Method:** first-order counterfactual; receptions held fixed; not simulated.
- **Not** evidence of successful evasion.
- Does not change CLOSE C1, and does not reopen C1.

**Procedural note.** Attempt 1 completed all gates and calculations, then failed while writing the CSV header (a
list + tuple type error).
- Its `c1_results.json` is identical to attempt 2's except for the `code_md5` field.
- This was a procedural execution issue, not a change to any result.

## E. K2 final evidence

**Sources:** closure `K2_CLOSURE_RECORD_DEVELOPMENT_ONLY.md` (`5b3c0328…`); spec rev 3 (`f37b71bd…`); run manifest
`K2_RUNS.md5` (`60dbca6b…`, 241 entries).

**E.1 — INCONCLUSIVE.**
- **Reason:** seed 36 had **no attacker drop decision in either A1 or A2**.
- So the frozen primary comparison was undefined for that seed, and the experiment stopped before any metric was
  computed.

**E.2 — DESCRIPTIVE** (read-only diagnostic after the stop): 0–9 of 20 configured attackers per seed became active.

**Provenance limitation (permanent):**
> "Seeds 33–40 are the best available Stage-F-unused allocation, but their historical global non-use cannot be proven
> because the earlier 40-seed batch is unavailable."
- Seed 32 was excluded and not used.

**Must not be read as:** attack disproven; attack impossible; masking ineffective.

## F. K1 / C1 code-audit evidence

**Source:** `C1_K1_CODE_AUDIT_RECORD_DEVELOPMENT_ONLY.md` (`33e3261e…`); source md5s in §K.

**F.1 — DEMONSTRATED (code-audited). Gate position path.**
- **Single source of position:** the gate's stored information about node X is written only at
  `aqua-sim-routing-trustq-vbf.cc` l.821 / l.970.
  - These writes are keyed by the decoded transmitter.
  - pos = header `f` = the transmitter's own position, set in `MACprepare` (`aqua-sim-routing-vbf.cc` l.741, l.759),
    quantized to the millimetre.
  - No entry is ever erased.
- **Watch targets:** taken only from that table.
- **Freeze-relevant gate calls:** l.867 (direct credit), l.903 (blame), l.905 (backup credit).

**F.2 — DEMONSTRATED (code-audited). Timing and motion bounds.**
- Blame-path entry age is ≤ 68 s: the 60 s stale filter (l.440, constant l.184) plus the 8 s watch (l.675, l.701).
- MCM moves a node ≤ 0.3 m per whole-second update.
- Range propagation delivers only within 1,000 m at transmission time.

**F.3 — CONDITIONAL. Distance bound.**
- Gate distance ≤ 1,020.700866 + 0.3·(⌊T_mac⌋ + 1) m (blame), or 1,000.300866 + 0.3·(⌊T_mac⌋ + 1) m (credit).
- This assumes air delay < 1 s and the default attributes, as listed in audit §J.

**F.4 — INCONCLUSIVE. Absolute impossibility: audit result B — NOT PROVEN.**
- T_mac has no finite enforced upper bound. The broadcast MAC shares one resettable backoff counter per node, and
  PktTable eviction (`WINDOW_SIZE` = 19, global packet UIDs) removes the forward-once guarantee.
- **Not done:** the loophole is not closed by assumption.

## G. Observability / evidence limitations

These rest on the committed Stage A–E record plus the code reading below. They are not universal impossibility
claims; each is scoped to the implementation and the examined data.

**G.1 — DEMONSTRATED (committed, held-out). Passive attribution not demonstrated reliable** (E-35, D-21; OC-1
`a82851c5…`). The E2 frozen conclusion:
> "Oracle-free overhearing evidence does not separate droppers from honest nodes at the declared false-alarm rate."
- AUC 0.9055 (2.5th percentile 0.8464).
- TDR 0.343 at FA 0.0528 (73 / 1,383); G2b failed.
- E1 (E-32 to E-34): G1 failed because honest silence is pair-persistent and over-dispersed.

**G.2 — DESCRIPTIVE (committed). Observability ceiling** (E-35; OC-1 §6).
- p = 1.0: 14.2 % of drops are observable; 34 / 42 active malicious (seed, X) are never observable.
- p = 0.75: 64.0 % of drops are observable.

**G.3 — DEMONSTRATED (code-audited). Some malicious behaviour is invisible to passive peers by construction.**
- A node that never transmits has no neighbour entry at any observer (F.1).
- So it is never watched, never gate-evaluated and never the subject of an observer-trust update. Every
  `UpdateObservedTrust` call (l.862, 876, 897, 898, 913, 921) is a credit or blame of a decoded transmitter or a
  watched table entry.

**G.4 — DESCRIPTIVE (committed; development diagnostic, seed 1). Silence is confounded by legitimate HH-VBF
forwarding** (E-29; `analysis/stageD_tables.txt`).
- At p = 0.75, only 209 of 3,679 valid silent opportunities (5.7 %) were drops.
- The rest were legitimate:
  - the candidate never decoded the copy: 37 %;
  - it acted on a different upstream copy: 32 %;
  - it forwarded but the observer did not hear it: 20 %;
  - plus ineligibility and suppression.

**G.5 — DEMONSTRATED (code reading). PACT cannot supply missing evidence, as implemented.**
- PACT rescales observer-trust updates that already occur: credit or blame events inside the custody-gated duplicate
  branch (l.860–862, l.893–898), with a weight in [0, 1].
- A watch timeout, i.e. a silent drop, produces no observer-trust update in either the gate or the PACT arm
  (`CheckWatchTimeout`, l.680–702).
- So PACT creates no evidence about unobserved behaviour.
- **Scope:** PACT's empirical effect in the rebaselined network was **never evaluated**: E3 to E5 were not run, and
  OC-2 stopped. The pre-rebaseline PACT pilot (handoff §6.5) is HISTORICAL and is not cited as final evidence.

## H. Evidence-status table

| # | Claim | Status | Underlying artifact | Exact hash | Scope | Allowed thesis wording |
|---|---|---|---|---|---|---|
| 1 | Freeze condition not reached; 271,903 evaluations; 0 reached d*; 0 freezes | DESCRIPTIVE | K1 record; `k1.json` | `dceb4e24cd760dd28ed584f0e24b9965`; `835a429edd15fabf5985827c20d2a271` | 40 dB / 1,000 m / ξ 0.3; 40 runs (E1 12–21, E2 p075 / p100 2–11, F-0d 2–11) | "Under the project's main 40 dB / 1000 m configuration, the EAQTE-style environmental freeze condition was not reached in the examined traces (271,903 gate evaluations; 0 reached the analytically derived freeze threshold; 0 freeze events)." |
| 2 | Freeze ⇒ gate distance > 1,478.9508 m | DEMONSTRATED (code-audited) | audit §C; K1 record | `33e3261e68135b579945f5d0dd18399d`; `dceb4e24…` | implementation at 40 dB, ξ 0.3 | "In the implementation, a freeze requires a gate distance greater than 1,478.95 m." |
| 3 | Freeze impossible unless T_mac ≥ ≈ 1,527 s (blame) / 1,595 s (credit) | **CONDITIONAL** | audit §G–I | `33e3261e…` | current implementation and configuration; air delay < 1 s; default attributes | the C.3 statement, verbatim, with "conditional on MAC residence time; the code does not bound it" |
| 4 | Absolute impossibility of the freeze | **INCONCLUSIVE (audit B — NOT PROVEN)** | audit §I | `33e3261e…` | — | "A code-only proof of absolute impossibility was not obtained." |
| 5 | Same-drop reversal does not reach a freeze-relevant SS input before the gate evaluation | DEMONSTRATED | C1 closure; `c1_results.json` (measure = verify) | `2f753b979b07d661dc4b2a25c0e822d3`; `20821d4dc40c638448fbac660a6aa524` | existing E2 traces, p = 0.75 / 1.0, seeds 2–11; primary same-drop counterfactual | D.1, verbatim |
| 6 | p = 0.75: 1,951 units, REACH 0, FEASIBLE 0; p = 1.0: 432, 0, 0 | DEMONSTRATED | same | same | same | "1,951 (p = 0.75) and 432 (p = 1.0) blame-of-drop units; REACH = 0 and FEASIBLE = 0 in both." |
| 7 | Parity PASS; ordering PASS; C1 = CLOSE C1 | DEMONSTRATED | C1 closure; C1 manifest | `2f753b97…`; `8d611738841d04a4ff1a188aa9a9f42d` | same | "Both validity gates passed; under the frozen decision rule, C1 closed as CLOSE C1." |
| 8 | Exposure: seed 2 (p = 0.75) active attackers but no blame-of-drop; 46 / 200 active, 22 / 200 with blame-of-drop | DESCRIPTIVE | C1 closure §5; `c1_n3_nodes.csv` | `2f753b97…`; `36c81158b9a7fad8a6038de2173b92d8` | same | "Attacker exposure was sparse; at p = 0.75, seed 2 had active attackers but none with a blame-of-drop event." |
| 9 | Cumulative variant: 79 FEASIBLE on 7 attackers (p = 0.75); 37 on 2 (p = 1.0) | DESCRIPTIVE — **SECONDARY / OUTSIDE THE FROZEN DECISION RULE** | C1 closure §7; `c1_n2_events.csv` | `2f753b97…`; `d5e2c067305d3cad0237a26388758516` | first-order counterfactual, not simulated | "The cumulative secondary analysis indicates that motion changes associated with earlier attacker drops can reach the reconstructed stability input in some later blame events. This observation is outside the primary C1 decision rule and does not establish successful environment-masked evasion." |
| 10 | K2 = INCONCLUSIVE (seed 36: no attacker drop in A1 or A2; primary comparison undefined; stopped before any metric) | INCONCLUSIVE | K2 closure; `K2_RUNS.md5` | `5b3c03283a92f9018fd8b9216b3a59df`; `60dbca6b0e23116e6337d390b56ce2d0` | seeds 33–40 (provenance limitation), arms A0 / A1 / A2 | the K2 closure statement, verbatim (§E.1) |
| 11 | Gate's information about X comes only from X's own decoded transmissions; watch targets only from that table | DEMONSTRATED (code-audited) | audit §C–D; source | `33e3261e…`; `953629a5e75c1bc7ae5352ba0fb015cd` | implementation as audited | "In the implementation, an observer's gate inputs about a node come only from that node's own decoded transmissions." |
| 12 | Blame-path entry age ≤ 68 s; node step ≤ 0.3 m/s; delivery ≤ 1,000 m | DEMONSTRATED (code-audited) | audit §D–F | `33e3261e…` | current configuration, default attributes | as stated, with scope |
| 13 | Passive oracle-free attribution not demonstrated reliable (E2 frozen conclusion) | DEMONSTRATED (committed, held-out) | E-35; OC-1 | `a82851c5b39bf96da21076a29c876ef4` (OC-1) | seeds 2–11, p = 0.75, Arm A | the E2 frozen conclusion, verbatim, with its AUC |
| 14 | Observability ceiling (p = 1.0: 14.2 % observable; 34 / 42 never observable) | DESCRIPTIVE (committed) | E-35; OC-1 §6 | `a82851c5…` | same | "At p = 1.0, 34 of 42 active malicious nodes were never observable." |
| 15 | A never-transmitting node is never watched, gate-evaluated or trust-updated by passive observers | DEMONSTRATED (code-audited / code reading) | audit §C–D; source l.862–921 | `33e3261e…`; `953629a5…` | implementation as audited | "In the implementation, a node that never transmits is never evaluated by passive observers." |
| 16 | Silence confounded by legitimate forwarding (5.7 % of valid silent opportunities were drops) | DESCRIPTIVE (committed; seed-1 diagnostic) | E-29; `analysis/stageD_tables.txt` | `755135767d9df5c08c02e802d1c4e76f` | seed 1, p = 0.75, development diagnostic | "In a development diagnostic, most silent opportunities were explained by legitimate HH-VBF behaviour (only 5.7 % were drops)." |
| 17 | PACT only rescales existing custody-gated evidence; a silent-drop timeout produces no update | DEMONSTRATED (code reading) | source l.860–898, l.680–702 | `953629a5…` | implementation; PACT's empirical effect never evaluated after rebaseline | "As implemented, PACT reweights existing evidence events and cannot supply evidence about unobserved behaviour; its empirical effect in the corrected network was not evaluated." |
| 18 | In-range freeze analytically reachable only below ≈ 34.53 dB | CONDITIONAL (closed-form; network behaviour untested) | `analysis/stageE/eaqte_operating_point/ee_bound_output.txt` (already committed) | `8fda74d7b82248bb5875ec2fef7213c6` | at d = 1,000 m, worst case | "For in-range links, the freeze condition is analytically reachable only below about 34.5 dB; network behaviour there was not evaluated." |

## I. Claims permitted for thesis use

Only the "Allowed thesis wording" of §H, with its scope.

**Summary claim** (assembled strictly from rows 1, 3, 5, 8, 11 and 15; its parts are DESCRIPTIVE, CONDITIONAL and
DEMONSTRATED as labelled there):

> "The environment-masked-evasion threat remains unproven under the current implementation. In the examined traces
> the freeze condition was not reached; the code admits a freeze only under an extreme MAC-residence condition; the
> reversal coupled to the blamed drop did not reach the freeze-relevant stability input; a never-transmitting
> attacker is never evaluated; and attacker exposure was sparse."

## J. Claims prohibited

- That the attack exists, works or was demonstrated. That it is impossible, in general or under any configuration.
- Calling the gate impossible to trigger under the current configuration, or closing the T_mac loophole by
  assumption. Using "PROVEN IMPOSSIBLE".
- Treating the cumulative variant as primary, or as evidence of evasion.
- Reading K2 as attack disproven, attack impossible or masking ineffective.
- That EAQTE is secure, unreliable or ineffective in general. Anything about the EAQTE paper's parameters or results.
  "We reproduced the EAQTE paper."
- That observer trust is impossible in general. That PACT is useless. That PACT was shown empirically not to work in
  the corrected network (it was not evaluated there).
- Any routing degradation, routing resilience, detection, attribution or mitigation improvement.
- Any novelty, "first" or state-of-the-art claim (literature review pending).
- That seeds 33–40 are proven globally unused.
- Generalisation beyond the stated scopes: other UASNs, other HH-VBF configurations, other Eb/N0, MAC, propagation or
  mobility models.

**Not promoted by this record** (they remain development-only and are not citable as final evidence unless separately
promoted):
- F-0 / F-1 / F-2, F-3, NCSR, RF-A;
- the post-K2, post-C1 and final-thesis-contribution reviews.

## K. Exact source-artifact paths and hashes

**Manifest:** `analysis/STAGE_F_FINAL_EVIDENCE.md5`, 51 entries, md5sum format, absolute paths. It verified 51 / 51
at promotion.

| Group | Files |
|---|---|
| K1 | `K1_REACHABILITY_RECORD_DEVELOPMENT_ONLY.md` `dceb4e24cd760dd28ed584f0e24b9965`; `code/k1_reachability.py` `ae6490cee387e9f09550b9e50b21fcd5`; `results/K1_reachability/k1.json` `835a429edd15fabf5985827c20d2a271`; `results/K1_reachability/k1.txt` `3ab176b5761149682189a2346fd7b494`; `results/K1_guards/k1_run2.strace` `f8056d893e2cc463d57fca216f0994ae`; `results/K1_guards/k1_run2.stdout` `3ab176b5…`; `results/K1_guards/k1_reachability_run2.py.md5` `4d13dd34114907f6ed7e8e5c33749069`; `INPUTS.md5` `82ee3cd628acff4a7113d63533b34f0d`; `OUTPUTS.md5` `4241b7074352b615dedc1d852c25f4a4` |
| C1 | `C1_GATE_P1_FEASIBILITY_RECORD_DEVELOPMENT_ONLY.md` `d23d77688bb164d2c5d65ace29103d68`; `C1_N2_N3_MEASUREMENT_SPEC_DEVELOPMENT_ONLY.md` `6c53952f3044fe852a290806dfb137ad`; `C1_AMENDMENT_A1_DEVELOPMENT_ONLY.md` `a4aefcd5578320176745f759efacdde5`; `C1_CLOSURE_RECORD_DEVELOPMENT_ONLY.md` `2f753b979b07d661dc4b2a25c0e822d3`; `code/c1_measure.py` `b8c86fea4de5ec06dbea338322244b63`; `results/C1_measure/` and `results/C1_verify/` `c1_results.json` `20821d4dc40c638448fbac660a6aa524`, `c1_n2_events.csv` `d5e2c067305d3cad0237a26388758516`, `c1_n3_nodes.csv` `36c81158b9a7fad8a6038de2173b92d8`; `results/C1_manifest/C1_OUTPUTS.md5` `8d611738841d04a4ff1a188aa9a9f42d`; `results/C1_report/C1_MEASUREMENT_REPORT_DEVELOPMENT_ONLY.md` `ca342a1e16a0f71f582c12e3360b8b8e`; `results/C1_guards/C1_PRE_EXECUTION.md5` `145a03a3c6466e1e5ca87c062862794a`; `C1_PRE_EXECUTION_ATTEMPT2.md5` `2e4b8cd4ecd8bdb6fa710363d2d8b8a2`; `ATTEMPT1_NOTE.txt` `c6de67705dc6fde3751134419238485d`; `strace_measure.log` `f52a6c5b3f58a259b4ff83b8fc97c789`; `strace_verify.log` `78328faa5251b9045c36394422f9fdee`; `results/C1_measure_attempt1_crash/c1_results.json` `7ae1b30b450cec0f6077e65187e2471a` |
| K2 | `K2_ENVIRONMENT_MASKING_SPEC_DEVELOPMENT_ONLY.md` `f37b71bd09b5363edf50684ef4eedca0`; `K2_CLOSURE_RECORD_DEVELOPMENT_ONLY.md` `5b3c03283a92f9018fd8b9216b3a59df`; `code/k2_sims.sh` `0556798403170aa31714735965b15da4`; `code/k2_common.py` `96c4efc146a9c29b9bd4acc5880fcb7f`; `code/k2_precheck.py` `5b6541a18a7ef32916ec397c5d18ac8d`; `results/K2_guards/K2_RUNS.md5` `60dbca6b0e23116e6337d390b56ce2d0`; `k2_precheck_code.md5` `f70d673a48b433f270436e5ed6b3be06`; `k2_precheck.stdout` `d41d8cd98f00b204e9800998ecf8427e` (empty); `k2_precheck.stderr` `f9eb8e14c4745575c6700a808cfb39a6` |
| Audit | `C1_K1_CODE_AUDIT_RECORD_DEVELOPMENT_ONLY.md` `33e3261e68135b579945f5d0dd18399d` |
| Source (repository, at promotion) | `aqua-sim-routing-trustq-vbf.cc` `953629a5e75c1bc7ae5352ba0fb015cd`; `.h` `08f66365ba28df29e47705784743fdba`; `aqua-sim-routing-vbf.cc` `71180aa73dd32809404dde5f86ad7dbb`; `aqua-sim-header-routing.cc` `504d43eade5ac14e328c17a5542f6704`; `aqua-sim-range-propagation.cc` `32248cf7bb7a595bc93880a57f85254a`; `aqua-sim-phy-cmn.cc` `a14306fbcf59312171525ea149bed583`; `aqua-sim-mac-broadcast.cc` `58d8770bf7fb39ca68bd53a1f88de0ab`; `aqua-sim-mac.cc` `f1669f809abe5c5ecd20affb0853a4ba`; `aqua-sim-modulation.cc` `0a54293e60b7e1db70b6e03d7b2bcfef`; `aqua-sim-datastructure.h` `c27265e2bfe83be4f848a42d7416a4ba`; `aqua-sim-channel.cc` `95cb8bc890e3dfd7f405389fdb9c17dc`; `scratch/mcm-mobility-model.h` `77d2da1375e51975da2679fed2573b92`; `scratch/uwsn-trustq-attack.cc` `aeb769cfd7ce0b69d374681187a245d9` |
| Committed, cited (not in the manifest) | `analysis/stageE/OC1_SYNTHESIS.md` `a82851c5b39bf96da21076a29c876ef4`; `analysis/stageD_tables.txt` `755135767d9df5c08c02e802d1c4e76f`; `analysis/stageE/eaqte_operating_point/ee_bound_output.txt` `8fda74d7b82248bb5875ec2fef7213c6`; E-29, E-32 to E-35 in `EXPERIMENT_LOG.md` |

Development paths are relative to `/home/aswinlaks/uwsn-runs/stageF_dev/`. Source paths are relative to
`src/aqua-sim-ng/model/` unless they start with `scratch/`.

## L. Repository / provenance integrity (at promotion)

- **Repository:** HEAD `894f3dc`, submodule `db72cab` (clean). Status and index were identical to the pre-Stage-F
  snapshot before this documentation was added.
- **Artifacts:** all 51 manifest entries verified; development `INPUTS.md5` verified; C1 output manifest verified.
- **Files changed by this promotion:**
  - new: this file and `analysis/STAGE_F_FINAL_EVIDENCE.md5`;
  - narrowly scoped status entries in `PROJECT_HANDOFF.md`, `EXPERIMENT_LOG.md` (E-37) and
    `RESEARCH_DECISIONS.md` (D-27).
- **Not modified:** any source file, trace, result, specification or development artifact.
- **Not created:** no `analysis/stageF/` directory.
