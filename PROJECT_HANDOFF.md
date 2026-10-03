# UASN Trust-Aware HH-VBF — Project Handoff (consolidated)

Last updated: 2026-10-03.
Sources: Handoff 1 (first chat), Handoff 2 (second chat), and direct inspection of this workspace on 2026-10-02/03.
Companion files: `EXPERIMENT_LOG.md` (every run), `RESEARCH_DECISIONS.md` (every decision).

**Status tags used below**

| Tag | Meaning |
|---|---|
| VERIFIED | Checked against the code or a run in this workspace (date given). |
| HISTORICAL | Reported in an earlier chat. Not reproducible here: its scripts/outputs are not in this workspace. |
| CORRECTED | An earlier handoff claim that the code or data contradicts. The correction is stated. |
| PRE-REBASELINE | Produced under unlimited reception and the legacy hold-time formula (see §7). Diagnostic only; not to be mixed with results from the corrected model. |

---

## 1. Context

- Final-year project, course 23CSE498, Amrita Vishwa Vidyapeetham (Coimbatore). Target: IEEE paper.
- Platform: NS-3.41 + Aqua-Sim-NG at `~/ns-allinone-3.41/ns-3.41` (WSL2 Ubuntu).
- Workspace provenance (VERIFIED 2026-10-02): a clone of `github.com/chethana100/uwsn`, made 2026-10-02. The aqua-sim-ng submodule is at `fa2e87d`.
  Not present on this machine: the `.bak` source backups, `~/eaqte_*.py`, `~/fix*.py`, `~/uwsn-results`, the analysis code for the flow-level detector and for the observer AUCs, and the 40-seed batch from the other chat.
- Base paper: Khoshvaght et al., "An environment-aware Q-learning-based trust evaluation scheme in UASNs" (EAQTE), *Computer Standards & Interfaces* 96 (2026) 104087.
- Deadline: unknown. The guide's position on negative results and on a head-to-head comparison with the paper: unknown.

### Network (scenario `scratch/uwsn-trustq-attack.cc`, VERIFIED 2026-10-02)

| Parameter | Value |
|---|---|
| Nodes | 100; sink = node 0 fixed at (1500, 1500, 0) |
| Volume | 3000 × 3000 × 2500 m |
| Nominal range | 1000 m (`SetTransRange`); see §7 for what is actually enforced |
| Sources | 10 (chosen by `std::mt19937(BASE_SEED + run)`), about 95 packets each, 950 per run |
| Packet | 80 bytes, 0.033 pkt/s, traffic 2–2900 s, simulation end 3000 s |
| Energy | TX 10 W, RX 3 W, idle 0.03 W, initial 10 000 J |
| MAC | `AquaSimBroadcastMac` |
| Mobility | MCM (`scratch/mcm-mobility-model.h`), sink constant |
| Routing | `AquaSimTrustQVBF` (subclass of `AquaSimVBF`), HopByHop = 1, Width 400 m |
| Seed | `BASE_SEED` 12345, `--run` selects the ns-3 run |

These parameters closely match T-SAPR (Zhu et al., Ad Hoc Networks 2023) Table 2: 3000×3000×2500 m, 1000 m range, 10 W / 3 W / 30 mW.

---

## 2. Terminology (mandatory)

**Four layers. Never attribute an item to a layer that does not state it.**

1. **Original HH-VBF specification**: Nicolaou et al., "Improving the Robustness of Location-Based Routing for Underwater Sensor Networks". VBF (Xie, Cui, Lao, 2006) is only its predecessor/reference.
   - Note: the VBF 2006 paper is not in the attached reference set. The HH-VBF paper says its holding time is "computed the same way as in VBF" but does not print the formula.
2. **Aqua-Sim-NG implementation**: `AquaSimVBF` in `src/aqua-sim-ng/model/aqua-sim-routing-vbf.cc`. Never edited by this project.
3. **Project-specific modifications**: everything in `AquaSimTrustQVBF` and the scenario: trust priority, observer, EAQTE gate, PACT, attacker, logging.
4. **Proposed research contribution**: see `RESEARCH_DECISIONS.md`.

**Baseline.** The experimental baseline is **HH-VBF**, not ordinary VBF. The HH-VBF baseline is `AquaSimTrustQVBF` with `PriorityScale=0` and the trust and attack features off. It is only valid once verification V1–V3 passes (see `RESEARCH_DECISIONS.md`).

