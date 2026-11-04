import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def ingest():
    """Load Backblaze Drive Stats into bronze."""
    raise NotImplementedError


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
