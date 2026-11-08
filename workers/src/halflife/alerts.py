import os
from datetime import date

import httpx

from halflife.score import fleet_id, rest


def message(fleet: str, day: date, k: int, alerts: list[dict]) -> str:
    """Slack text for a day's new alerts, riskiest first (at most 20 lines)."""
    lines = [f"Halflife: {len(alerts)} new alerts for {fleet} on {day}"]
    for a in sorted(alerts, key=lambda a: a["rank"])[:20]:
        why = (
            f"entered the top {k}"
            if a["kind"] == "entered_top_k"
            else f"rose from rank {a['prev_rank']:,}"
        )
        lines.append(f"- {a['drive_id']}: rank {a['rank']:,}, {why}")
    return "\n".join(lines)


def notify(fleet: str, day: date, k: int) -> list[dict]:
    """Create new alerts for a fleet's scoring day; post them to Slack when a webhook is set."""
    url, headers = rest("rpc/make_alerts")
    body = {"fid": fleet_id(fleet), "day": str(day), "k": k}
    new = httpx.post(url, json=body, headers=headers, timeout=60).raise_for_status().json()
    hook = os.environ.get("SLACK_WEBHOOK_URL")
    if hook and new:
        httpx.post(hook, json={"text": message(fleet, day, k, new)}, timeout=30).raise_for_status()
    return new