**Naming rule.** Two different mechanisms were both called "EAQTE" in earlier chats:
- **"EAQTE gate"**: the paper's per-neighbour environmental freeze (EE < ξ_th = 0.3 ⇒ skip the trust update). Implemented in TrustQVBF.
- **"flow-level detector"**: a sink-side per-flow change detector built in an earlier chat (once nicknamed "EAQTE v2"). It is **not** EAQTE.

Keep them separate in code, filenames, logs and the writeup.

---

## 3. Key files

| Path | Contents |
|---|---|
| `src/aqua-sim-ng/model/aqua-sim-routing-trustq-vbf.{h,cc}` | TrustQVBF: trust priority, observer, EAQTE gate, PACT, attacker, `[DIAG]` logging |
| `src/aqua-sim-ng/model/aqua-sim-routing-vbf.cc` | Aqua-Sim-NG base VBF/HH-VBF (reference; not edited) |
| `scratch/uwsn-trustq-attack.cc` | Main scenario |
| `scratch/mcm-mobility-model.h` | MCM mobility + adversarial motion (header-only) |
| `scratch/uwsn_vbf_compare.cc`, `scratch/uwsn-phase1-baseline.cc` | Use base `AquaSimVBF` directly. They must be switched to the HH-VBF baseline before they are used for comparisons. |
| `scratch/uwsn-trustq-baseline.cc`, `scratch/uwsn-trustq.cc` | Older TrustQ scenarios |
| `analyze_trace.py`, `analyze_results.py` | PDR/delay/energy from the trace; paired statistics |

---

## 4. Seed allocation (from Handoff 2; do not mix)

| Seeds | Use |
|---|---|
| 1 | Development only |
| 2–11 | Observer held-out set + flow-detector v1 |
| 12–21 | Clean calibration |
| 22–31 | Flow-detector v2 + attacker arms |
| 32+ | Free per Handoff 2. **The 40-seed batch from the other chat used unknown seeds.** Confirm before using any of 32–40. |

Run indices present in this workspace: 1–20 only (VERIFIED 2026-10-03).

---

## 5. Code state

### 5.1 TrustQVBF attributes (VERIFIED 2026-10-02)

| Attribute | Default | Notes |
|---|---|---|
| TrustWeight | 0.35 | The scenario overrides it to **0.3** |
| EnergyWeight | 0.30 | |
| DistanceWeight | 0.20 | |
| DelayWeight | 0.15 | |
| TrustDecay | 0.7 | |
| InitialEnergyRef | 10000 | |
| DelayNormConstant | 5.0 | |
| PriorityScale | 0.2 | 0 = HH-VBF baseline |
| PactEnabled | false | |
| IsMalicious | — | Set by the scenario for chosen nodes |
| DropProbability | — | |
| PaperHoldTime | **true** since Stage C (2026-10-03) | true = published √α·T_delay + (R − d)/v₀; false = legacy Aqua-Sim `+2(d−R)/v` |
| PaperDesirableness | **true** (new in Stage C) | true = hold time uses HH-VBF Def. 2 α′; false = Aqua-Sim α. Thresholds always use the Aqua-Sim α |
| ObservedTrustWeight | **0.0** | Observed trust never influences forwarding |
| AttackStart | 0 | |
| AttackMode | 0 | 0 plain, 1 masked, 2 ramped |
| RampTime | 600 | |

### 5.2 Scenario flags

`run`, `tag`, `priorityScale`, `attackerFraction`, `dropProbability`, `adversarialMotion`, `pactEnabled`.

Added 2026-10-03:
- `mobilityLog` (A1, default true): writes `<tag>_<run>_mobility.csv`.
- `routing=trustq|aquasim-hhvbf` (A2, default `trustq`). `aquasim-hhvbf` is the unmodified Aqua-Sim-NG `AquaSimVBF` with HopByHop=1; it rejects attackers, PACT and adversarial motion.
- `propagation=range|simple` (Stage B, default `range`). `simple` exists only to reproduce pre-rebaseline runs. `RX_RANGE_M` > 0 with `range` aborts.

`_meta.csv` now ends with 17 record-keeping columns: run, base_seed, propagation, routing, hop_by_hop, width, priority_scale, trust_weight, observed_trust_weight, paper_hold_time, pact_enabled, attack_start, attack_mode, rx_range_m_env, eaqte_xi_env, sink_mobility, stream_base.

Other attributes can only be set as `--ns3::AquaSimTrustQVBF::<Name>=<value>`.

### 5.3 Environment variables

| Variable | Effect |
|---|---|
| `EAQTE_XI` | Freeze threshold (default 0.3; 0 = gate off) |
| `RX_RANGE_M` | Routing-layer reception cut. **Applied in code** (CORRECTED: Handoff 2 said "not applied"). Default off. **Not to be used in final experiments.** |

