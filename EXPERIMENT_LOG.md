# Experiment Log

One entry per experiment: purpose, code state, exact command, seed, parameters, output location, result, status.

Common settings unless stated: scenario `scratch/uwsn-trustq-attack.cc`, `BASE_SEED` 12345, propagation `AquaSimSimplePropagation` (unlimited reception), `PaperHoldTime=false` (legacy hold formula).
**All entries below are PRE-REBASELINE diagnostics** (see `PROJECT_HANDOFF.md` §7). Do not mix their numbers with results from the corrected model.

**Output location warning.** Runs from 2026-10-02/03 were written to Claude's session scratchpad:
`/tmp/claude-1000/-home-aswinlaks-ns-allinone-3-41-ns-3-41/4a4ba5ed-eb43-4726-8c1d-c1ce127f6cfd/scratchpad/`
That directory is **not persistent**. The scripts and summaries are recorded here; regenerate the outputs if needed (each run takes about 22 s).
**It was wiped by a WSL restart on 2026-10-03, after Stage D.** The Stage C/D scripts and outputs were then rebuilt into `analysis/` and the runs regenerated into `~/uwsn-runs/stageCD_seed1/`. See E-30.

Run command template (from that directory):
```
LD_LIBRARY_PATH=/home/aswinlaks/ns-allinone-3.41/ns-3.41/build/lib \
  /home/aswinlaks/ns-allinone-3.41/ns-3.41/build/scratch/ns3.41-uwsn-trustq-attack-default \
  --run=1 --tag=insp --attackerFraction=0.2 --dropProbability=<p> > stdout.log 2> stderr.log
```

---

## Historical (earlier chats; not reproducible here)

| ID | What | Seeds | Result | Status |
|---|---|---|---|---|
| H-01 | Observer held-out evaluation | 2–11 | AUC 0.523; 0.553 with custody oracle; bar 0.7 → FAIL | HISTORICAL; command line unknown |
| H-02 | Flow-level detector v1 | 2–11 | AUC 0.611 | HISTORICAL |
| H-03 | Flow-level detector v2 + attacker arms | 22–31 | AUC 0.789; masked 0.683; matched-budget 0.686 | HISTORICAL |
| H-04 | Clean calibration (gate freeze rate) | 12–21 (per allocation) | 197 / ~16,900 freezes | HISTORICAL |
| H-05 | Adversarial-motion v1/v2 | unknown | 91/859 and 10/125 freezes (malicious/honest) | HISTORICAL; handoffs conflict on whether it was analysed |
| H-06 | PACT pilot | 1 | Honest 0.6696 → 0.6664; droppers 0.5 in both arms | HISTORICAL; `ObservedTrustWeight=0` |
| H-07 | 40-seed batch | unknown | unknown | HISTORICAL; command line, analyzer and seeds not available |
| H-08 | Older `noattack`/`underattack`/`heavyattack`/`trustq` runs present in repo root | 1–20 | Files present; producing code version unknown | Present in workspace |

---

## 2026-10-02

### E-01 — First inspection run, dropProbability 1.0
- Code: TrustQVBF at submodule HEAD (`.cc` md5 `961383608c66c5bcacc1569de2f8d2f7`), binary already built.
- Params: `--run=1 --tag=insp --attackerFraction=0.2 --dropProbability=1.0`. Output: `scratchpad/run1/`.
- Result:
  - 185 drops, by 3 of 20 attackers (nodes 34, 65, 76).
  - 0 of 41,358 predicted watches were on an attacker. Droppers' observed trust stayed at 0.5.
  - 46.0 decoded copies per transmission. PDR 601/950 = 63.26%.
  - 135 freezes, all on honest nodes.
- Analysis scripts: `obs_inspect.py`, `hold_inspect.py`.
  - 22.4% of relay transmissions had base < 0 (NaN path).
  - 48.8% of relays were > 1 km from the upstream transmitter.
  - Hold time is non-monotone in distance.

### E-02 — Same, dropProbability 0.75
- Output: `scratchpad/run1p75/`.
- Result: 150 drops. Dropper node 34 ended at observed trust 0.73. 87% of blames hit honest nodes.

### E-03 — ns-3 NaN-to-Time check
- `nantest.cc` and `nantest2.cc` (scratchpad), compiled against `libns3.41-core-default`.
- Result: `Seconds(NaN)` = 0.5 s for every NaN tested; it does not assert.

