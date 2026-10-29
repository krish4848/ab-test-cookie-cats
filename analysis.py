"""Cookie Cats A/B test analysis: gate_30 (control) vs gate_40 (treatment).

Usage: python3 -I analysis.py <cookie_cats.csv> <metrics.sql> <out_dir>
Fixed seed, so every number in the README and memo is reproducible.
"""
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import (
    confint_proportions_2indep,
    proportion_effectsize,
    proportions_ztest,
)

SEED = 42
N_BOOT_PROP = 20_000
N_BOOT_MEAN = 5_000
ALPHA = 0.05

csv_path, sql_path, out_dir = map(Path, sys.argv[1:4])
out_dir.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(SEED)

df = pd.read_csv(csv_path)
df["retention_1"] = df["retention_1"].astype(int)
df["retention_7"] = df["retention_7"].astype(int)

res = {}

# ---------------------------------------------------------------- SQL layer
con = sqlite3.connect(":memory:")
df.to_sql("players", con, index=False)
sql_text = "\n".join(
    line.split("--")[0] for line in sql_path.read_text().splitlines())
queries = [q.strip() for q in sql_text.split(";") if "SELECT" in q]
sql_out = {}
for i, q in enumerate(queries, 1):
    sql_out[f"Q{i}"] = pd.read_sql_query(q, con)
    print(f"--- SQL Q{i} ---")
    print(sql_out[f"Q{i}"].to_string(index=False))
res["sql"] = {k: v.to_dict("records") for k, v in sql_out.items()}

ctrl = df[df.version == "gate_30"]
trt = df[df.version == "gate_40"]
n_c, n_t = len(ctrl), len(trt)

# ------------------------------------------------- 1. sample ratio mismatch
chi2, p_srm = stats.chisquare([n_c, n_t])
res["srm"] = {"n_gate_30": n_c, "n_gate_40": n_t,
              "share_gate_40": n_t / (n_c + n_t),
              "chi2": chi2, "p": p_srm}

# --------------------------------- 2. retention metrics (primary + secondary)
def prop_test(col, data_c, data_t, n_boot=N_BOOT_PROP):
    x = np.array([data_t[col].sum(), data_c[col].sum()])   # treatment first
    n = np.array([len(data_t), len(data_c)])
    p_t, p_c = x / n
    z, p = proportions_ztest(x, n)
    ci = confint_proportions_2indep(x[0], n[0], x[1], n[1], method="wald",
                                    compare="diff", alpha=ALPHA)
    # Parametric bootstrap == nonparametric bootstrap for Bernoulli outcomes
    bt = rng.binomial(n[0], p_t, n_boot) / n[0]
    bc = rng.binomial(n[1], p_c, n_boot) / n[1]
    d_boot = bt - bc
    rel_boot = d_boot / bc
    return {
        "p_gate_30": p_c, "p_gate_40": p_t,
        "diff_pp": (p_t - p_c) * 100,
        "diff_ci95_wald_pp": [ci[0] * 100, ci[1] * 100],
        "diff_ci95_boot_pp": list(np.percentile(d_boot, [2.5, 97.5]) * 100),
        "rel_change_pct": (p_t / p_c - 1) * 100,
        "rel_ci95_boot_pct": list(np.percentile(rel_boot, [2.5, 97.5]) * 100),
        "z": z, "p_raw": p,
    }

ret = {"retention_7": prop_test("retention_7", ctrl, trt),
       "retention_1": prop_test("retention_1", ctrl, trt)}
# Holm correction across the two retention tests
reject, p_adj, _, _ = multipletests(
    [ret["retention_7"]["p_raw"], ret["retention_1"]["p_raw"]],
    alpha=ALPHA, method="holm")
for (k, v), pa, rj in zip(ret.items(), p_adj, reject):
    v["p_holm"] = pa
    v["significant_after_holm"] = bool(rj)
res["retention"] = ret

# ---------------------------------------------- 3. engagement (rounds played)
def boot_mean_diff(a, b, n_boot=N_BOOT_MEAN):
    a, b = a.to_numpy(), b.to_numpy()
    d = np.empty(n_boot)
    for i in range(n_boot):
        d[i] = rng.choice(b, len(b)).mean() - rng.choice(a, len(a)).mean()
    return list(np.percentile(d, [2.5, 97.5]))

mw = stats.mannwhitneyu(trt.sum_gamerounds, ctrl.sum_gamerounds,
                        alternative="two-sided")
