from datetime import datetime
from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True)
Day = typer.Option(formats=["%Y-%m-%d"])
ScoreDay = typer.Option(..., "--date", formats=["%Y-%m-%d"])
Required = typer.Option(...)


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
    from halflife import DATA, report
    from halflife.clean import run

    r, jumps = run(DATA)
    print(report.render(r))
    if jumps:
        raise typer.Exit(f"Null rate jumped past NULL_RATE_MAX_JUMP: {jumps}")


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
def score(day: datetime = ScoreDay, fleet: str = "Acme Storage"):
    """Score active drives and upsert to Supabase."""
    from halflife import DATA, ROOT
    from halflife.score import score

    model_dir = max((ROOT / "models").iterdir())
    print(f"{score(day.date(), fleet, DATA, model_dir):,} drives scored with {model_dir.name}")


@app.command()
def onboard(fleet: str = Required, file: Path = Required, apply: bool = False):
    """Propose a column mapping for a customer file; with --apply, clean, featurize and score it."""
    import os

    import yaml

    from halflife import DATA, ROOT
    from halflife import onboard as ob

    slug = fleet.lower().replace(" ", "-")
    path = ROOT / "mappings" / f"{slug}.yaml"
    if not apply:
        path.parent.mkdir(exist_ok=True)
        path.write_text(yaml.safe_dump(ob.propose(ob.profile(file)), sort_keys=False))
        print(f"{path.read_text()}\nReview {path}, then re-run with --apply.")
        return
    r = ob.apply(
        file,
        yaml.safe_load(path.read_text()),
        fleet,
        DATA / "fleets" / slug,
        max((ROOT / "models").iterdir()),
        int(os.environ.get("HORIZON_DAYS", "30")),
    )
    print(
        f"{r['rows_in']:,} rows in, {sum(r['quarantined'].values()):,} quarantined "
        f"{r['quarantined']}, {r['scored']:,} drives scored for {fleet} on {r['data_end']}"
    )