### E-04 — Determinism baseline before the diagnostic patch
- Params: `pre_p100_a` and `pre_p100_b` (p = 1.0, identical runs), `pre_p075` (p = 0.75).
- Result:
  - All outputs identical between identical runs **except the `.tr`**.
  - The cause is VBHeader `range=`, which is uninitialized. The traces are identical once that field is masked.

### E-05 — Logging-only `[DIAG]` patch verification
- Code: `.cc` md5 `d9677a0ea208527206a5e75e50505fe1` (28 inserted lines). Build OK (only the known `-Wreorder` warnings).
- Params: `post_p100` (p = 1.0) and `post_p075` (p = 0.75) vs E-04.
- Result:
  - Trust, observed, energy and meta CSVs and stdout byte-identical.
  - Trace identical with `range=` masked.
  - stderr identical once `[DECISION]`/`[HOLD]`/`[VERDICT]` lines are removed (354,182 and 355,545 lines).

### E-06 — Observer verdict vs ground-truth cross-tab
- Scripts: `diag_crosstab.py`, `diag_extra.py` on `post_p100` and `post_p075`. Outputs `xtab_p100.txt`, `xtab_p075.txt`.
- Integrity: watches = final verdicts (71,230 and 70,513); no node made two decisions on one packet.
- Result (p = 0.75):
  - 11% of blames were real drops.
  - 69% of drops were never watched.
  - Every credit was a true forward.
  - Blames on honest nodes: 37% out of pipe, 22% ineligible, 25% had forwarded and transmitted.
- Result (p = 1.0): 185 of 185 drops never watched.

## 2026-10-03

### E-07 — Upstream recovery from on-air `d`
- Script: `d_recover.py` on `post_p075` and `post_p100`.
- Result: recovery error median 3.8 m, max 7.8 m. The true upstream was the nearest candidate in 4,064 of 4,064 transmissions; the nearest other transmitter was at least 166 m away at the 5th percentile.

### E-08 — `RX_RANGE_M=1000` (routing-layer cut)
- Params: `rx1000_p100`, `rx1000_p075`, environment variable `RX_RANGE_M=1000`, seed 1.
- Result:
  - 0 NaN holds.
  - The PHY still decodes 48.0 and 47.4 copies per transmission.
  - Trace-based deliveries 467/463 vs routing 283/282.
- Not to be used in final experiments.

### E-09 — Counterfactual for the NaN clamp
- Script: `nan_counterfactual.py`.
- Result: base < 0 ⇔ NaN in 970 of 970 cases. With a clamp, the legacy formula gives these nodes 1.28–1.60 s (all later than the current 0.5 s); the paper formula gives 0 s.

### E-10 — Seed-32 availability check
- Runs present in the workspace: indices 1–20 only. `run_*.sh` default to 1..20.
- The other chat's 40-seed batch (seeds unknown) is not available.
- Status: **cannot confirm** that seed 32 is unused. Awaiting the user's decision.

### E-11 — Stage A1 verification (logging/provenance only)
- Code: scenario md5 `b3ac1069…` → `fa2c1e95…` (87 insertions; 2 meta lines extended). Library unchanged (`477e2aab…`). Build OK; only the 3 known MCM `-Wreorder` warnings.
- Params: `a1_p100` and `a1_p075` (seed 1, attackerFraction 0.2, p = 1.0 / 0.75) vs `post_p100` / `post_p075`.
- Result: **PASS.**
  - Energy, observed and trust CSVs, stdout and stderr byte-identical.
  - Trace identical with `range=` masked.
  - The 10 original meta columns identical; 15 provenance columns appended.
  - New `insp_1_mobility.csv`: 300,000 rows (100 nodes × 3000 samples at k+0.5 s), ~32 MB.
- **New finding:** the sink drifts (node 0 x: 1500 → 2197 m over the run). `MobilityHelper::Install` keeps an existing model, so the ConstantPosition install for the sink is a no-op. See `PROJECT_HANDOFF.md` §7.12.

---
**From Stage A2 onward the sink is fixed and RNG streams are pinned.** Outputs are not comparable with E-01..E-11. Everything is still PRE-REBASELINE: unlimited reception and legacy hold time until Stages B/C.

