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
