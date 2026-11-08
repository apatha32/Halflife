import os
from pathlib import Path

import httpx

from halflife.onboard import apply, profile, propose
from halflife.score import rest


def fetch(path: str, out: Path) -> Path:
    """Download an uploaded CSV from the private Supabase Storage bucket."""
    _, headers = rest("")
    r = httpx.get(
        f"{os.environ['SUPABASE_URL']}/storage/v1/object/uploads/{path}",
        headers=headers,
        timeout=120,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.raise_for_status().content)
    return out


def waiting(status: str) -> list[dict]:
    """Uploads in a status, with their fleet name."""
    url, headers = rest("uploads")
    params = {
        "status": f"eq.{status}",
        "select": "id,fleet_id,path,mapping,fleets(name)",
        "order": "created_at",
    }
    return httpx.get(url, params=params, headers=headers, timeout=60).raise_for_status().json()


def update(upload_id: str, fields: dict) -> None:
    url, headers = rest("uploads")
    httpx.patch(
        url, params={"id": f"eq.{upload_id}"}, json=fields, headers=headers, timeout=60
    ).raise_for_status()


def process(data: Path, model_dir: Path) -> dict[str, int]:
    """Propose mappings for new uploads and run approved ones through clean -> features -> score."""
    done = {"proposed": 0, "scored": 0, "failed": 0}
    for u in waiting("uploaded"):
        prof = profile(fetch(u["path"], data / "uploads" / f"{u['id']}.csv"))
        update(
            u["id"], {"status": "needs_review", "mapping": propose(prof) | {"sources": list(prof)}}
        )
        done["proposed"] += 1
    for u in waiting("approved"):
        update(u["id"], {"status": "processing"})
        try:
            file = fetch(u["path"], data / "uploads" / f"{u['id']}.csv")
            r = apply(
                file, u["mapping"], u["fleets"]["name"], data / "fleets" / u["fleet_id"], model_dir
            )
            keep = ("rows_in", "rows_out", "quarantined", "parse_failures", "data_end", "scored")
            update(u["id"], {"status": "scored", "result": {k: r[k] for k in keep}, "error": None})
            done["scored"] += 1
        except Exception as e:  # noqa: BLE001  customer data: mark this upload failed, keep the job going
            update(u["id"], {"status": "failed", "error": str(e)[:500]})
            done["failed"] += 1
    return done