### E-12 — Stage A2 code change
- Scenario md5 `fa2c1e95…` → `9d0eb352…`. Library unchanged.
- Changes:
  - **Sink fix:** MCM on nodes 1..99 only; abort unless the sink is `ConstantPositionMobilityModel`.
  - `--routing=trustq|aquasim-hhvbf`.
  - Per-node MAC stream `1000+2i` and routing stream `1000+2i+1`.
  - Meta columns `sink_mobility`, `stream_base`.
- Build OK. Warnings: the known `-Wreorder` set plus make's "Clock skew detected"; the binary was confirmed newer than the source and to contain the A2 code.
- Note: `AquaSimPropagation::RayleighAtt` creates a new RNG per call (automatic stream). Checked as harmless: the signal cache uses the constant `RxPower`, not the drawn value, and `r` records don't contain the power stamp.

### E-13 — A2 determinism (seed/run 1, DEVELOPMENT/DIAGNOSTIC, no attackers)
- `a2_tq_a`/`a2_tq_b`: `--run=1 --routing=trustq --priorityScale=0`.
- `a2_vb_a`/`a2_vb_b`: `--run=1 --routing=aquasim-hhvbf`.
- Result: **PASS.** Within each arm, every output is byte-identical; the trace is identical with `range=` masked (120,666 records: 2,331 t, 118,335 r).

### E-14 — V1: TrustQVBF (PriorityScale=0, ObservedTrustWeight=0, legacy hold) vs base AquaSimVBF (HopByHop=1)
- Seed/run 1, DEVELOPMENT/DIAGNOSTIC. Unlimited reception (current propagation). No attackers.
- Result: **PASS.**
  - Trace **identical record for record** after masking only `range=` and `dataType=` (120,666 records).
  - Energy and mobility byte-identical.
  - Deliveries 706/950 (PDR 74.32%) in both; delay avg 1.707 s in both.
- Expected differences only: trust CSV (empty for base), stderr (TrustQ logs), meta configuration columns.
- Control: masking `range=` alone diverges at record 1 (the `dataType` header byte), confirming it is a genuine difference.
- **Scope of the claim:** under these matched conditions (seed 1, this topology, no attackers, unlimited reception, legacy hold time), TrustQVBF with PriorityScale=0 reproduces the base Aqua-Sim-NG HH-VBF forwarding behaviour. This does not by itself prove equivalence in general. V1 is repeated under range propagation in Stage B; the published hold time and α′ are covered by V2/V3 in Stage C.

### E-15 — A2 smoke test of the attacker path (seed 1, DIAGNOSTIC)
- `a2_smoke_p075`: `--run=1 --attackerFraction=0.2 --dropProbability=0.75` (trustq, PriorityScale default 0.2).
- Result: runs normally. 41 drops by 3 droppers (nodes 4, 14, 62); 658 deliveries; provenance shows the ConstantPosition sink and stream base 1000.

---
**Stage B (2026-10-03).** Range propagation is enforced at the channel; legacy hold time is still in use, so every result is still PRE-REBASELINE until Stage C. All runs are seed/run 1, DEVELOPMENT/DIAGNOSTIC.
Stage B numbers (PDR, delay, energy) are **not** to be compared with earlier numbers as performance results: the physical model changed deliberately.

### E-16 — Stage B code change
- Scenario md5s:
  - attack `9d0eb352…` → `ddc4c875…` (+17 lines)
  - trustq-baseline `8bcbca5d…` (+24 / −1: sink fix)
  - trustq `08e5ee07…` (+10)
  - phase1 `d449202e…` (+3)
  - vbf_compare `4594a245…` (+3)
- Library unchanged. All 5 targets build; no new warnings.
- Binaries confirmed to contain the intended strings: range propagation in all 5; `RX_RANGE_M` refusal in the 3 TrustQVBF scenarios; sink check in attack and trustq-baseline.

### E-17 — B1: `--propagation=simple` reproduces A2
- Pairs: `b1_tq` vs `a2_tq_a`; `b1_vb` vs `a2_vb_a`; `b1_smoke` vs `a2_smoke_p075`.
- Result: **PASS.** All outputs byte-identical; trace identical with only `range=` masked; meta identical.

### E-18 — Range runs, determinism and `RX_RANGE_M` refusal
- `b_tq_a`/`b_tq_b` (trustq, PriorityScale 0): **PASS**, identical with `range=` masked (26,034 records).
- `RX_RANGE_M=1000` with range propagation: aborts with "[B] RX_RANGE_M is set…" (exit 134), as intended.