### 5.4 Logs (stderr, `NS_LOG_UNCOND`)

- `[EAQTE] TX/RX`, `[OBSERVER] watch/CUSTODY/DEVIATION/TIE/MODELMISS/TIMEOUT/DROP`, `[EE]`, `[SSCCQ]`, `[EAQTE-FREEZE]`, `[EAQTE-ATTEMPT]`, `[PACT]`, `[EAQTE-SS]`, `[EAQTE-CCQ]`, `[RANGE]`.
- Added 2026-10-02 (logging-only, `// [DIAG]`, 28 lines): `[DECISION]`, `[HOLD]`, `[VERDICT]`.

### 5.5 Run directly (VERIFIED)

```
LD_LIBRARY_PATH=build/lib build/scratch/ns3.41-uwsn-trustq-attack-default --run=1 --tag=X ...
```

About 22 s per run. The trace is about 94 MB; stderr is about 30 MB with the `[DIAG]` logging.

---

## 6. Historical results (HISTORICAL + PRE-REBASELINE)

Reported in earlier chats under unlimited reception and the legacy hold formula. Not reproducible from this workspace.

### 6.1 Flow-level sink detector (not EAQTE)

- **Method:** per flow, scan change points with a two-proportion z-test and keep the maximum Z. The threshold is the 95th percentile of Z on clean runs. Flows that are dead before onset are excluded.
- **v1** (distance baseline, seeds 2–11): AUC 0.611, TDR 0.16, FAR 0.13.
- **v2** (per-flow change detection, seeds 22–31, onset 500 s): AUC 0.789 (≥5% loss) [95% CI ≈ 0.69–0.89], TDR 0.17, FAR 0.03.
  - By loss threshold: ≥1 packet 0.763 | ≥10% 0.781 | ≥20% 0.819.
  - Onset error median 105 s (n = 6).
- **Attacker arms:**

  | Arm | Drops | Packets lost | AUC |
  |---|---|---|---|
  | Plain, p = 0.75 | 3138 | 811 | 0.789 |
  | Masked | 1654 | 449 | 0.683 |
  | Plain, p = 0.40 (matched budget) | 1667 | 492 | 0.686 |

  Masking gave no stealth advantage.
- VBF redundancy absorbs about 70% of drops; only 26–31% of malicious drops cost a packet.

### 6.2 Node-level observer (rigorous negative)

- Held-out AUC 0.523 (frozen design); 0.553 with the oracle custody tag. The pre-set bar was 0.7: **FAIL**.
- Diagnosed cause: relays self-select, so a dropper looks like a node that lost the race.

### 6.3 The paper's gate in our network

- EE over 14,323 decisions: median 0.764; 0.92% below 0.3.
- 132 freezes, all at distance > 1480 m and CCQ < 0.6, **zero on attackers**. Node 99 absorbs most freezes (a volume effect).
- Clean calibration (Handoff 1): 197 freezes out of about 16,900 attempts.

### 6.4 Attack on the gate (adversarial motion)

- v1: 91 freezes on malicious vs 859 on honest.
- v2: 10 vs 125.
- SS is symmetric, so an attacker cannot destabilize only its own evaluations.
- Handoff 1 gives these tables; Handoff 2 says the runs were "never analysed". **The two handoffs conflict.**

### 6.5 PACT pilot (seed 1)

- Honest mean 0.6696 → 0.6664.
- Droppers stayed at 0.5000 in both arms.
- **Run with `ObservedTrustWeight=0`**, so trust never affected routing.

### 6.6 Findings against the EAQTE paper (from its own equations)

- Variance of p ≤ 1/4, so CCQ ≥ 0.755·p. The paper's Eq. 24 claim that CCQ → 0 is impossible.
- A freeze needs p < 0.795.
- Whether the gate can fire depends on constants the paper does not report.
- The paper's pairwise communication evidence has no counterpart in HH-VBF.

---

## 7. Verified findings, 2026-10-02/03 (seed 1, development diagnostics)

### 7.1 Reception is not range-limited

- `AquaSimSimplePropagation` (the helper default) delivers to every node, and the PHY's `RXThresh` = 0.
- The SINR check uses the energy model's constant `RxPower`, so decoding is independent of distance. Only overlapping receptions fail.
- About 46 decoded copies per transmission.

### 7.2 NaN hold time

