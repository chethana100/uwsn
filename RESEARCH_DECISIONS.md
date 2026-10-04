# Research Decisions

Each decision gives its ID, date, the decision, the reason, and its status.
For every routing item, the source layer is stated: **[HH-VBF paper]**, **[Aqua-Sim-NG]**, **[project]**, or **[contribution]**.

## Scope

| ID | Date | Decision | Why | Status |
|---|---|---|---|---|
| S-01 | earlier chats | **No Q-learning routing.** Q-learning is not part of the routing contribution. | Scope; "TrustQ" is only a class name. | In force |
| S-02 | earlier chats | **Wormhole attack out of scope** unless explicitly approved. | Scope | In force |
| S-03 | earlier chats | **No reimplementation of TUMRL/ARTMM/TMC** at a different scale. Comparison is against this project's own prior methods, with held-out seeds and pre-registered bars. | Unreasonable scope (paper evaluates 500 nodes, 100 m range) | In force |
| S-04 | earlier chats | **EAQTE gate** = the paper's environmental freeze, implemented as a baseline mechanism. The paper's energy/data evidence and Q-learning are not implemented. | Base-paper alignment | In force |
| S-05 | earlier chats | **Flow-level detector** is a separate mechanism, never called EAQTE. | Naming confusion | In force |
| S-06 | earlier chats | **Observer trust must be resolved before the final PACT evaluation.** | PACT reweights observer evidence; the evidence is currently invalid | In force |
| S-07 | earlier chats | **PACT** = Peer-referenced Attenuated Continuous Trust (`--pactEnabled`; default off reproduces the published freeze). | Definition | In force; no PACT changes until approved |
| S-08 | 2026-10-02 | Preserve valid negative findings. Do not optimize for positive results. Do not change the problem statement or novelty framing without discussing the evidence. | Research integrity | In force |

## Baseline and routing

| ID | Date | Decision | Source layer | Status |
|---|---|---|---|---|
| D-01 | 2026-10-02 | **Reception range enforced at the channel** with `AquaSimRangePropagation`, consistently in every experimental arm. All earlier PDR/detector numbers are pre-rebaseline diagnostics. | [HH-VBF paper]: Lemma 2 assumes nodes beyond R cannot hear; α ∈ [0,3] presumes d ≤ R. [Aqua-Sim-NG] provides the model; MDTBOR (Sun et al. 2026) uses the same configuration. | **Done (Stage B, 2026-10-03):** all 5 scenarios; `--propagation=simple` kept in the main scenario only to reproduce pre-rebaseline runs. B1–B4 and V1 (range) pass (E-17..E-20). |
| D-01a | 2026-10-03 | **`RX_RANGE_M` not used in final experiments.** The code stays inert (default off); the scenario will refuse to run if it is set together with range propagation. | [project] | Approved |
| D-02 | 2026-10-02/03 | **Hold time = T = √α · T_delay + (R − d)/v₀**, the VBF formulation the HH-VBF paper says HH-VBF uses. The mapping to code must be verified before patching. Legacy `+2(d−R)/v` is kept only behind `PaperHoldTime=false` to reproduce old diagnostics. | Formula: [VBF 2006, not in the attached set; HH-VBF paper defers to it]. Legacy form: [Aqua-Sim-NG base VBF line 625–628]. | **Done (Stage C, 2026-10-03).** Mapping: T_delay = `DELAY` = 1.0 s [Aqua-Sim-NG value; not in the paper]; R = `GetTransRange()` = 1000 m; d = `Distance(pkt)` = |node − stamped f|; v₀ = `SOUND_SPEED_IN_WATER` = 1500. V2 exact (E-25). |
| D-03 | 2026-10-02 | **`baseDelay < 0` clamp** only as a logged defensive guard, never as the primary NaN fix. | [project] | **Done (Stage C).** Implemented as `!(holdAlpha >= 0)` on the value under the square root (α′ by default), so it also catches NaN; logs `[GUARD]`. 0 events under range propagation; 517 under the `simple` control (E-24). Side effect: `simple` + legacy attributes no longer reproduce the NaN → 0.5 s artefact. |
| D-04 | 2026-10-02 | **Opportunity-conditioned observer, Step 1 only:** offline replay/accounting. No trust updates, no q estimation, no PACT changes, no C++ observer changes. Match only responses whose recovered upstream agrees; exclude different-upstream cases. | [contribution] | **Step 1 done (Stage D, 2026-10-03):** ε = 25 m accepted after validation (max recovery error 0.601 m, min separation 136 m). Results in EXPERIMENT_LOG E-28/E-29. No redesign proposed yet, by instruction. |
| D-05 | 2026-10-03 | **HH-VBF baseline = `AquaSimTrustQVBF` with `PriorityScale=0`**, trust/attack features off. Valid only after V1–V3 pass. Base `AquaSimVBF` is not modified. | [project] | Approved, conditional on V1–V3 |
| D-06 | 2026-10-03 | **Desirableness factor = HH-VBF Definition 2: α′ = (R − d·cosθ)/R**, implemented in the TrustQVBF subclass, with no `p/W` term when claiming paper-faithful HH-VBF. The exact current path and the proposed change must be shown before editing. | [HH-VBF paper] Definition 2. The `p/W` term in Aqua-Sim's `CalculateDelay` is [Aqua-Sim-NG], following VBF Definition 1. | **Done (Stage C)** for the **hold time only** (2026-10-03 decision): `PaperDesirableness=true` default; Aqua-Sim α remains available (`=false`) and still drives the self-adaptation thresholds (D-07). V2 exact (E-25). |
| D-07 | 2026-10-03 | **Duplicate suppression: keep the Aqua-Sim self-adaptation rule for now** (min desirableness ≤ 1.5/2^(n−1); a single copy needs ≤ 1.5; a node quits at 10 copies). Documented as an implementation deviation. | [Aqua-Sim-NG]. The HH-VBF paper's β rule (forward if min distance to overheard vectors > β) is not specified well enough in the attached copy to replace it. | Approved (temporary) |
| D-08 | 2026-10-03 | **Seed 32 not used**, because the historical 40-seed batch cannot be confirmed. A2 determinism and V1 use seed/run 1 only, labelled development/diagnostic, not held-out evaluation. | — | Decided |
| D-10 | 2026-10-03 | **Sink fixed at (1500, 1500, 0).** MCM installed only on nodes 1..99; the scenario aborts unless the sink is ConstantPosition. This is a simulation-correctness fix and a pre-rebaseline change; no attempt to keep outputs byte-identical with A1. | [project] scenario bug. The HH-VBF paper's simulations keep the source and sink fixed. EAQTE §3.1 places the sink on the surface (fixedness not stated). | **Done:** A2 (main scenario) and Stage B (`uwsn-trustq-baseline.cc`, both with an abort check) |
| D-11 | 2026-10-03 | **RNG streams pinned per node** (MAC `1000+2i`, routing `1000+2i+1`) so arms with different numbers of RNG objects draw matched MAC randomness. | [project] experimental control | Done in A2 |
| D-12 | 2026-10-03 | **V1 is stated conservatively:** it tests whether TrustQVBF with PriorityScale=0 reproduces base HH-VBF forwarding under matched conditions; it is not a general proof of equivalence. | [project] | In force |
| D-09 | 2026-10-03 | **Execution order A1 → A2 → B → C → D**, stopping after each stage with a verification report. No changes to PACT, EAQTE trust updates, attacker logic or the new observer mechanism yet. | [project] | In force |

