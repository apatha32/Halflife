from datetime import datetime

import typer

app = typer.Typer(no_args_is_help=True)
Day = typer.Option(formats=["%Y-%m-%d"])


@app.command()
def ingest(
    start: datetime = Day,
    end: datetime = Day,
    sample_pct: float = typer.Option(10.0, min=0.01, max=100),
):
    """Load Backblaze Drive Stats into bronze."""
    from halflife.ingest import ingest

    if start > end:
        raise typer.BadParameter("--start must be on or before --end")
    ingest(start.date(), end.date(), sample_pct)


@app.command()
def clean():
    """Bronze -> silver with quarantine and a quality report."""
    import json
    import os

    from halflife import DATA, report
    from halflife.clean import clean

    out = DATA / "reports"
    out.mkdir(parents=True, exist_ok=True)
    prev = sorted(out.glob("*.json"))
    r = report.build(
        clean(DATA / "bronze", DATA / "silver"), json.loads(prev[-1].read_text()) if prev else None
    )
    stem = out / r["run_at"].replace(":", "")
    stem.with_suffix(".json").write_text(json.dumps(r, indent=2))
    stem.with_suffix(".md").write_text(report.render(r))
    print(report.render(r))
    limit = float(os.environ.get("NULL_RATE_MAX_JUMP", "0.05"))
    jumps = {c: d for c, d in r["null_rate_change"].items() if d > limit}
    if jumps:
        raise typer.Exit(f"Null rate jumped more than {limit:.0%}: {jumps}")


@app.command()
def features():
    """Silver -> gold labels and features."""
    import os

    from halflife import DATA
    from halflife.features import features

    n = features(DATA / "silver", DATA / "gold", int(os.environ.get("HORIZON_DAYS", "30")))
    print(f"gold: {n:,} rows")


@app.command()
def train():
    """Train and evaluate models."""
    import os

    from halflife import DATA, ROOT, evaluate
    from halflife.train import train

    k = int(os.environ.get("WEEKLY_CAPACITY", "50"))
    meta = train(
        DATA / "gold", ROOT / "models", k, float(os.environ.get("NEG_SAMPLE_RATE", "0.05"))
    )
    tables = "\n\n".join(
        f"### {split.title()}\n\n{evaluate.table(r)}" for split, r in meta["results"].items()
    )
    doc = (
        f"# Evaluation — model {meta['version']}\n\nBest (by validation PR-AUC): "
        f"**{meta['best']}**. K = {k} drives per weekly snapshot. Splits: {meta['splits']}.\n\n"
        f"{tables}\n\n![Cost curve](../models/{meta['version']}/cost_curve.png)\n"
    )
    (ROOT / "docs" / "evaluation.md").write_text(doc)
    print(doc)


@app.command()
def score():
    """Score active drives and upsert to Supabase."""
    raise NotImplementedError


@app.command()
def onboard():
    """Map a customer file to the canonical schema."""
    raise NotImplementedError
