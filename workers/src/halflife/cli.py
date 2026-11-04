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
    raise NotImplementedError


@app.command()
def features():
    """Silver -> gold labels and features."""
    raise NotImplementedError


@app.command()
def train():
    """Train and evaluate models."""
    raise NotImplementedError


@app.command()
def score():
    """Score active drives and upsert to Supabase."""
    raise NotImplementedError


@app.command()
def onboard():
    """Map a customer file to the canonical schema."""
    raise NotImplementedError