## Recorded deviations from the HH-VBF paper (Aqua-Sim-NG implementation details)

These are **not** part of the original HH-VBF specification.

| Item | HH-VBF paper | Aqua-Sim-NG / current code |
|---|---|---|
| Desirableness, hold time | α′ = (R − d cosθ)/R (Def. 2) | **Since Stage C: α′ (matches the paper).** Legacy α available with `PaperDesirableness=false` |
| Desirableness, self-adaptation thresholds | The paper's suppression uses β and "self-adaptation" (combination unspecified) | **Explicit deviation (2026-10-03 decision):** Aqua-Sim-NG α = p/W + (R − d cosθ)/R (VBF Def. 1) still feeds the 1.5 and 1.5/2^(n−1) thresholds in `TimeoutTrustAware`. Hold time and thresholds therefore use *different* desirableness factors. |
| Holding time | "computed the same way as in VBF" (formula not printed) | **Since Stage C: √α′·T_delay + (R − d)/v₀ (published VBF form).** Legacy √α·DELAY + 2(d − R)/v available with `PaperHoldTime=false` |
| Position precision in the header | (not modelled) | VBHeader serializes positions to the millimetre (`(uint32)(x*1000+0.5)`); receivers compute with the rounded f |
| Eligibility with a single copy | Within the per-hop pipe (distance ≤ threshold) | Pipe **and** α ≤ 1.5 (`m_priority`) |
| Duplicate suppression | β-distance rule + "self-adaptation" (combination unspecified) | min α ≤ 1.5/2^(n−1); quit at `MAX_NEIGHBOR` = 10 (D-07) |
| T_delay | Not given | `DELAY` = 1.0 s |
| Pipe radius | Recommends W = R (Lemma 2); β = 0.75R in their simulations | W = 400 m, R = 1000 m (project choice) |
| MAC | Broadcast MAC, back off, drop after 4 | `AquaSimBroadcastMac`, `BC_MAXIMUMCOUNTER` 4, backoff ≤ 0.1 s (matches; backoff window not given in the paper) |
| v₀ | 1500 m/s | Routing uses 1500; `AquaSimRangePropagation` uses depth-dependent Mackenzie speed (~1534–1555 m/s at 25 °C) |
| Decoding | (not modelled in the paper) | Aqua-Sim PHY: SINR uses constant `RxPower`, so decoding is distance-independent; only collisions fail |

