import os
from pathlib import Path

ROOT = Path(__file__).parents[3]
DATA = Path(os.environ.get("DATA_DIR", ROOT / "data"))
