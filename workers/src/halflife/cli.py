import json
import os
from datetime import date, datetime
from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True)
Day = typer.Option(formats=["%Y-%m-%d"])
ScoreDay = typer.Option(..., "--date", formats=["%Y-%m-%d"])
Required = typer.Option(...)


def capacity() -> int:
    """Weekly replacement capacity K (drives)."""
    return int(os.environ.get("WEEKLY_CAPACITY", "50"))


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
    from halflife import DATA
    from halflife.features import features

    n = features(DATA / "silver", DATA / "gold")
    print(f"gold: {n:,} rows")


@app.command()
def train():
    """Train and evaluate models."""
    from halflife import DATA, ROOT, evaluate
    from halflife.train import train

    k = capacity()
    meta = train(
        DATA / "gold", ROOT / "models", k, float(os.environ.get("NEG_SAMPLE_RATE", "0.05"))
    )
    doc = evaluate.doc(meta)
    (ROOT / "docs" / "evaluation.md").write_text(doc)
    print(doc)


@app.command()
def score(day: datetime = ScoreDay, fleet: str = "Acme Storage"):
    """Score active drives and upsert to Supabase."""
    from halflife import DATA, ROOT, alerts
    from halflife.score import score

    model_dir = max((ROOT / "models").glob("*/model.pkl")).parent
    print(f"{score(day.date(), fleet, DATA, model_dir):,} drives scored with {model_dir.name}")
    print(f"{len(alerts.notify(fleet, day.date(), capacity())):,} new alerts")


@app.command()
def onboard(fleet: str = Required, file: Path = Required, apply: bool = False):
    """Propose a column mapping for a customer file; with --apply, clean, featurize and score it."""

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
        max((ROOT / "models").glob("*/model.pkl")).parent,
    )
    print(
        f"{r['rows_in']:,} rows in, {sum(r['quarantined'].values()):,} quarantined "
        f"{r['quarantined']}, {r['scored']:,} drives scored for {fleet} on {r['data_end']}"
    )


@app.command()
def nightly(fleet: str = "Acme Storage"):
    """Ingest new months, clean, featurize, score the newest day and raise alerts."""
    from halflife import DATA, ROOT, alerts
    from halflife.clean import run
    from halflife.features import features
    from halflife.ingest import ingest, newest_day, resume_from
    from halflife.monitor import health
    from halflife.score import score

    start = resume_from(
        DATA / "bronze", date.fromisoformat(os.environ.get("INGEST_START", "2024-01-01"))
    )
    end = newest_day(start)
    ingest(start, end, float(os.environ.get("SAMPLE_PCT", "10")))
    _, jumps = run(DATA)
    if jumps:
        raise typer.Exit(f"Null rate jumped past NULL_RATE_MAX_JUMP: {jumps}")
    features(DATA / "silver", DATA / "gold")
    model_dir = max((ROOT / "models").glob("*/model.pkl")).parent
    report = max((DATA / "reports").glob("*.json"))
    r = json.loads(report.read_text()) | {
        "model_health": health(DATA / "gold", model_dir, capacity())
    }
    report.write_text(json.dumps(r, indent=2))
    print(f"{score(end, fleet, DATA, model_dir):,} drives scored for {end}")
    print(f"{len(alerts.notify(fleet, end, capacity())):,} new alerts")


@app.command()
def uploads():
    """Propose mappings for new customer uploads and score approved ones."""
    from halflife import DATA, ROOT
    from halflife.uploads import process

    print(process(DATA, max((ROOT / "models").glob("*/model.pkl")).parent))
