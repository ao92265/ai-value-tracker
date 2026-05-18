"""Claude Code JSONL adapter. Wraps avt.spend internals into the common row shape."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from avt.spend import (
    parse_jsonl,
    session_cost,
    git_branch_at,
    issue_from_branch,
    issue_from_commits,
    DEFAULT_PROJECT,
)


def read(project=DEFAULT_PROJECT, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    project_dir = Path(project)
    if not project_dir.is_dir():
        return []
    rows = []
    for jsonl in project_dir.glob("*.jsonl"):
        mtime = datetime.fromtimestamp(jsonl.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            continue
        info = parse_jsonl(jsonl)
        if not info["usage"]:
            continue
        cost, ti, to, cw, cr = session_cost(info["usage"])
        if cost == 0:
            continue
        branch = git_branch_at(info["cwd"], info["start_ts"])
        issue = issue_from_branch(branch) or issue_from_commits(info["cwd"], branch)
        attr = f"issue:{issue}" if issue else (f"branch:{branch}" if branch else "unattributed")
        rows.append({
            "source": "claude-code",
            "started": info["start_ts"] or "",
            "cost_usd": round(cost, 4),
            "attributed_to": attr,
            "units": ti + to + cw + cr,
            "notes": (info["title"] or info["first_prompt"] or "").replace("\n", " ")[:120],
        })
    return rows