### E-19 — B2/B3/B4 (`b_checks.py`)
- Positive control `b1_tq` (simple): 99,409 decoded copies > 1000 m; 287 NaN holds. The checks do detect violations.
- Two bugs in my analysis script were found and fixed before reporting:
  - `r`-record UniqueID was being skipped (B3 initially showed 1 delivery).
  - Transmissions at exact whole seconds now use the worse of the two possible MCM positions.

| Check | b_tq_a (trustq PS=0) | b_smoke (p=0.75, PS=0.2) | b_vb (base AquaSimVBF) |
|---|---|---|---|
| Transmissions / decoded copies / copies per tx | 2125 / 23909 / 11.25 | 2036 / 22949 / 11.27 | 2125 / 23909 / 11.25 |
| Unmatched decoded copies | 0 | 0 | 0 |
| Max tx→rx distance at transmission time | 999.989 m | 999.991 m | 999.989 m |
| Copies > 1000 m | **0** | **0** | **0** |
| Copies in (999, 1000] / (990, 999] m | 106 / 512 | 117 / 491 | 106 / 512 |
| Nodes within 1000 m per tx; decoded / in-range | 13.64; 0.825 | 13.55; 0.832 | 13.64; 0.825 |
| B3: trace sink UIDs vs `[EAQTE] RX` | 304 = 304, sets equal | 317 = 317, sets equal | 304 (no routing log) |
| `[HOLD]` calculations | 2785 | 2756 | n/a |
| base < 0 / non-finite base, hh or final | 0 / 0 | 0 / 0 | n/a |
| base min / max | 0.1023 / 2.8467 | 0.1023 / 2.8467 | n/a |
| final hold min / max | 0 / 1.6031 s | 0 / 1.4724 s | n/a |
| hh min (legacy formula); finals clamped to 0 | −0.0923; 16 | −0.0923; 2 | n/a |
| Max hold-time distance (receiver at reception vs stamped f) | 948.5 m (0 > 1000) | 948.2 m (0 > 1000) | n/a |
| `[GUARD]` events | 0 (guard not implemented until Stage C) | 0 | 0 |
| nan/inf anywhere in stderr (all tags) / trace | none / 0 | none / 0 | none / 0 |

- Note: negative `hh` comes from the legacy `+2(d−R)/v` term for receivers close to the transmitter. It is finite, is clamped to 0 by the existing code, and is not a domain violation of α. It disappears with the published (R−d)/v₀ ≥ 0 in Stage C.

### E-20 — V1 repeated under range propagation
- `b_tq_a` (trustq, PriorityScale 0, ObservedTrustWeight 0, legacy hold) vs `b_vb` (base AquaSimVBF, HopByHop 1). No attackers.
- Result: **PASS.**
  - Trace identical record for record after masking only `range=` and `dataType=` (26,034 records).
  - Energy and mobility byte-identical. 304 deliveries and delay avg 1.3218 s in both.
- Control (`range=` masked only): diverges at record 1 (the `dataType` byte).
- Same scope limits as E-14: matched conditions only, not a general proof.

### E-21 — The other four scenarios under range propagation (smoke test)
- trustq-baseline: exit 0; 11.23 copies per tx; sink check passed.
- trustq: exit 0; 11.20.
- phase1: exit 0; 10.98.
- vbf_compare (`--simTime=600 --traces=true --hopByHop=1 --width=1000`): exit 0; 7.70.
- Under simple propagation these would be about 50 copies per tx.

---
**Stage C (2026-10-03).** R2 (published hold time) + R3 (HH-VBF Def. 2 α′ for the hold time only) + defensive guard. Seed/run 1, DEVELOPMENT/DIAGNOSTIC. With range propagation and the published hold time now in place, the routing model is the corrected HH-VBF baseline configuration. Results here are still seed-1 diagnostics, not an evaluation.

### E-22 — Stage C code change
- TrustQVBF `.h` `e3d5effd…` → (+5); `.cc` `d9677a0e…` → (+52 / −7, every removed line a replaced one).
- Scenario `ddc4c875…` → (+4): meta column `paper_desirableness`.
- Changes:
  - `PaperHoldTime` default true.
  - New `PaperDesirableness` attribute (default true).
  - New `HhvbfDesirableness()`: α′ = (R − d cosθ)/R, used for the hold time only.
  - Guard `!(holdAlpha >= 0)` → logged `[GUARD]`, clamp to 0.
  - `[HOLD]` gains 17-digit `halpha`, `d`, `hhx`, `finx`, `tx`.