- `sqrt(baseDelay)` with baseDelay < 0 occurs for receivers more than ~1 km ahead of the transmitter.
- In ns-3.41, `Seconds(NaN)` becomes **exactly 0.5 s**.
- 22.4% of relay transmissions were affected. base < 0 ⇔ NaN holds one-for-one (970 of 970).
- NaN holds go to 0 with `RX_RANGE_M=1000`.

### 7.3 Legacy hold time `+2(d−R)/v`

Hold time is non-monotone in distance: nodes 0–500 m from the previous hop fire first (median 0.09 s).

### 7.4 `RX_RANGE_M` is a routing-layer filter only

- The PHY still decodes far copies (~48 per transmission), which still cause collisions and cost receive energy.
- Trace-based PDR 467 vs routing 283.
- The plain-VBF scenarios never apply the cut.

### 7.5 Observer accounting (`[DIAG]` cross-tab)

**At dropProbability 1.0:**
- 0 of 41,358 predicted watches were on an attacker.
- All 185 drops were never watched.

**At dropProbability 0.75:**
- Only 11% of blames were real drops.
- 69% of drops were never watched.
- Every credit was a true forward.
- 82% of blames on honest nodes involved a node that had responded to a different upstream copy.

### 7.6 `ExtraInfo.d` is on air

- CORRECTED: Handoff 2 said "does not survive".
- Its negative components wrap as `uint32`. Undoing the wrap (v > 2147483.648 ⇒ v − 4294967.296) recovers the upstream position within 8 m, uniquely in 4,064 of 4,064 relay transmissions.
- This gives a non-oracle substitute for the custody tag.

### 7.7 Custody tag

- It is a simulator `ByteTag` (0 bytes on air).
- **Every** observer trust update requires it. The current code is the oracle variant (the 0.553 design), not the frozen 0.523 design.

### 7.8 CCQ history

The CCQ variance window is "the last 10 *calls*", including logging calls and PACT's loop over all neighbours. That confounds EAQTE-vs-PACT comparisons.

### 7.9 RNG streams

- ns-3 assigns each RNG object a stream when it is created.
- TrustQVBF creates one extra RNG per node (`m_dropRand`). That shifts the MAC backoff streams relative to base VBF, so different arms are not paired at the level of random draws unless streams are pinned.

### 7.10 VBHeader `range=` field

Uninitialized. It differs between identical runs, so traces must be compared with `range=` masked.

### 7.12 The sink is not fixed (VERIFIED 2026-10-03, E-11)

- `sensorMobility.Install (nodes)` gives node 0 MCM.
- The later `sinkMobility.Install (nodes.Get (0))` is a no-op, because `MobilityHelper::Install` only creates a model when none exists (`mobility-helper.cc:88–89`). Line 185 only sets the starting position.
- The sink drifts about 700 m per run, while the routing target `TargetPos` stays at (1500, 1500, 0).
- **CORRECTED:** both handoffs say "sink = node 0 fixed at (1500, 1500, 0)".
- `uwsn-trustq-baseline.cc` has the same pattern (Gauss-Markov). `uwsn_vbf_compare.cc` is correct (separate containers).
- Every historical result was produced with a drifting sink.
- **FIXED in Stage A2 (2026-10-03)** in `uwsn-trustq-attack.cc`: MCM on nodes 1..99 only; the scenario aborts unless the sink is ConstantPosition. Verified: sink at (1500, 1500, 0) with zero velocity throughout.
- **FIXED in Stage B** in `uwsn-trustq-baseline.cc`, with the same abort check.

### 7.13 Reception range enforced at the channel (Stage B, 2026-10-03)

- All 5 scenarios use `AquaSimRangePropagation`. The main scenario has `--propagation=range|simple` (default `range`) and refuses `RX_RANGE_M` with `range`.
- Verified on seed 1 (E-19):
  - 0 decoded copies beyond 1000 m (max 999.99 m at transmission time, from exact positions).
  - About 11.3 copies per transmission, versus about 51 before.
  - Trace deliveries equal routing deliveries (UID sets equal).
  - 0 negative base values, 0 NaN/Inf anywhere.
  - Maximum distance used in a hold calculation: 948.5 m.
- §7.1, §7.2 and §7.4 describe the pre-Stage-B model and are now historical.

### 7.14 HH-VBF hold time corrected (Stage C, 2026-10-03)

- Hold time = √α′·T_delay + (R − d)/v₀ with α′ = (R − d cosθ)/R (HH-VBF Def. 2). The self-adaptation thresholds still use the Aqua-Sim-NG α (documented deviation, D-07).
- Verified on seed 1 (E-25):
  - α′, d and the hold time recomputed independently match **exactly**.
  - 100% of decidable forward/suppress decisions reproduced by an independent replay.
  - 0 guard events and 0 non-finite values under range propagation.
