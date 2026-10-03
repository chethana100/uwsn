# Stage D — Observable-evidence accounting in corrected HH-VBF

Seed/run 1, **development/diagnostic only, not an evaluation**. Recorded 2026-10-03.
Full context: `../PROJECT_HANDOFF.md`, `../EXPERIMENT_LOG.md` (E-22 to E-29), `../RESEARCH_DECISIONS.md`.

## 1. Provenance of the files in this directory

The original scripts and outputs lived in a temporary scratch directory, which a WSL restart wiped on 2026-10-03, after Stage D but before this archive was made. Two consequences:

- **The scripts here are exact rebuilds.** Each was written during the session, either in full or as an original plus small recorded edits, and is reproduced from that record.
- **No checksum of the original files exists.** None was taken before the loss.

**How identity was established instead.**
1. The simulator code and binaries are unchanged since Stage C. The source files were last modified at 01:49:46 and the binaries built at 01:50:21 / 01:50:35 on 2026-10-03; their checksums are in §2.
2. The five seed-1 runs were regenerated with that binary into `~/uwsn-runs/stageCD_seed1/` (outside the repo, persistent).
3. The rebuilt scripts were re-run on those runs.

All four outputs below are **identical, character for character,** to the outputs these scripts printed before the restart. The reference copies, transcribed from that record, are in `~/uwsn-runs/stageCD_seed1/expected_from_transcript/`. The headline counts in the regenerated runs also match exactly.

| File | What it is |
|---|---|
| `stageD_tables.txt` | Stage D five diagnostics + relay counts (`d_accounting.py`) |
| `stageD_recovery.txt` | Upstream-position recovery validation (`d_recovery.py`) |
| `stageC_v23.txt` | Stage C V2/V3 checks (`v23.py`) |
| `stageC_compare.txt` | Stage C forwarding change, legacy vs corrected (`c_compare.py`) |
| `d_common.py` | Shared loader. Separates ORACLE fields from OBSERVABLE fields; rebuilds the exact header f and d |
| `d_recovery.py`, `d_accounting.py` | Stage D scripts |
| `v23.py`, `c_compare.py` | Stage C scripts |
| `runargs.sh`, `cmp_runs.py` | Run wrapper; run-to-run comparison used in Stages A2–C |

## 2. Code state used

- Repo HEAD `370d2e6`, aqua-sim-ng submodule `fa2e87d`, both **plus uncommitted working-tree changes** from Stages DIAG, A1, A2, B and C.

| File | MD5 |
|---|---|
| `src/aqua-sim-ng/model/aqua-sim-routing-trustq-vbf.cc` | `ace79178175d4d7394153bd9946bc080` |
| `src/aqua-sim-ng/model/aqua-sim-routing-trustq-vbf.h` | `08f66365ba28df29e47705784743fdba` |
| `scratch/uwsn-trustq-attack.cc` | `aeb769cfd7ce0b69d374681187a245d9` |
| `scratch/mcm-mobility-model.h` | `77d2da1375e51975da2679fed2573b92` |
| `build/lib/libns3.41-aqua-sim-ng-default.so` | `f9880f3dcc05dfb49c42146cae2e15e8` |
| `build/scratch/ns3.41-uwsn-trustq-attack-default` | `54e444ed2ade8baf1c5fc3f54be5ad36` |

- **Stage D made no C++ changes.** It is offline analysis of simulator outputs only.

## 3. Configuration (corrected HH-VBF baseline)

- Routing: `AquaSimTrustQVBF`, HopByHop = 1, W = 400 m, R = 1000 m.
- **`PriorityScale = 0`** (HH-VBF baseline; hold ranking = α′ hold time). `ObservedTrustWeight = 0`.
- **Range propagation:** `AquaSimRangePropagation`. No routing-layer `RX_RANGE_M`.
- **Published hold time:** T = √α′·T_delay + (R − d)/v₀, with α′ = (R − d cosθ)/R (HH-VBF Def. 2), T_delay = 1.0 s (Aqua-Sim-NG value), v₀ = 1500 m/s.
- **Self-adaptation thresholds:** still use the Aqua-Sim-NG α = p/W + (R − d cosθ)/R (1.5; 1.5/2^(n−1)). This is a documented deviation from the paper.
- Sink fixed at (1500, 1500, 0). MCM on the other 99 nodes. Pinned MAC/routing RNG streams.
- **Seed / run = 1** for every run below.

| Run | Command (`analysis/runargs.sh <outdir> …`) |
|---|---|
| `c_tq_a` (clean) | `--run=1 --routing=trustq --priorityScale=0` |
| `d_p100` | `--run=1 --routing=trustq --priorityScale=0 --attackerFraction=0.2 --dropProbability=1.0` |
| `d_p075` | `--run=1 --routing=trustq --priorityScale=0 --attackerFraction=0.2 --dropProbability=0.75` |
| `c1_tq` (Stage C legacy control) | `c_tq_a` arguments + `--ns3::AquaSimTrustQVBF::PaperHoldTime=false --ns3::AquaSimTrustQVBF::PaperDesirableness=false` |
| `c_smoke` (Stage C, PS 0.2) | `--run=1 --attackerFraction=0.2 --dropProbability=0.75` |

