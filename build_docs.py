"""Render README.md and memo.md from results.json so every number is generated, not typed.
Usage: python3 -I build_docs.py <results.json> <repo_root>
"""
import json
import sys
from pathlib import Path

res = json.loads(Path(sys.argv[1]).read_text())
root = Path(sys.argv[2])

M = "−"  # true minus sign


def s(x, d=2):
    """Signed number."""
    return f"{x:+.{d}f}".replace("-", M)


def pct(x, d=2):
    return f"{x * 100:.{d}f}%"


def ci(pair, d=2):
    return f"{s(pair[0], d)} to {s(pair[1], d)}"


r7, r1 = res["retention"]["retention_7"], res["retention"]["retention_1"]
eng, srm, pw = res["engagement"], res["srm"], res["power"]
z7 = res["sensitivity_exclude_zero_round_users"]["retention_7"]
z1 = res["sensitivity_exclude_zero_round_users"]["retention_1"]
ex = res["exploratory_rounds_ge_30"]["retention_7"]
n_all = srm["n_gate_30"] + srm["n_gate_40"]
n_excl = res["sensitivity_exclude_zero_round_users"]["n_excluded"]
out_rounds = eng["max_rounds_user"]["rounds"]


def p4(p):
    return f"{p:.4f}" if p < 0.001 else f"{p:.3f}"