- `TimeoutTrustAware`, `Recv`, all observer functions, EAQTE, PACT and attacker code verified byte-identical to before.
- All 5 targets build; no new warnings.

### E-23 — C1: legacy attributes reproduce Stage B
- `--ns3::AquaSimTrustQVBF::PaperHoldTime=false --ns3::AquaSimTrustQVBF::PaperDesirableness=false`.
- Pairs: `c1_tq` vs `b_tq_a`; `c1_smoke` vs `b_smoke`; base `c_vb` vs `b_vb`.
- Result: **PASS.**
  - Trace (`range=` masked), energy, mobility, trust, observed and stdout identical.
  - stderr identical after stripping only the appended `[HOLD]` fields.
  - Stage B meta columns identical.

### E-24 — New default: determinism and C3 guard test
- `c_tq_a` vs `c_tq_b`: **PASS**, identical (28,819 records).
- C3 `c3_simple` (`--propagation=simple`, new default): 517 `[GUARD]` events (negative α′, e.g. −0.333, from receivers beyond R), 0 NaN/Inf. The guard works and is logged.

### E-25 — V2/V3 (`v23.py`)
- Two of my own replay errors were found and fixed before reporting:
  - f must be rounded to the millimetre as VBHeader serializes it (`(uint32)(x*1000+0.5)`).
  - Trace times are printed to 6 significant digits (10 ms at t ~ 1000 s), so copies within half that resolution of the timer expiry are undecidable. This caused 1 apparent mismatch in the legacy control (node 60, packet 21/921); the logged n=1 shows that copy arrived after the timer.

| | c_tq_a (PS=0) | c_smoke (p=0.75, PS=0.2) | c1_tq legacy (control) |
|---|---|---|---|
| `[HOLD]` lines / `[GUARD]` | 3135 / 0 | 3305 / 0 | 2785 / 0 |
| Non-finite halpha, d, hh, final | 0 | 0 | 0 |
| α′ (halpha) min / max | 0.0947 / 1.9072 | 0.0635 / 1.9072 | (Aqua-Sim α) 0.1023 / 2.8467 |
| hh min / max; negative final | 0.371 / 1.625 s; 0 | 0.288 / 1.625 s; 0 | −0.092 / 1.603 s; 0 (16 clamped) |
| Internal identity \|hh − (√α′·T_delay + (R−d)/v₀)\| | **0** | **0** | 1.587 (expected: legacy formula) |
| final == hh (17-digit string) | 3135/3135 | 0/3305 (PS=0.2 scales by priority, as designed) | 2769/2785 |
| Independent α′ / d / T from mobility log (max error) | **0 / 0 / 0** over 3079 | **0 / 0 / 0** over 3245 | α′ off by 0.9999 (expected) |
| Skipped (ambiguous printed time) | 56 | 60 | 56 |
| V3 decisions reproduced | **3078/3078** (57 skipped) | **3245/3245** (60 skipped) | 2676/2676 (109 skipped) |

### E-26 — Forwarding change: range-corrected legacy (`c1_tq`) vs Stage C default (`c_tq_a`), seed 1
Diagnostic only; not a performance result.

| | Legacy (c1_tq) | Stage C (c_tq_a) |
|---|---|---|
| Transmissions | 2125 | 2516 |
| Decisions FWD / SUPPRESS / INELIG / OUTPIPE | 1178 / 744 / 863 / 10856 | 1569 / 185 / 1381 / 13029 |
| Sink deliveries (trace = routing) | 304 | 428 |
| Delay avg / max | 1.32 / 3.16 s | 2.13 / 8.30 s |
| Relays per (packet, upstream copy): mean; 1/2/3 | 1.63; 385/215/121 | 1.65; 614/50/285 |
| Median hold by progress 0–250 / 250–500 / 500–750 / 750–1000 m | 0.274 / 0.143 / 0.536 / 0.625 s | 1.406 / 1.110 / 0.919 / 0.507 s |
| Spearman(hold, progress) | −0.347 | **−0.922** |

