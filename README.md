# Cookie Cats A/B test: did moving the first gate from level 30 to level 40 hurt retention?

An end-to-end analysis of a public mobile-game A/B test, written in SQL and Python. The goal is a decision a product team could act on, not just a p-value. Everything below is generated from `outputs/results.json` by the code in `src/`, with a fixed random seed.

**Result in one paragraph.** Moving the gate to level 40 lowered day-7 retention from 19.02% to 18.20%, a change of −0.82 percentage points (95% CI −1.33 to −0.31; −4.3% relative; Holm-adjusted p = 0.003). Day-1 retention also moved down (−0.59 pp) but not significantly, and there is no reliable change in rounds played. **Recommendation: keep the gate at level 30.** Two caveats matter: the arms differ in size more than chance usually produces (sample-ratio check p = 0.009), and the dataset has no revenue data, so the gate's monetization effect is unmeasured.

![Retention effect](outputs/fig1_retention_effect.png)

*Figure 1. Difference in retention (gate_40 minus gate_30) with 95% confidence intervals. Blue: all players. Gray: excluding the 3,994 players who played 0 rounds. Day-7 is clearly below zero, and day-1 straddles zero.*

## Design

| | |
|---|---|
| Experiment | First gate in the game moved from level 30 (control, `gate_30`) to level 40 (treatment, `gate_40`) |
| Data | 90,189 players, one row each: `version`, `sum_gamerounds` (rounds played in the first 14 days after install), `retention_1`, `retention_7` (returned on day 1 / day 7) |
| Primary metric | Day-7 retention |
| Secondary metrics | Day-1 retention. Rounds played is reported as descriptive only, because it is measured after assignment and the gate can affect it. |
| Tests | Two-proportion z-test for retention, Wald and bootstrap CIs on the difference, Holm correction across the two retention metrics. Mann-Whitney U and bootstrap on rounds played. |

**Honesty note on metric choice.** I chose day-7 retention as the primary metric because it is the harder-to-move, longer-horizon signal, but I had read published summaries of this dataset before running anything. The choice was not blind and should not be read as a pre-registered plan.

## Results

| Metric | gate_30 | gate_40 | Difference (95% CI) | Relative change | p-value |
|---|---|---|---|---|---|
| Day-7 retention (primary) | 19.02% | 18.20% | −0.82 pp (−1.33 to −0.31) | −4.3% (−6.9 to −1.6) | 0.002 raw, 0.003 Holm |
| Day-1 retention | 44.82% | 44.23% | −0.59 pp (−1.24 to +0.06) | −1.3% (−2.8 to +0.1) | 0.074 raw, 0.074 Holm |
| Mean rounds played | 52.46 | 51.30 | −1.16 (−4.00 to +0.96, bootstrap) | n/a | Mann-Whitney 0.050 |

Bootstrap and Wald intervals for the retention differences agree to the second decimal (day-7 bootstrap: −1.33 to −0.31). The medians for rounds played are 17 (gate_30) and 16 (gate_40).

## Checks and caveats

1. **Sample-ratio mismatch.** The arms have 44,700 and 45,489 players, which is 50.4% in treatment against an expected 50%. A chi-squared test gives p = 0.009. That is below 0.01 but above the 0.001 threshold some teams use for automatic alarms. I treat it as a flag, not proof of a broken experiment: the imbalance is small, but nothing in the data can rule out an assignment or logging problem, and the dataset documentation does not describe how players were assigned. If assignment was not random, the causal reading of the retention gap is weaker. A real team would audit the assignment pipeline before acting.
2. **Power.** With these arm sizes, 80% power and a two-sided 5% test, the smallest detectable change is about 0.73 pp for day-7 retention and 0.93 pp for day-1. The observed day-7 effect (−0.82 pp) sits just above that line, so it may be somewhat overstated, since significant effects near the detection limit tend to be. The observed day-1 effect (−0.59 pp) is below the day-1 limit, so the day-1 test could not reliably detect an effect that size: "not significant" there does not mean "no effect". Detecting a 0.5 pp day-7 change would take roughly 96,000 players per arm.
3. **One extreme outlier.** A single gate_30 player logged 49,854 rounds. With that player the mean difference in rounds is −1.16. Without that player it is −0.04 (−1.39 to +1.27). The apparent engagement gap is that one player. The Mann-Whitney test, which is robust to outliers, gives p = 0.050, borderline and not significant at 5%.
4. **Zero-round players.** 3,994 players installed but never played a round. Excluding them leaves the day-7 result essentially unchanged (−0.81 pp, CI −1.34 to −0.28), and day-1 stays non-significant (−0.54 pp, CI −1.20 to +0.13).
5. **Exploratory split by engagement (Figure 2).** Only players who reach the gate can be affected by it, so I looked at retention by rounds played. This is descriptive only, because rounds played is measured after assignment and may itself be changed by the gate, which biases any comparison conditioned on it. Among players with 30 or more rounds (16,656 vs 16,613), day-7 retention is 43.9% vs 43.0% (−0.87 pp, CI −1.94 to +0.19). The direction matches the main result but the interval includes zero. I did not run formal tests on the buckets.
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