readme = f"""# Cookie Cats A/B test: did moving the first gate from level 30 to level 40 hurt retention?

An end-to-end analysis of a public mobile-game A/B test, written in SQL and Python. The goal is a decision a product team could act on, not just a p-value. Everything below is generated from `outputs/results.json` by the code in `src/`, with a fixed random seed.

**Result in one paragraph.** Moving the gate to level 40 lowered day-7 retention from {pct(r7['p_gate_30'])} to {pct(r7['p_gate_40'])}, a change of {s(r7['diff_pp'])} percentage points (95% CI {ci(r7['diff_ci95_wald_pp'])}; {s(r7['rel_change_pct'], 1)}% relative; Holm-adjusted p = {p4(r7['p_holm'])}). Day-1 retention also moved down ({s(r1['diff_pp'])} pp) but not significantly, and there is no reliable change in rounds played. **Recommendation: keep the gate at level 30.** Two caveats matter: the arms differ in size more than chance usually produces (sample-ratio check p = {p4(srm['p'])}), and the dataset has no revenue data, so the gate's monetization effect is unmeasured.

![Retention effect](outputs/fig1_retention_effect.png)

*Figure 1. Difference in retention (gate_40 minus gate_30) with 95% confidence intervals. Blue: all players. Gray: excluding the {n_excl:,} players who played 0 rounds. Day-7 is clearly below zero, and day-1 straddles zero.*

## Design

| | |
|---|---|
| Experiment | First gate in the game moved from level 30 (control, `gate_30`) to level 40 (treatment, `gate_40`) |
| Data | {n_all:,} players, one row each: `version`, `sum_gamerounds` (rounds played in the first 14 days after install), `retention_1`, `retention_7` (returned on day 1 / day 7) |
| Primary metric | Day-7 retention |
| Secondary metrics | Day-1 retention. Rounds played is reported as descriptive only, because it is measured after assignment and the gate can affect it. |
| Tests | Two-proportion z-test for retention, Wald and bootstrap CIs on the difference, Holm correction across the two retention metrics. Mann-Whitney U and bootstrap on rounds played. |

**Honesty note on metric choice.** I chose day-7 retention as the primary metric because it is the harder-to-move, longer-horizon signal, but I had read published summaries of this dataset before running anything. The choice was not blind and should not be read as a pre-registered plan.

## Results

| Metric | gate_30 | gate_40 | Difference (95% CI) | Relative change | p-value |
|---|---|---|---|---|---|
| Day-7 retention (primary) | {pct(r7['p_gate_30'])} | {pct(r7['p_gate_40'])} | {s(r7['diff_pp'])} pp ({ci(r7['diff_ci95_wald_pp'])}) | {s(r7['rel_change_pct'], 1)}% ({ci(r7['rel_ci95_boot_pct'], 1)}) | {p4(r7['p_raw'])} raw, {p4(r7['p_holm'])} Holm |
| Day-1 retention | {pct(r1['p_gate_30'])} | {pct(r1['p_gate_40'])} | {s(r1['diff_pp'])} pp ({ci(r1['diff_ci95_wald_pp'])}) | {s(r1['rel_change_pct'], 1)}% ({ci(r1['rel_ci95_boot_pct'], 1)}) | {p4(r1['p_raw'])} raw, {p4(r1['p_holm'])} Holm |
| Mean rounds played | {eng['mean_gate_30']:.2f} | {eng['mean_gate_40']:.2f} | {s(eng['mean_diff'])} ({ci(eng['mean_diff_boot_ci95'])}, bootstrap) | n/a | Mann-Whitney {p4(eng['mannwhitney_p'])} |

Bootstrap and Wald intervals for the retention differences agree to the second decimal (day-7 bootstrap: {ci(r7['diff_ci95_boot_pp'])}). The medians for rounds played are {eng['median_gate_30']:.0f} (gate_30) and {eng['median_gate_40']:.0f} (gate_40).

## Checks and caveats

1. **Sample-ratio mismatch.** The arms have {srm['n_gate_30']:,} and {srm['n_gate_40']:,} players, which is {pct(srm['share_gate_40'], 1)} in treatment against an expected 50%. A chi-squared test gives p = {p4(srm['p'])}. That is below 0.01 but above the 0.001 threshold some teams use for automatic alarms. I treat it as a flag, not proof of a broken experiment: the imbalance is small, but nothing in the data can rule out an assignment or logging problem, and the dataset documentation does not describe how players were assigned. If assignment was not random, the causal reading of the retention gap is weaker. A real team would audit the assignment pipeline before acting.
2. **Power.** With these arm sizes, 80% power and a two-sided 5% test, the smallest detectable change is about {pw['mde_pp_retention_7_80pct']:.2f} pp for day-7 retention and {pw['mde_pp_retention_1_80pct']:.2f} pp for day-1. The observed day-7 effect ({s(r7['diff_pp'])} pp) sits just above that line, so it may be somewhat overstated, since significant effects near the detection limit tend to be. The observed day-1 effect ({s(r1['diff_pp'])} pp) is below the day-1 limit, so the day-1 test could not reliably detect an effect that size: "not significant" there does not mean "no effect". Detecting a 0.5 pp day-7 change would take roughly {round(pw['n_per_arm_for_0.5pp_drop_d7'], -3):,.0f} players per arm.
3. **One extreme outlier.** A single gate_30 player logged {out_rounds:,} rounds. With that player the mean difference in rounds is {s(eng['mean_diff'])}. Without that player it is {s(eng['without_outlier']['mean_diff'])} ({ci(eng['without_outlier']['mean_diff_boot_ci95'])}). The apparent engagement gap is that one player. The Mann-Whitney test, which is robust to outliers, gives p = {p4(eng['mannwhitney_p'])}, borderline and not significant at 5%.
4. **Zero-round players.** {n_excl:,} players installed but never played a round. Excluding them leaves the day-7 result essentially unchanged ({s(z7['diff_pp'])} pp, CI {ci(z7['diff_ci95_wald_pp'])}), and day-1 stays non-significant ({s(z1['diff_pp'])} pp, CI {ci(z1['diff_ci95_wald_pp'])}).
5. **Exploratory split by engagement (Figure 2).** Only players who reach the gate can be affected by it, so I looked at retention by rounds played. This is descriptive only, because rounds played is measured after assignment and may itself be changed by the gate, which biases any comparison conditioned on it. Among players with 30 or more rounds ({res['exploratory_rounds_ge_30']['n_gate_30']:,} vs {res['exploratory_rounds_ge_30']['n_gate_40']:,}), day-7 retention is {pct(ex['p_gate_30'], 1)} vs {pct(ex['p_gate_40'], 1)} ({s(ex['diff_pp'])} pp, CI {ci(ex['diff_ci95_wald_pp'])}). The direction matches the main result but the interval includes zero. I did not run formal tests on the buckets.
6. **CUPED was not applied, deliberately.** It needs a pre-experiment covariate correlated with the outcome. This dataset has none: `sum_gamerounds` covers the 14 days after install, so using it would bias the estimate. Variance reduction would be a natural step with pre-period data.
7. **No revenue.** The gate is a monetization lever, because players can pay to skip the wait. A decision to keep or move it should weigh the retention loss against purchase revenue, which this dataset cannot show.
8. **Why?** The data cannot say why an earlier gate would retain better. Hypotheses to test, not conclusions: forced breaks may slow player fatigue, or the wait may build a habit of returning.

![Retention by rounds played](outputs/fig2_retention_by_rounds.png)

*Figure 2. Day-7 retention by rounds played. Descriptive only (see caveat 5).*

## Recommendation

Keep the first gate at level 30. See [`memo.md`](memo.md) for the one-page decision memo, written as if for a product lead. This is a portfolio exercise on a public dataset, not a real business decision.

## Reproduce

```bash
pip install -r requirements.txt
bash src/download_data.sh   # fetches the public dataset into data/
bash run_all.sh             # SQL + analysis, charts, README, memo
```

Everything is seeded (`SEED = 42`), so reruns give identical numbers.

## Repo layout

| Path | What it is |
|---|---|
| `src/metrics.sql` | SQL for arm sizes, medians (window functions), retention funnel, engagement buckets, data-quality checks |
| `src/analysis.py` | Loads the data into SQLite, runs the SQL, then the statistical tests, power analysis and sensitivity checks |
| `src/make_charts.py` | Builds the two figures |
| `src/build_docs.py` | Generates this README and the memo from `outputs/results.json` |
| `outputs/` | `results.json` (all numbers), `analysis_log.txt`, figures |
| `memo.md` | One-page recommendation |

## Data

The public Cookie Cats A/B dataset, originally shared through Kaggle and DataCamp. `src/download_data.sh` pulls a copy from a public GitHub mirror. The CSV is not committed to this repo. Check the original source's license before redistributing it.
"""