eng = {
    "mean_gate_30": ctrl.sum_gamerounds.mean(),
    "mean_gate_40": trt.sum_gamerounds.mean(),
    "median_gate_30": ctrl.sum_gamerounds.median(),
    "median_gate_40": trt.sum_gamerounds.median(),
    "mean_diff": trt.sum_gamerounds.mean() - ctrl.sum_gamerounds.mean(),
    "mean_diff_boot_ci95": boot_mean_diff(ctrl.sum_gamerounds, trt.sum_gamerounds),
    "mannwhitney_p": mw.pvalue,
    "prob_superiority_gate_40": mw.statistic / (n_c * n_t),
}
# sensitivity: drop the single extreme value (49,854 rounds, gate_30)
mx = df.sum_gamerounds.idxmax()
df_no = df.drop(index=mx)
c2, t2 = df_no[df_no.version == "gate_30"], df_no[df_no.version == "gate_40"]
eng["max_rounds_user"] = {"rounds": int(df.loc[mx, "sum_gamerounds"]),
                          "version": df.loc[mx, "version"]}
eng["without_outlier"] = {
    "mean_gate_30": c2.sum_gamerounds.mean(),
    "mean_gate_40": t2.sum_gamerounds.mean(),
    "mean_diff": t2.sum_gamerounds.mean() - c2.sum_gamerounds.mean(),
    "mean_diff_boot_ci95": boot_mean_diff(c2.sum_gamerounds, t2.sum_gamerounds),
}
res["engagement"] = eng

# ----------------------------------------------------- 4. power / MDE
def mde_pp(p_base, n1, ratio, power=0.8):
    """Smallest absolute drop (pp) detectable at given power, two-sided alpha."""
    h = NormalIndPower().solve_power(nobs1=n1, alpha=ALPHA, power=power,
                                     ratio=ratio, alternative="two-sided")
    p_alt = np.sin(np.arcsin(np.sqrt(p_base)) - h / 2) ** 2
    return (p_base - p_alt) * 100

def n_needed(p_base, drop_pp, power=0.8):
    es = proportion_effectsize(p_base, p_base - drop_pp / 100)
    return NormalIndPower().solve_power(effect_size=es, alpha=ALPHA,
                                        power=power, ratio=1.0)

p7, p1 = ret["retention_7"]["p_gate_30"], ret["retention_1"]["p_gate_30"]
ratio = n_t / n_c
res["power"] = {
    "mde_pp_retention_7_80pct": mde_pp(p7, n_c, ratio),
    "mde_pp_retention_1_80pct": mde_pp(p1, n_c, ratio),
    "n_per_arm_for_0.5pp_drop_d7": n_needed(p7, 0.5),
    "n_per_arm_for_1.0pp_drop_d7": n_needed(p7, 1.0),
    "n_per_arm_for_0.25pp_drop_d7": n_needed(p7, 0.25),
}

# ------------------------------------ 5. sensitivity: exclude zero-round users
nz = df[df.sum_gamerounds > 0]
res["sensitivity_exclude_zero_round_users"] = {
    "n_excluded": int((df.sum_gamerounds == 0).sum()),
    "retention_7": prop_test("retention_7", nz[nz.version == "gate_30"],
                             nz[nz.version == "gate_40"], n_boot=2000),
    "retention_1": prop_test("retention_1", nz[nz.version == "gate_30"],
                             nz[nz.version == "gate_40"], n_boot=2000),
}

# ----------------------- 6. exploratory: players likely to have hit the gate
# sum_gamerounds is measured AFTER assignment and can itself be affected by the
# treatment, so conditioning on it is biased. Direction-of-effect only.
ex = df[df.sum_gamerounds >= 30]
res["exploratory_rounds_ge_30"] = {
    "n_gate_30": int((ex.version == "gate_30").sum()),
    "n_gate_40": int((ex.version == "gate_40").sum()),
    "retention_7": prop_test("retention_7", ex[ex.version == "gate_30"],
                             ex[ex.version == "gate_40"], n_boot=2000),
}

# -------------------------------------------------- 7. CUPED applicability
res["cuped"] = {
    "applicable": False,
    "reason": ("CUPED needs a pre-experiment covariate correlated with the "
               "outcome. This dataset has none: sum_gamerounds covers the "
               "first 14 days after install, i.e. after assignment, so using "
               "it as a covariate would bias the estimate."),
}

def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return o

(out_dir / "results.json").write_text(json.dumps(clean(res), indent=2))
print("\n=== RESULTS ===")
print(json.dumps(clean(res), indent=2))
