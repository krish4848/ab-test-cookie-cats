# Recommendation: keep the first gate at level 30

**To:** Product lead, Cookie Cats (hypothetical, portfolio exercise)
**From:** Krish Gada
**Date:** October 14, 2026

## Decision

Do not ship the change that moves the first gate from level 30 to level 40.

## Why

- **Day-7 retention fell.** 19.02% of players on gate_30 were still playing on day 7, against 18.20% on gate_40: a drop of 0.82 percentage points, or 4.3% of the retained base (95% CI 0.31 to 1.33 pp lower). It is significant after correcting for testing two retention metrics (Holm p = 0.003).
- **Nothing offsets it.** Day-1 retention is also lower (0.59 pp) but not significantly so, and there is no reliable difference in rounds played: the apparent gap in the average comes from a single player with 49,854 rounds.
- **The result is stable.** Bootstrap intervals match the standard ones, and dropping the 3,994 players who never played a round barely changes the day-7 result (−0.81 pp).

## How sure are we

- **Moderately.** The day-7 interval excludes zero, but the effect is close to the smallest size this test could detect (0.73 pp), so the true drop may be smaller than 0.82 pp.
- **There is a data-quality flag.** The arms are 44,700 and 45,489 players, a split that chance alone rarely produces (p = 0.009). The assignment process should be checked before this result is treated as final.
- **Revenue is missing.** The gate is also a purchase point. If gate_40 produced meaningfully more revenue, the decision could change, and this data cannot show it.

## Next steps

1. Audit how players were assigned and logged, to explain the 789-player imbalance.
2. Pull in-app purchase data for both groups and compare revenue per player alongside retention.
3. If other gate positions are worth testing, plan for roughly 96,000 players per arm to detect a 0.5 pp change in day-7 retention.

Full method, checks and code: see `README.md`.