memo = f"""# Recommendation: keep the first gate at level 30

**To:** Product lead, Cookie Cats (hypothetical, portfolio exercise)
**From:** Krish Gada
**Date:** October 14, 2026

## Decision

Do not ship the change that moves the first gate from level 30 to level 40.

## Why

- **Day-7 retention fell.** {pct(r7['p_gate_30'])} of players on gate_30 were still playing on day 7, against {pct(r7['p_gate_40'])} on gate_40: a drop of {abs(r7['diff_pp']):.2f} percentage points, or {abs(r7['rel_change_pct']):.1f}% of the retained base (95% CI {abs(r7['diff_ci95_wald_pp'][1]):.2f} to {abs(r7['diff_ci95_wald_pp'][0]):.2f} pp lower). It is significant after correcting for testing two retention metrics (Holm p = {p4(r7['p_holm'])}).
- **Nothing offsets it.** Day-1 retention is also lower ({abs(r1['diff_pp']):.2f} pp) but not significantly so, and there is no reliable difference in rounds played: the apparent gap in the average comes from a single player with {out_rounds:,} rounds.
- **The result is stable.** Bootstrap intervals match the standard ones, and dropping the {n_excl:,} players who never played a round barely changes the day-7 result ({s(z7['diff_pp'])} pp).

## How sure are we

- **Moderately.** The day-7 interval excludes zero, but the effect is close to the smallest size this test could detect ({pw['mde_pp_retention_7_80pct']:.2f} pp), so the true drop may be smaller than {abs(r7['diff_pp']):.2f} pp.
- **There is a data-quality flag.** The arms are {srm['n_gate_30']:,} and {srm['n_gate_40']:,} players, a split that chance alone rarely produces (p = {p4(srm['p'])}). The assignment process should be checked before this result is treated as final.
- **Revenue is missing.** The gate is also a purchase point. If gate_40 produced meaningfully more revenue, the decision could change, and this data cannot show it.

## Next steps

1. Audit how players were assigned and logged, to explain the {srm['n_gate_40'] - srm['n_gate_30']:,}-player imbalance.
2. Pull in-app purchase data for both groups and compare revenue per player alongside retention.
3. If other gate positions are worth testing, plan for roughly {round(pw['n_per_arm_for_0.5pp_drop_d7'], -3):,.0f} players per arm to detect a 0.5 pp change in day-7 retention.

Full method, checks and code: see `README.md`.
"""

(root / "README.md").write_text(readme)
(root / "memo.md").write_text(memo)
print("README.md and memo.md written")
