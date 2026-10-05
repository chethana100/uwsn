# Stage E — C-d evaluation framework

**Status:** adopted 2026-10-05 after the D4-5 stop. Frozen when committed. Decision record: `../../RESEARCH_DECISIONS.md` D-19.

Contents:
0. Status
1. Inherited from revision 4
2. P5: binning for Arms B and C
3. Judged populations and false-alarm denominators
4. Statistics (D-Cd-7)
5. Gate for proceeding past E1 (G1′)
6. G5: blind spot, Arm B vs Arm A
7. G6: PACT, Arm C vs Arm B
8. Allowed claims
9. Supersession of revision-4 rules
10. Execution order, gates and seeds
11. Limitations
12. Revision log

---

## 0. Status

- **Revision 4 remains frozen and unchanged** (`README.md`, commit `8a0ff2f`).
- **The V6-B / G1 failure is a permanent revision-4 result** (`../../EXPERIMENT_LOG.md` E-34): n_min is undefined in the full calibration and in all 10 folds. **C-d does not retroactively make G1 pass.**
- **C-d is a new evaluation framework** adopted after the D4-5 stop, as the outcome of the Option C discussion. It is **not** another calibration redesign aimed at 0.80 power; D4-5 stays in force.
- **No power guarantee (0.80 or any other) exists for any arm.**
- Attacker seeds stay sealed until C-d is frozen.

## 1. Inherited from revision 4, unchanged

- O1/O2 and the information boundary (`README.md` §5–§7).
- The decision statistic r_w = (K_w − E_w)/S_w, and n_eff = 0 when S_w = 0.
- The revision-4 Arm-A calibration `e1/e1_calibration_rev4.json` (md5 `0ca88a0e4c8fc56f63e6b44b496b65fd`): bins, ρ_A,b and τ_A,b.
- The 5% false-alarm level; the attacker configuration (p = 0.75; `README.md` §11); the Eb/N0 grid and regimes (§10).
- S1/S2; the PACT formula and leakage rule (§8); the seed allocation (§4).
- G2, G2b, G3, G4 and G5(a) as frozen, except where §9 below states otherwise.

## 2. P5: binning for Arms B and C (resolved, option b)

For Arms B and C, bins are built per arm and per Eb/N0 grid point g, from the clean seeds 12–21, by the **frozen revision-4 §7 step-3 algorithm applied to that arm's own n_eff**. The algorithm's fixed parameters are unchanged:
- n_eff values processed in ascending order; pairs with equal n_eff never split;
- a bin closes at ≥ M = 200 pairs; an undersized last bin is merged into the one before;
- L₁ = n_ref = 14, and L_b = the smallest n_eff in bin b for b ≥ 2;
- half-open intervals [L_b, L_{b+1}), with the last bin [L_K, ∞).

Further details:
- Arm B's 0/1 weights make n_eff the integer count of unfrozen opportunities. Arm C's n_eff is real-valued; "equal" means bit-identical doubles.
- Thresholds: ρ_X,b by nearest rank on r_w, then the frozen PAVA procedure.
- Arm B is calibrated in E3; Arm C when E5 is prepared (leakage rule).
- **S_w = 0:** n_eff = 0 < n_ref, so the pair falls in no bin and is below the judging threshold.

## 3. Judged populations and false-alarm denominators

- **J1:** Arm A judges a pair iff n ≥ n_ref = 14, using the frozen revision-4 bins and τ_A,b. Arms B and C judge a pair iff n_eff ≥ 14, and flag it iff r_w > τ_X,b(g) for its P5 bin. This is fixed before attacker seeds are unsealed and is not selected from E1 power.
- **D-Cd-3, common Arm-A malicious denominator:** D_k is the set of active-malicious pairs (seed, O, X) judged in **Arm A**, for attacker run k. Every pair in D_k stays in the TDR denominator of Arms B and C. If the corresponding B/C pair has n_eff < 14 (including S_w = 0), it counts as **not detected**. Evidence removal therefore cannot raise TDR by shrinking the denominator.
- **D-Cd-6, per-arm honest denominators:** FA_X = (honest pairs flagged in Arm X) / (honest pairs judged in Arm X), each arm using its **own** judged honest set. Arm A's honest denominator is never used for Arms B or C. **Evidence coverage is reported separately** for each arm, attacker run and grid point: the judged honest count, and the ratio (honest pairs judged in X) / (honest pairs judged in A). FA and coverage are never combined into one figure.

