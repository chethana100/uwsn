# Stage E — pre-implementation artifacts

Recorded 2026-10-04. Seed/run 1 only, **development/diagnostic validation, not an evaluation**.
Decisions: `../../RESEARCH_DECISIONS.md` D-13 to D-16. Log: `../../EXPERIMENT_LOG.md` E-31.

Stage E itself (O1/O2, E1–E5) has **not** been implemented or run. This directory holds only:

1. the validation of the approved logging-only `[RXHDR]` patch (decision D1(ii));
2. the arithmetic behind the EAQTE Eb/N0 grid landmarks.

Arm labels used for Stage E (mandatory): **Arm 0** plain HH-VBF; **Arm A** observer-based trust, no environmental gate; **Arm B** observer-based trust + EAQTE gate; **Arm C** observer-based trust + PACT.

## 1. `rxhdr_validation/` — receiver-side decoded-header logging (D1(ii))

**What changed.** aqua-sim-ng submodule commit `41c67c3`: 8 inserted lines in `AquaSimTrustQVBF::Recv`, on the received-packet branch, immediately after the existing `packet->PeekHeader (vbh)`. Each received copy logs:

```
[RXHDR] node=<receiver> tx=<forwardAddr> src=<senderAddr> pk=<pkNum> f=x:y:z d=x:y:z tgt=x:y:z t=<time>
```

at 17 significant digits. `d` is logged exactly as decoded, i.e. still wrapped as uint32/1000; unwrap with v > 2147483.648 ⇒ v − 4294967.296. The line reads only the already-decoded header and changes no simulation behaviour.

**Why.** The trace prints header values to 6 significant digits, so Stage D rebuilt f and d offline from simulator-side ground truth (true positions, `[HOLD]` times, `[DECISION] up`). With `[RXHDR]` the Stage E observer input is the decoded bytes themselves.

**Code state.**

| File | MD5 |
|---|---|
| `src/aqua-sim-ng/model/aqua-sim-routing-trustq-vbf.cc` | `953629a5e75c1bc7ae5352ba0fb015cd` |
| `build/lib/libns3.41-aqua-sim-ng-default.so` | `871c50fc90cc613513ce25211cc8e450` |
| `build/scratch/ns3.41-uwsn-trustq-attack-default` | `54e444ed2ade8baf1c5fc3f54be5ad36` (unchanged) |

**Runs.** The three Stage D configurations (`c_tq_a`, `d_p100`, `d_p075`; arguments in `../STAGE_D_README.md` §3) were rerun with the patched library into `~/uwsn-runs/rxhdr_seed1/`, outside the repo (181 MB, not archived), and compared with `~/uwsn-runs/stageCD_seed1/`.

**Results** (`validation_output.txt`, identical pattern in all three runs):

- **Behaviour unchanged.**
  - energy, mobility, trust, observed, meta, stdout: byte-identical;
  - stderr: identical after removing `[RXHDR]` lines;
  - trace: 0 differing records after masking `token=`, `ts=`, `range=`.
- **Trace masking is permanent.** VBHeader's constructor initialises only `m_messType`, so `m_token`, `m_ts` and `m_range` are serialized from uninitialised memory. This is a pre-existing Aqua-Sim-NG defect and is deliberately not fixed.
  - The patch moved the stack garbage in `token` (30 → 0 / 2799601 / 4083687). `ts` also differs in 25 records of each attacker run.
  - Nothing in VBF/TrustQVBF reads the token; `GetToken` has no caller in aqua-sim-ng.
  - **All behavioural trace comparisons mask token, ts and range from now on.**
- **Coverage.** `[RXHDR]` lines = trace `r` records, one-to-one (26303 / 26180 / 26106).
  - The trace `r` event fires in `AquaSimPhyCmn::SendPktUp`, which the signal cache calls only for packets with status RECEPTION. The broadcast MAC passes every such copy to routing `Recv`.
- **Agreement with the printed trace.** 0 component mismatches beyond 6-digit print resolution. All values lie on the mm grid. The target is always (1500, 1500, 0). Every receiver of a transmission decoded identical f, d.
- **Agreement with the Stage D reconstruction.**
  - Non-ambiguous transmissions (2476 / 2375 / 2397): 0 f and 0 d mismatches.
  - The 34–40 transmissions Stage D flagged ambiguous: 7 f and 15 d mismatches, at most 0.3005 m (one MCM second of drift). This cannot change any MATCH/OTHER-UP outcome (ε = 25 m, nearest other transmitter ≥ 136 m).
- **Upstream recovery from the decoded values alone:** max error 0.601 m, median 0.300 m, 0 above 25 m. This reproduces Stage D, and is now independent of the ground-truth upstream used in the Stage D rebuild.

**Files.**

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

## 2. `eaqte_operating_point/` — Eb/N0 landmark arithmetic

`ee_bound.py` mirrors `AquaSimTrustQVBF::TransmissionProbability` (EAQTE Eqs. 6–10) and evaluates it offline. Output: `ee_bound_output.txt`.

This is arithmetic only: no simulator run, no seed, no outcome data. It gives:

- **The EE bound.** EE ≥ 0.5·(1 − tanh ¼)·p(1000 m) = 0.3537 > ξ = 0.3 at the current 40 dB, so the gate is inert for every in-range neighbour.
- **The grid landmarks** at 1000 m (f = 25 kHz, m = 640 bits; k has no effect at exactly 1 km):

  | Eb/N0 | Condition for a freeze to become possible |
  |---|---|
  | 34.5 dB | SS = 0, var = ¼ (worst case) |
  | 31.1 dB | SS = 0, var = 0 |
  | 24.5 dB | SS = 0.5 (no-velocity default) |

- **A structural fact.** With the published ψ = 0.5 and ξ = 0.3, a freeze requires both SS < 0.6 and CCQ < 0.6.
- **A correction.** The handoff's historical values at 100 m — p = 0.913 at 20 dB and 0.057 at 5 dB — do not reproduce with the current formula, which gives 0.943 and 0.161.