---
**Stage D (2026-10-03).** Offline opportunity accounting on the corrected HH-VBF baseline model:
- Stage C binary (lib `f9880f3d…`), range propagation, published hold time, α′.
- **PriorityScale=0** in every run, so the hold ranking is exactly the α′ hold; ObservedTrustWeight 0.
- Seed/run 1, DEVELOPMENT/DIAGNOSTIC; not an evaluation.
- No C++ changes.
- Scripts: `d_common.py`, `d_recovery.py`, `d_accounting.py`. Full output: `stageD_tables.txt`.

### E-27 — Stage D runs
- `c_tq_a` (clean, reused from E-24).
- `d_p100`: `--routing=trustq --priorityScale=0 --attackerFraction=0.2 --dropProbability=1.0`.
- `d_p075`: same with p = 0.75.
- 218 / 172 drops, each by 3 droppers (nodes 5, 15, 58 by address); 411 / 415 deliveries.

### E-28 — Upstream recovery validation (before accepting ε)
- **Precision note:** the trace prints 6 significant digits, so a wrapped negative `d` component (~4.29e6) is printed with ±5 m error. E-07's 3.8–7.8 m errors were mostly print precision.
- Here the exact header bytes were rebuilt (f = mm-rounded position at MACprepare; d = relay position at reception − upstream's rounded f, serialized as `(uint32)(d*1000+0.5)` with truncate-and-wrap).
- **The rebuild matches the printed trace values within print resolution in 100% of transmissions** (0 f and 0 d mismatches; 34–40 per run not rebuildable because a time is ambiguous).
- Recovery error |(f_X − d_X) − f_upstream|: median 0.30 m, p99 0.600 m, **max 0.601 m** in all three runs. This is the relay's MCM drift (0.3 m per step) between reception and MACprepare.
- Nearest *other* transmitter of the same packet to the recovered position: **min 136.1 m**; p5 182.5 m. **0** ambiguous at 25 m.
- Pre-stated rule (max error ≤ 12.5 m) → **ε = 25 m ACCEPTED**.

### E-29 — Five diagnostics + relay-count observation (complete tables in `stageD_tables.txt`)
- **Custody-equivalence check:** `[DECISION] up` equals the custody tag's prev on every `[VERDICT] CREDIT` line (5145 / 5595 / 5241 equal, 0 different).
- **D1, DROP observability** (≥1 valid observable opportunity):
  - **p = 1.0: 0/218 (0%)**. All 3 droppers never transmitted anything, so they are in no observer's table.
  - **p = 0.75: 58/172 (33.7%)**: 47 via O=U, 58 via O≠U. Unobservable: never heard 7 (4.1%); only stale entries 104 (60.5%; freshest entry 89–639 s, median 181 s; only 28 within 120 s); fails the eligibility estimate 3 (1.7%); no observer in hearing range 0.
  - EAQTE exclusion removes none.
- **D2:** MATCH is 100% FWD_TX in every run. OTHER-UP is 100% DIFF_UP. Silent breakdown below.
- **D3, silence vs ground truth** (p = 0.75):
  - 3,679 valid silent opportunities; **209 DROP (5.7%) → false-blame rate 94.3%**.
  - Unique (X, c): 58/784 DROP (7.4%) → 92.6%.
  - Malicious candidates only: 65.4% (O≠U) and 67.3% (O=U) of silences are not DROP (DIFF_UP).
  - Silent makeup: NORX 1368 (37%), DIFF_UP 1177 (32%), FWD_TX unheard by O 720 (20%), DROP 209, INELIG 101, SUPPRESS 93, OUTPIPE 11.
  - All 209 DROP silences had predicted rank 1.
  - Clean and p = 1.0 runs: 0 DROP among silences (3,865 and 2,492 silent opportunities).
- **D4, recovered upstream vs custody tag:**
  - Position level: **100%** agreement (13,267 / 11,344 / 11,166 heard responses).
  - Identity resolvable by O: 86–91% agree, 9–14% unresolved (O never decoded the upstream copy), **0 disagree**.
- **D5, EAQTE exclusion:** **0** opportunities excluded in all runs (EE p1 ≈ 0.71). The C++ gate also froze 0 times (min C++ EE 0.628).
  - Analytically: var(p) ≤ 1/4, so CCQ ≥ 0.755·p. With Eb/N0 = 40 dB, p(1000 m) = 0.937, so **EE ≥ 0.354 for every in-range neighbour even with SS = 0**. A freeze needs a neighbour beyond ~1480 m, which range propagation now rules out.
  - This depends on Eb/N0, which the paper leaves unspecified.
- **Relay counts** per (packet, upstream copy), sizes 1/2/3:
  - clean 614/50/285; p = 1.0 546/99/311; p = 0.75 557/90/306.
  - In every group of size 2 or 3, all members decided with n = 1 (no duplicate heard before their own timer expired).
  - Accounting observation only.

### E-30 — Archiving Stage C/D artifacts after the scratch loss (2026-10-03)
- **Loss:** a WSL restart wiped the session scratch directory (scripts, `stageD_tables.txt`, runs, patch backups). No checksums of the original scripts had been taken.
- **Code unchanged since Stage C:** sources last modified 01:49:46; library `f9880f3d…` and scenario binary `54e444ed…` built 01:50:21 / 01:50:35.
- **Scripts rebuilt** exactly from the session record into `analysis/`: `d_common.py`, `d_recovery.py`, `d_accounting.py`, `v23.py`, `c_compare.py`, `runargs.sh`, `cmp_runs.py`.
- **Runs regenerated** with the same binary into `~/uwsn-runs/stageCD_seed1/` (persistent, outside the repo): `c1_tq`, `c_tq_a`, `c_smoke`, `d_p100`, `d_p075`. Headline counts match E-24..E-27.
- **Identity check:** the rebuilt scripts' outputs (`analysis/stageD_tables.txt`, `stageD_recovery.txt`, `stageC_v23.txt`, `stageC_compare.txt`) are **identical** under `diff` to the outputs printed before the restart (transcribed to `~/uwsn-runs/stageCD_seed1/expected_from_transcript/`).
- This is a functional identity check, not a checksum of the original files.

---

## 2026-10-04

### E-31 — `[RXHDR]` receiver-side decoded-header logging: validation (decision D-15)
- **Purpose:** before Stage E, replace the Stage D offline header rebuild, which used simulator ground truth, with the header values each receiver actually decoded. Logging only.
- **Code:**
  - aqua-sim-ng commit `41c67c3`: 8 inserted lines in `AquaSimTrustQVBF::Recv`, after `packet->PeekHeader (vbh)` on the received-packet branch.
  - `.cc` md5 `953629a5…`; library `871c50fc…`; scenario binary unchanged (`54e444ed…`).
  - Build: only the known `-Wreorder` warnings.
- **Runs:** seed/run 1, DEVELOPMENT/DIAGNOSTIC.
  - The three Stage D configurations (`c_tq_a`, `d_p100`, `d_p075`; E-24/E-27 arguments) were rerun into `~/uwsn-runs/rxhdr_seed1/` (outside the repo, not archived).
  - Compared with `~/uwsn-runs/stageCD_seed1/`.
- **Behaviour unchanged:**
  - energy, mobility, trust, observed, meta, stdout: byte-identical;
  - stderr: identical after removing `[RXHDR]` lines;
  - trace: 0 differing records after masking `token=`, `ts=`, `range=`.
- **Trace defect (pre-existing, Aqua-Sim-NG):** VBHeader `token`, `ts` and `range` are uninitialised.
  - The patch moved the stack garbage in `token` (30 → 0 / 2799601 / 4083687). `ts` also differs in 25 records per attacker run.
  - No code reads the token. These fields are masked permanently (D-16) and not fixed.
- **Coverage:** `[RXHDR]` lines = trace `r` records, one-to-one (26303 / 26180 / 26106).
- **Decoded values:**
  - vs the printed trace: 0 mismatches beyond 6-digit print resolution.
  - vs the Stage D rebuild: 0 f and 0 d mismatches on all non-ambiguous transmissions. The 34–40 ambiguous transmissions per run have mismatches of at most 0.30 m, which cannot change any MATCH/OTHER-UP outcome.
  - Upstream recovery from the decoded values alone: **max 0.601 m**, median 0.300 m. This reproduces E-28, now without the ground-truth upstream that the Stage D rebuild used.
- **Archive:** `analysis/stageE/rxhdr_validation/` (original scripts and outputs) and `analysis/stageE/README.md`.
- **Status:** PASS; accepted as the final D1 change. Stage E (O1/O2, E1) not started.