## 4. Statistics (D-Cd-7)

### 4.1 Resampling

G5 (seeds 22–31) and G6 (seeds 41–50) each use one generator, NumPy PCG64 seed 12345, and B = 10,000 replicates. For replicate b = 1…B in order:
1. Draw seed positions with `integers(0, 10, 10)`.
2. For each drawn seed position, in order, draw node positions with `integers(0, 99, 99)` over that seed's fixed list of the 99 non-sink node addresses, sorted ascending.

**The same draws apply to every arm (A, B, C), every attacker run (M1, AM, PL) and every grid point in the family.** A pair (seed, O, X) enters a replicate with multiplicity = (count of its seed) × (count of X within that seed). Pairing is therefore kept within arms and across attacker runs. Every reported effect, interval and p-value in the family comes from these replicates.

Under S1, Arms A, B and C are offline replays of the same simulated trace for a given seed and attacker run. The attacker runs are separate simulations on the same seeds, scenario and RNG allocation, so their traces legitimately differ.

### 4.2 Effects in a replicate

- TDR_X\* = Σ_{i∈D_k} mult_i·flag_X(i) / Σ_{i∈D_k} mult_i.
- FA_X\* is defined the same way over Arm X's own judged honest set.
- Δ_BA\* = TDR_B\* − TDR_A\*; I\* = Δ_BA\*(k) − Δ_BA\*(PL); Δ_CB\* = TDR_C\* − TDR_B\*.

### 4.3 Approximate percentile-bootstrap p-values