## Recorded EAQTE implementation choices (the paper leaves these unspecified)

| Item | Choice | Note |
|---|---|---|
| f | 25 kHz | WHOI micro-modem (EAQTE ref [48]) |
| k | 1.5 | EAQTE says only k ∈ [1, 2]; DOIDS (Zhang et al. 2023) states 1.5 as the practical case |
| Eb/N0 | 40 dB | 20 dB gave p(1000 m) ≈ 0 |
| Units of d in Eq. 6 | km | |
| m bits | 640 | 80-byte packet |
| n_p (variance window) | 10 | **Currently sampled per call, including logging (correctness issue for comparisons; fix to be proposed separately)** |
| Velocity of j | Estimated from two overheard positions (dt ≥ 0.05 s) | SS = 0.5 when no estimate. EAQTE §3.1 assumes neighbours *exchange* location; HH-VBF has no such exchange |
| Gate granularity | Per observation event | Paper: per time slot (slot length not given) |
| MCM speed | Direction from ∇ψ, fixed magnitude 0.3 m/s | SS uses direction only |

## Stage E (2026-10-04)

| ID | Date | Decision | Source layer | Status |
|---|---|---|---|---|
| D-13 | 2026-10-04 | **Stage E framework ("Option B").** Keep the original EAQTE → environment-masked attack → PACT question, with a common, frozen, oracle-free evidence layer under the trust arms.<br>**Arm labels, mandatory everywhere:**<br>• **Arm 0** = plain HH-VBF<br>• **Arm A** = observer-based trust, no environmental gate<br>• **Arm B** = observer-based trust + EAQTE gate<br>• **Arm C** = observer-based trust + PACT<br>**Evidence layer:** O1 = opportunity conditioning exactly as validated in Stage D (O1-H self-transmission exclusion **OFF**); O2 = MATCH/SILENT aggregation against a frozen clean-seed honest baseline. EAQTE and PACT may only change the weight or exclusion of an otherwise valid opportunity, never how opportunities are built.<br>**S1:** `PriorityScale=0` and `ObservedTrustWeight=0`; trust never affects forwarding; Arms A/B/C are evaluated by offline replay on identical traces.<br>**Scope:** E1–E5 are **security-mechanism validation only**. They must not be described as showing that observer trust improves HH-VBF forwarding performance.<br>Sequence: E1 → E5 with decision gates, a stop-and-report after each stage. | [contribution]; [project] | Specification approved 2026-10-04. **Frozen specification: `analysis/stageE/README.md`, revision 3** (revisions in its §14). E1 under revision 2 failed G1 (E-32, `58cc50c`; historical record kept unchanged); revision-3 re-evaluation of E1 not yet run. |
| D-14 | 2026-10-04 | **Stage E seed allocation:** 12–21 clean calibration (E1, E3); 2–11 E2 held-out observer test; 22–31 E4 attacker arms; **41–50 E5 confirmatory (new)**; 1 development only; 32–40 unused (D-08). | [project] | Approved |
| D-15 | 2026-10-04 | **D1(ii): receiver-side `[RXHDR]` logging.** One logging-only line in `AquaSimTrustQVBF::Recv` logs the decoded f, d, target, IDs and time of every received copy at 17 significant digits. It replaces the Stage D offline header rebuild, which used simulator ground truth, as the observer input path.<br>**S2 (replaces "no C++ changes for E1–E5"):** *One approved logging-only C++ change is permitted solely to expose the exact receiver-decoded header fields; no behavior-changing C++ changes are permitted during E1–E5.* | [project] | **Done:** submodule commit `41c67c3`. Validated on seed 1 (E-31; `analysis/stageE/README.md`). Accepted as final; no further changes to the patch |
| D-16 | 2026-10-04 | **VBHeader `token`, `ts`, `range` are a pre-existing Aqua-Sim-NG trace defect.** The constructor initialises only `m_messType`, so these fields carry uninitialised memory and can change when unrelated code changes stack layout. Nothing in VBF/TrustQVBF reads them. They are **permanently masked** in every behavioural trace comparison. **Do not fix them**: no change to packet/header construction. | [Aqua-Sim-NG] | In force |
| D-17 | 2026-10-04 | **Stage E revision 3.** V6 calibration redesigned: n-binned empirical thresholds (deterministic bins, M = 200, per-bin nearest-rank τ_A,b), power by thinning, and option (i) — if no bin reaches power ≥ 0.80, n_min is undefined and G1 fails, with no change to 0.80 or p_min. V3-a separation rule (> ε + 12.5 m = 37.5 m) replaces the underived 50 m rule. V6 on seeds 12–21 is development validation; the independent false-alarm assessment is G2b on seeds 2–11. Open point P5 (Arm B/C binning) is decided before E3. Basis: E-32 clean-seed diagnostics (`analysis/stageE/e1/diagnostics_rev3/`). Details in `analysis/stageE/README.md` §13 (R3-1 to R3-6). | [project] | Approved; **not yet implemented** |