- Hold time now decreases with progress (Spearman −0.922, versus −0.347 for the legacy formula).
- §7.3 is historical.
- **Known consequence:** the old diagnostic observer's prediction functions (`PredictDelayFor`, `FireTimeFor`, `PredictExpectedForwarder`) were deliberately left unchanged. They still model the Aqua-Sim α hold, so its verdicts don't match the new routing; Stage D replaces it.
- **Analysis pitfalls:** VBHeader rounds positions to the millimetre. Trace times have only 6 significant digits; use the 17-digit `[HOLD]` fields and the mobility log for exact work.

### 7.15 Stage D observability accounting (2026-10-03; seed 1, corrected HH-VBF baseline with PriorityScale 0, diagnostic)

- **Evidence availability:**
  - p = 1.0: **0%** of drops have any valid observable opportunity; the droppers never transmit, so no observer knows they exist.
  - p = 0.75: **33.7%** of drops are observable. 60.5% are lost to stale presence information (freshest entry 89–639 s old).
- **Evidence discrimination (p = 0.75):**
  - Only **5.7%** of valid silent opportunities are drops (unique (X, c): 7.4%).
  - The rest: X never decoded the copy (37%), X acted on a different upstream copy (32%), X forwarded but O didn't hear it (20%), plus ineligibility and suppression.
- **Positive evidence is exact:** every MATCH is a true forward. The recovered upstream agrees with the custody tag 100% at position level and never disagrees at identity level.
- **The EAQTE gate is structurally inert** in the corrected network under our constants (EE ≥ 0.354 for any in-range neighbour; 0 exclusions; 0 C++ freezes). §6.3's freezes all came from beyond-range receptions.
- **CORRECTED:** E-07 / §7.6 attributed 3.8–7.8 m recovery error to the on-air `d`. It was trace print precision; the on-air recovery error is ≤ 0.6 m.

### 7.11 Other observations

- Broadcast MAC drops a packet silently after 4 backoffs: about 6% of `FWD` decisions never reach the air.
- `AquaSimRouting::SendUp` is a stub. Sink deliveries come from the trace / `[EAQTE] RX`.

---

## 8. Other corrections to earlier handoffs

| Earlier claim | Correction |
|---|---|
| TrustWeight 0.35 | Effective value 0.3 (scenario override) |
| Max leverage of observed trust ≈ 2.6% (0.5 × 0.35 × 0.15) | With the code's constants: 0.5 × 0.3 × 0.2 = **3%** |
| (not previously noted) | The trust term reads the observed trust of the packet's **original source** (`GetSenderAddr`), not of the previous hop |
| Eb/N0 = 20 dB (header comment) | Code uses **40 dB**; only the comment is stale |
| Handoff 2 module status / Q-learning | No Q-learning routing exists in the code. "TrustQ" is only a class name. |

---

## 9. Working practices (from both handoffs; still in force)

- Real terminal output, never descriptions.
- Inspect the real file before every change; never edit from memory.
- Patch with anchor-checked scripts that verify the source checksum and abort cleanly. `grep -c` after patching. Build. Report warnings. One change at a time.
- `-Wreorder` warnings in `mcm-mobility-model.h` and in the TrustQVBF constructor are known and harmless.
- Fix pass criteria **before** running. Evaluate on seeds not used in design.
- Preserve valid negative results. Scale claims to the evidence. Correct earlier claims explicitly.
- Bash redirect order: `> file 2>&1`.
- `.vscode/watch-and-push.sh` asks "Commit and push?" on any change. Answering *y* runs `git add -A`, which would commit about 8,500 build files and traces up to ~94 MB.

---

## 10. Open items

- Stage plan A1 → A2 → B → C → D (see `RESEARCH_DECISIONS.md` D-09). Stages run one at a time, with a report after each.
- Not yet run:
  - Online replay (`eaqte_online.py`, missing from this workspace)
  - MLAR sweep (`uwsn_vbf_compare`)
  - Ramped attacker (AttackMode = 2)
  - Range-sensitivity pair
  - Baseline detectors (naive threshold, EWMA/CUSUM, per-node forwarding-rate clustering)
- Missing from this workspace: flow-detector and AUC analysis code; the 40-seed batch (command line, analyzer, seeds).
- Post-Review-2 report (a Claude Doc) predates the naming fix, the confidence intervals and the range finding.
- Authorship and venue AI-disclosure policy: to agree with the guide.