Approximate percentile-bootstrap p-values (one-sided percentile-interval inversion): p = (1 + #{b : I\*_b ≥ 0}) / (B + 1) for H₁ I < 0, and p = (1 + #{b : Δ\*_CB,b ≤ 0}) / (B + 1) for H₁ Δ_CB > 0. They are not exact p-values. Their validity, and therefore the familywise-error control Holm provides, is approximate. It assumes:
- (A1) the percentile bootstrap is approximately valid for I and Δ_CB;
- (A2) seeds are independent units and nodes within seeds are exchangeable;
- (A3) the number of top-level clusters is adequate.

Each family has only 10 seeds, a stated limitation. The "+1" is a conservative finite-B guard. Equivalently, Holm rejects hypothesis (j) iff its one-sided (1 − α/(m − j + 1)) percentile bound excludes 0.

Ties at the null boundary (I\* = 0, Δ\*_CB = 0) count against H₁.

### 4.4 Holm correction (familywise α = 0.05)

- Sort the family's m p-values ascending. Ties are broken by a fixed order: attacker run M1 before AM, then grid point g ascending in Eb/N0.
- Find the smallest j with p_(j) > α/(m − j + 1). Reject hypotheses (1)…(j − 1), or all of them if no such j exists.
- **G5 family:** k ∈ {M1, AM} × every **active** grid point (frozen `README.md` §10 regimes).
- **G6 family:** the (k, g) where G5 qualified.
- A (k, g) that fails the precision minimum (§4.6) stays in its family with p = 1. It is never rejected and is reported as "not interpretable", so m is fixed before any test outcome is seen.
- Decisions use the Holm-adjusted p-values. The unadjusted one-sided 95% bounds from the same replicates are reported alongside.

### 4.5 Zero-denominator convention

No replicate is ever discarded.

- **Replicate effects:** if a replicate has zero resampled observations in any denominator a statistic needs, that statistic takes the value least favourable to the alternative or condition being assessed:
  - I\* = 0 if Σmult over D_k or over D_PL is 0 (counts toward #{I\* ≥ 0}, i.e. against H₁);
  - Δ_BA\* = 0 for supporting effects with a zero denominator;
  - Δ_CB\* = 0 if Σmult over D_k is 0 (counts toward #{Δ\* ≤ 0}, i.e. against H₁);
  - guardrail ΔFA\* = FA_C\* − FA_A\* = +1 if either arm's judged honest denominator is 0 (the largest possible value, against the guardrail passing).
- **G5(a) ratio in a replicate,** R\* = (z_m\*/N_m\*) / (z_h\*/N_h\*). N_m\* and N_h\* are the multiplicity-weighted malicious-drop and honest opportunity counts; z_m\* and z_h\* are the frozen (w = 0) counts among them:
  - if N_m\* = 0 or N_h\* = 0: R\* = 0;
  - if z_h\* = 0 and z_m\* > 0: R\* = +∞ (the exact limit of a positive rate over a zero rate);
  - if z_h\* = 0 and z_m\* = 0: R\* = 0 (an undefined 0/0 takes the least favourable value).
- **Percentiles when +∞ can occur:** G5(a)'s two-sided 95% percentile interval uses nearest-rank order statistics of the 10,000 R\* values sorted ascending, with +∞ sorted last. The lower endpoint is the 250th value (⌈0.025·B⌉); the upper endpoint is the 9,750th (⌈0.975·B⌉). The guardrail's one-sided 95% lower bound keeps the frozen V6-A rule (5th percentile, linear interpolation); no infinite values can occur there.
- **The observed data:** zero denominators in the observed data use the existing "not interpretable" outcome:
  - D_k or D_PL below the precision minimum: that (k, g) is not interpretable (p = 1);
  - N_m = 0 or N_h = 0 for G5(a): G5(a) is not interpretable, so G5 cannot qualify at that (k, g);
  - an arm's judged honest set empty: the guardrail is not interpretable, so G6 cannot hold at that (k, g).
- **Transparency:** the number of replicates in which a convention was applied is reported for each (k, g) and statistic.

### 4.6 Precision minimum (an interpretability requirement, not a power guarantee)

At least **43 judged active-malicious pairs and 10 distinct malicious nodes** in D_k, for every attacker run entering a test (for I, both k and PL). These are the existing G2 numbers, fixed before any attacker data existed (TDR 95% CI half-width ≤ 0.15).
- Below the minimum, that (k, g) is "not interpretable" (p = 1): reported descriptively, never a pass or a fail.
- There is no extension unless a new seed allocation is approved separately.
- No equivalence claims are made.

## 5. Gate for proceeding past E1 (G1′)

**G1′ = V1–V5, V7, V8, V3-a and V6-A all pass.** This holds already (E-32 to E-34). G1′ only permits the relative evaluation below; it is not G1, and G1 remains FAILED (V6-B).

## 6. G5: blind spot, Arm B vs Arm A (E4, seeds 22–31)

Notation: k ∈ {M1 = `AttackMode=1`, AM = AdversarialMotion}; PL is the matched plain control; g is an active grid point.

- **Supporting effects (descriptive):** Δ_BA(k, g) = TDR_B − TDR_A on D_k, for M1, AM and PL. A positive Δ_BA is reported descriptively only.
- **Primary estimand:** the blind-spot contrast **I(k, g) = Δ_BA(k, g) − Δ_BA(PL, g)**.
- **Primary hypothesis (one-sided):** H₀ I(k, g) ≥ 0 vs **H₁ I(k, g) < 0**.

**G5 qualifies at (k, g) only if all three hold:**
1. **Primary:** the Holm-adjusted test of H₁ I(k, g) < 0 rejects (§4.3–4.4).
2. **Mechanism check, G5(a) (required co-condition, not Holm-adjusted):** P(w = 0 | malicious-drop opportunity) / P(w = 0 | honest opportunity) > 1, **with the lower endpoint of its 95% interval greater than 1**. The interval is the two-sided 95% percentile bootstrap interval from the same replicates (§4.5).
3. The precision minimum (§4.6) is met for both k and PL.

The blind-spot claim depends on I, not merely on B < A. **E5 runs only at the (k, g) where G5 qualified.**

## 7. G6: PACT, Arm C vs Arm B (E5, seeds 41–50)

- **Primary:** Δ_CB(k, g) = TDR_C − TDR_B on D_k, at the (k, g) where G5 qualified. One-sided test of **H₁ Δ_CB(k, g) > 0**, Holm-adjusted (§4.3–4.4).
- **Guardrail (D-Cd-4, zero margin):** FA_C − FA_A must **not be significantly greater than 0**, i.e. its one-sided 95% lower bound (5th percentile, linear interpolation) is ≤ 0. Per-arm honest denominators (§3). Evaluated without Holm adjustment at each (k, g), because adjustment would make a guardrail easier to pass.
- **G6 holds at (k, g) only if** the primary test rejects, the guardrail holds, and the precision minimum is met.

## 8. Allowed claims

| Outcome | May claim | May not claim |
|---|---|---|
| G5 qualifies | "Against [k] at [g], the EAQTE gate produced a blind spot: a detection loss beyond the matched plain control of I (CI), with the mechanism check satisfied" | Absolute detection or power; generalisation to other topologies |
| G5 does not qualify | "No blind spot detected at the achieved precision"; a positive Δ_BA described only | "EAQTE improves detection"; "EAQTE fails" |
| G6 holds | "PACT recovered Δ_CB (CI) relative to the EAQTE gate, with no significant FA increase over Arm A" | PACT power; 0.80 detection; superiority over Arm A |
| G6 fails or is not interpretable | "No detectable PACT recovery at the achieved precision" | "PACT fails" |
| Any outcome | — | Any calibrated or guaranteed power for any arm; any n_min; "G1 passed"; per-pair detection adequacy |

## 9. Supersession of revision-4 rules

| Revision 4 (`README.md`) | C-d |
|---|---|
| §12 "If G1 fails … no later stage runs"; §11 E4 precondition "G1–G4 pass" | G1′ (§5). G1 stays failed. E4 runs only if G1′, G2, G2b, G3 and G4 pass |
| §7 step 4 and step 6, §9: n_min as the judging threshold | J1: judged iff n ≥ 14 (Arm A) or n_eff ≥ 14 (Arms B/C); plus D-Cd-3 |
| §13 P5 (open) | Resolved, §2 |
| False-alarm denominators per arm (unspecified) | D-Cd-6 (§3) |
| §12 G5(b) | Primary I < 0, one-sided, Holm; G5(a) a required co-condition with the directional lower-endpoint rule |
| §12 G6(a)/(b) | Δ_CB > 0, one-sided, Holm; zero-margin guardrail with per-arm denominators |
| New | Precision minimum and "not interpretable"; the §4 statistics framework, including the zero-denominator convention |

Everything not listed here is unchanged (§1).

## 10. Execution order, gates and seeds

1. **Freeze C-d** (this document plus D-19). Seeds 2–11 stay sealed until then.
2. **E2 (seeds 2–11; Arm A; naive attacker p = 0.75, plus p = 1.0 for the ceiling table only):** gates G2 and G2b. Their frozen failure conclusions are unchanged.
3. **E3 (clean seeds 12–21):** P5 bins and τ_B,b; gates G3 and G4. Frozen failure conclusions unchanged.
4. **E4 (seeds 22–31; Arms A and B; attacker runs M1, AM, PL), only if G1′, G2, G2b, G3 and G4 pass:** G5 (§6). If no (k, g) qualifies, E5 does not run and PACT is reported as moot.
5. **E5 (seeds 41–50), only at the (k, g) where G5 qualified:** τ_C,b calibrated on clean seeds first, then G6 (§7).

The order E2 → E3 → E4 → E5 is unchanged. Seed allocation is as frozen (D-14): seed 1 development only; seeds 32–40 unused.

## 11. Limitations

- With 10 seeds per family, bootstrap error rates are approximate; the direction of any error (from few clusters versus two-stage resampling) is not known.
- No power guarantee exists for any arm (revision-4 V6-B failure, E-34).
- The calibration and its development validation used clean seeds 12–21, which also informed revisions 3 and 4. The independent false-alarm assessment is G2b on seeds 2–11.
- Results apply to the simulated topologies and the declared attacker configuration only.

## 12. Revision log

| Date | Revision |
|---|---|
| 2026-10-05 | C-d adopted after the D4-5 stop: G1′; J1 (n_ref = 14); D-Cd-3; D-Cd-6; P5 option (b); G5 primary contrast I < 0 with G5(a) as a required co-condition (lower endpoint of its 95% interval > 1); G6 Δ_CB > 0 with the zero-margin guardrail; D-Cd-7 approximate percentile-bootstrap p-values with Holm (assumptions A1–A3); zero-denominator convention; precision minimum; execution order E2 → E3 → E4 → E5. Revision 4 and its G1/V6-B failure are unchanged |