Reproduce from the run directory:
```
python3 analysis/d_accounting.py c_tq_a d_p100 d_p075
python3 analysis/d_recovery.py c_tq_a d_p100 d_p075
python3 analysis/v23.py c_tq_a
python3 analysis/c_compare.py c1_tq c_tq_a
```

## 4. ε = 25 m and its validation (`stageD_recovery.txt`)

- The recovered upstream position is f_X − d_X, both decoded from X's on-air header.
- Header values were rebuilt exactly: positions rounded to the millimetre by `(uint32)(v*1000+0.5)`, and d serialized with x86 truncate-and-wrap.
- The rebuild matches the printed trace in **100%** of rebuildable transmissions (0 f mismatches, 0 d mismatches). The trace's 6-digit printing is too coarse to recover d directly: about ±5 m for wrapped values.
- **Recovery error: max 0.601 m**, median 0.30 m. This is the relay's own MCM drift between reception and MACprepare.
- **Nearest other transmitter** of the same packet to the recovered position: **min 136.1 m**.
- 0 ambiguous at 25 m.
- Acceptance rule stated before running: max error ≤ 12.5 m → **ACCEPT**.

## 5. Definitions (fixed before results)

- **Opportunity (O, X, c = (U, P))**, built only from information O has:
  - **Source event:** O decodes U's copy of P, or O itself transmits P (O = U).
  - **X is a candidate if:**
    - it is in O's table (positions from copies O decoded);
    - it was last heard ≤ 60 s ago;
    - it is not O, U, the sink, or P's source.
  - **Eligibility,** judged from X's last-known position: inside range of f_U, inside the pipe (≤ W), and Aqua-Sim α ≤ 1.5 (the single-copy case).
  - **Valid observable opportunity:** eligible, and O within R of X (O could hear X's response).
  - α′ hold time is used **only** to rank candidates.
- **Outcomes (observable):**
  - MATCH: O decodes X's copy and the recovered upstream is within ε of f_U.
  - OTHER-UP: different upstream; **excluded, never blamed**.
  - SILENT: O never decodes X's copy.
- **Ground truth (oracle):** X's `[DECISION]` for P. Same upstream → FWD_TX / MAC_GIVEUP / DROP / SUPPRESS / INELIG / MAXNBR / OUTPIPE. Different upstream → DIFF_UP. None → NORX.
- **Custody tag:** reference only, never evidence. Its prev equals `[DECISION] up` on every `[VERDICT] CREDIT` line (5145 / 5595 / 5241, 0 different).
- **EAQTE exclusion:** EE = 0.5·CCQ + 0.5·SS < 0.3 computed by O for X (paper Eqs. 6–10, 13, 18, 25–26; f 25 kHz, k 1.5, Eb/N0 40 dB, 640 bits). p-history = last 10 samples per (O, X) at opportunity events.

## 6. The five diagnostics and results (`stageD_tables.txt`)

1. **DROP observability** (≥ 1 valid observable opportunity):
   - **p = 1.0: 0/218 (0%)**. The 3 droppers never transmitted anything.
   - **p = 0.75: 58/172 (33.7%).** 104 (60.5%) lost only to stale entries: the freshest was 89–639 s old (median 181 s).
2. **Outcome × ground-truth cross-tab:** split honest / malicious × O = U / O ≠ U.
   - MATCH = 100% FWD_TX and OTHER-UP = 100% DIFF_UP, in every run.
3. **False-blame rate** among silent opportunities (p = 0.75):
   - 3,679 silent, **209 DROP (5.7%) → 94.3%** not drops. Unique (X, c): 58/784 (7.4%).
   - Silent makeup: NORX 37%, DIFF_UP 32%, FWD_TX unheard 20%, DROP 5.7%, INELIG/SUPPRESS/OUTPIPE rest.
   - Clean and p = 1.0: 0 drops among silences.
4. **Recovered upstream vs custody tag:**
   - 100% agreement at position level.
   - At identity level: 86–91% agree, 9–14% unresolved (O never decoded the upstream copy), **0 disagree**.
5. **EAQTE exclusion:** **0** opportunities in every run (EE p1 ≈ 0.71); the C++ gate froze 0 times.
   - Analytically, CCQ ≥ (1 − tanh ¼)·p and p(1000 m) = 0.937, so EE ≥ 0.354 for any in-range neighbour.
   - This depends on Eb/N0, which the paper leaves unspecified.

- **Relay counts** per upstream copy (sizes 1/2/3): clean 614/50/285; p = 1.0 546/99/311; p = 0.75 557/90/306. Every member of a 2- or 3-relay group decided with no duplicate heard before its timer.
- **Accounting observation only.**

## 7. Limitations

- One seed, one topology, three droppers per run, a single attacker model (selective drop).
- Observer eligibility uses last-known positions. The 60 s freshness limit (the C++ neighbour-table value) and ε were fixed in advance.
- NORX mixes collision/half-duplex losses with estimation error. It is not decomposed further.
- These are **observability diagnostics, not security or performance claims**. No detection rate, AUC or PDR conclusion follows from them.
