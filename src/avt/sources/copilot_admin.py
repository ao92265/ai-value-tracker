"""GitHub Copilot admin adapter via `gh api`.

Pulls seat assignments and current month billing. Attributes flat seat cost
per assigned user. Plan price:

    business    = $19 /user /month
    enterprise  = $39 /user /month

Override with `--copilot-price`.

Needs gh authenticated with org admin scope (`read:org`, `manage_billing:copilot`).
"""

import json
import subprocess

PLAN_PRICE = {
    "business": 19.0,
    "enterprise": 39.0,
}


def _gh(args):
    try:
        r = subprocess.run(["gh", "api"] + args, capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout


def read(org, price_per_seat=None, month_yyyy_mm=None):
    billing = _gh([f"/orgs/{org}/copilot/billing"])
    plan = "business"
    if billing:
        try:
            plan = (json.loads(billing).get("plan_type") or "business").lower()
        except json.JSONDecodeError:
            pass
    if price_per_seat is None:
        price_per_seat = PLAN_PRICE.get(plan, 19.0)

    raw = _gh([
        "--paginate",
        f"/orgs/{org}/copilot/billing/seats",
    ])
    if not raw:
        return []
    rows = []
    seats = []
    for chunk in raw.split("\n"):
        if not chunk.strip():
            continue
        try:
            j = json.loads(chunk)
            seats.extend(j.get("seats", []))
        except json.JSONDecodeError:
            continue
    for seat in seats:
        login = (seat.get("assignee") or {}).get("login", "unknown")
        last_active = seat.get("last_activity_at") or ""
        rows.append({
            "source": "copilot",
            "started": month_yyyy_mm or last_active[:7],
            "cost_usd": round(price_per_seat, 2),
            "attributed_to": f"user:{login}",
            "units": 1,
            "notes": f"plan={plan} last_active={last_active}",
        })
    return rows
