import duckdb
import numpy as np
import polars as pl
from sklearn.metrics import average_precision_score

COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]
FRACTIONS = np.geomspace(1e-4, 1e-2, 15).round(6).tolist()
RANKED = """SELECT date, y::INT AS y, count(*) OVER (PARTITION BY date) AS n,
    row_number() OVER (PARTITION BY date ORDER BY score DESC, hash(drive_id)) AS rk FROM s"""


def metrics(s: pl.DataFrame, k: int) -> dict:
    """PR-AUC over all rows; precision/recall of the top k per weekly snapshot, averaged."""
    p, r = duckdb.sql(f"""WITH r AS ({RANKED}), w AS (
        SELECT date, sum(y) FILTER (rk <= {k}) AS tp, least(max(n), {k}) AS picked,
               sum(y) AS pos FROM r GROUP BY date)
        SELECT avg(tp / picked), sum(tp) / sum(pos) FROM w""").fetchall()[0]
    return {
        "pr_auc": round(average_precision_score(s["y"], s["score"]), 4),
        f"precision_at_{k}": round(p, 4),
        f"recall_at_{k}": round(r, 4),
    }


def calibration(y: np.ndarray, p: np.ndarray) -> dict:
    """Brier score, expected vs observed failures, and observed rate by predicted decile."""
    order = np.argsort(p)
    deciles = [
        (round(float(p[i].mean()), 5), round(float(y[i].mean()), 5))
        for i in np.array_split(order, 10)
    ]
    return {
        "brier": round(float(np.mean((p - y) ** 2)), 6),
        "expected_failures": round(float(p.sum()), 1),
        "observed_failures": int(y.sum()),
        "deciles_predicted_vs_observed": deciles,
    }


def reference(df: pl.DataFrame, features: list[str]) -> dict:
    """Per-feature decile edges and bin shares (last bin = null) for drift checks."""
    ref = {}
    for f in features:
        col = df[f].cast(pl.Float64).to_numpy()
        edges = (
            np.unique(np.nanquantile(col, np.linspace(0.1, 0.9, 9)))
            if np.isfinite(col).any()
            else np.array([])
        )
        ref[f] = {"edges": edges.tolist(), "share": shares(col, edges).tolist()}
    return ref


def shares(col: np.ndarray, edges) -> np.ndarray:
    """Share of values per bin defined by edges, plus a final bin for nulls."""
    ok = np.isfinite(col)
    counts = np.bincount(np.digitize(col[ok], edges), minlength=len(edges) + 1)
    return np.append(counts, (~ok).sum()) / max(len(col), 1)


def psi(ref: dict, df: pl.DataFrame) -> dict[str, float]:
    """Population stability index of each feature in df versus the training reference."""
    out = {}
    for f, r in ref.items():
        e = np.clip(np.array(r["share"]), 1e-4, None)
        a = np.clip(shares(df[f].cast(pl.Float64).to_numpy(), r["edges"]), 1e-4, None)
        out[f] = round(float(np.sum((a - e) * np.log(a / e))), 4)
    return out


def cost_curve(s: pl.DataFrame) -> list[dict]:
    """Failures caught vs healthy drives pulled per week when pulling the top K% of drives."""
    rows = duckdb.sql(f"""WITH r AS ({RANKED}), f AS (SELECT unnest({FRACTIONS})::DOUBLE AS frac)
        SELECT frac, sum(y) / count(DISTINCT date)::DOUBLE, sum(1 - y) / count(DISTINCT date)::DOUBLE
        FROM r, f WHERE rk <= greatest(1, round(frac * n)) GROUP BY frac ORDER BY frac""")
    return [
        {"k_pct": f * 100, "failures_avoided": round(a, 2), "healthy_pulled": round(h, 2)}
        for f, a, h in rows.fetchall()
    ]


def plot(curves: dict[str, list[dict]], path) -> None:
    """Save the cost curves of all models as one PNG."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    fig, ax = plt.subplots(figsize=(7, 4.5), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    for (name, pts), color in zip(curves.items(), COLORS):
        x, y = [p["healthy_pulled"] for p in pts], [p["failures_avoided"] for p in pts]
        ax.plot(x, y, color=color, lw=2, marker="o", ms=4, label=name)
        ax.annotate(
            name,
            (x[-1], y[-1]),
            xytext=(4, 0),
            textcoords="offset points",
            color="#52514e",
            fontsize=9,
            va="center",
        )
    ax.set_xscale("symlog", linthresh=1)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xlabel("Healthy drives pulled per week", color="#52514e")
    ax.set_ylabel("Failures caught per week", color="#52514e")
    ax.set_title(
        "Cost curve: pulling the top 0.01%-1% riskiest drives each week",
        loc="left",
        color="#0b0b0b",
        fontsize=11,
    )
    ax.grid(color="#e8e7e3", lw=0.8)
    ax.tick_params(colors="#52514e")
    for side in ax.spines.values():
        side.set_color("#d4d3cd")
    ax.legend(frameon=False, labelcolor="#52514e")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def table(results: dict[str, dict]) -> str:
    """Render {model: metrics} as a Markdown table."""
    cols = list(next(iter(results.values())))
    head = "| model | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols)
    return head + "".join(
        f"\n| {m} | " + " | ".join(str(v) for v in r.values()) + " |" for m, r in results.items()
    )


def doc(meta: dict) -> str:
    """docs/evaluation.md for a trained model version."""
    ranks = "\n\n".join(
        f"### {split.title()}\n\n{table(r)}" for split, r in meta["results"].items()
    )
    cal = {
        h: {k: v for k, v in r.items() if not k.startswith("deciles")}
        for h, r in meta["calibrated_test"].items()
    }
    deciles = "\n".join(
        f"| {i + 1} | {p:.4f} | {o:.4f} |"
        for i, (p, o) in enumerate(meta["calibrated_test"]["30d"]["deciles_predicted_vs_observed"])
    )
    return f"""# Evaluation: model {meta["version"]}

Best 30-day ranker (by validation PR-AUC): **{meta["best"]}**. K = {meta["k"]} drives per weekly snapshot.
Splits: {meta["splits"]}.

## Ranking (raw scores, 30-day label)

{ranks}

## Calibrated chance of failing within 7, 30 and 90 days (test)

Each head is Platt-calibrated on the validation period. Brier is the mean squared error of the
probability; expected vs observed compares summed probabilities with actual failures.

{table(cal)}

### 30-day calibration by predicted decile (test)

| Decile | Mean predicted | Observed rate |
|---|---|---|
{deciles}

![Cost curve](../models/{meta["version"]}/cost_curve.png)
"""
