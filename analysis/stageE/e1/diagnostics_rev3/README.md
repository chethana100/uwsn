# Revision-3 design-basis diagnostics (provenance only)

These four scripts produced the diagnostics on which Stage E revision 3 was designed
(`../../README.md` §13, decisions R3-1 and R3-3). They are **provenance only**: they are not the
revision-3 calibration implementation, and they determine no threshold, bin or n_min.

- Inputs, read only: the revision-2 E1 outputs. That is the observer-side opportunity files
  `~/uwsn-runs/stageE/E1/run_N/e1_opportunities.csv` (N = 12–21, clean seeds), the revision-2 calibration
  file `../e1_calibration.json`, and, for `v3_diag.py`, the evaluation-only ground truth (`../truth.py`).
- **No attacker data, no simulation, no calibration.** Nothing is written except the `*_output.txt` files here.
- The scripts were first run from the session scratchpad on 2026-10-04. These are exact byte copies.
  They were rerun from this folder to capture their outputs, which match the values reported in the
  revision-3 proposal.
- `v6_diag2.py` is the version that produced the reported numbers. Its beta quantiles use NumPy sampling
  (`default_rng(1)`), because SciPy is not installed on this machine.
- The revision-2 diagnostics in `../diagnostics/` are unchanged.

| Script | Output | Diagnoses |
|---|---|---|
| `v6_diag.py` | `v6_diag_output.txt` | False alarms at the revision-2 τ_A by pair size; binomial vs observed variance (implied ρ); variance shares by seed, observer, neighbour and pair; per-seed shifts; residual silence by observer-visible geometry |
| `v6_diag2.py` | `v6_diag2_output.txt` | Persistence of a pair's silence propensity; the model-based power ceiling (~0.41, diagnostic only); effect of observer-visible covariates on ρ |
| `v6_diag3.py` | `v6_diag3_output.txt` | Additive observer and neighbour effects in pair-level excess variance (overfitting caveat: 929 effects fitted to 2,044 pairs) |
| `v3_diag.py` | `v3_diag_output.txt` | O1 classification margin (MATCH vs OTHER-UP distance to f_U) and spacing between transmitters of the same packet |
