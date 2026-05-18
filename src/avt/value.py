"""Pull GitHub PR + issue data via gh CLI. Output value-side CSV per issue.

Columns:
  issue, title, state, closed_at, prs_open, prs_merged, prs_closed,
  lines_added, lines_removed, files_changed, age_days
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone


def gh(args):
    try:
        r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"gh failed: {e}", file=sys.stderr)
        return None
    if r.returncode != 0:
        print(f"gh error: {r.stderr.strip()}", file=sys.stderr)
        return None
    return r.stdout


def list_issues(repo, days):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    out = gh([
        "issue", "list", "--repo", repo, "--state", "all", "--limit", "500",
        "--search", f"updated:>={since}",
        "--json", "number,title,state,createdAt,closedAt,labels",
    ])
    if not out:
        return []
    return json.loads(out)


def prs_for_issue(repo, issue_num):
    """Find PRs that reference this issue (closes/fixes/resolves #N) via search."""
    out = gh([
        "pr", "list", "--repo", repo, "--state", "all", "--limit", "20",
        "--search", f"#{issue_num} in:body",
        "--json", "number,state,additions,deletions,changedFiles,mergedAt,createdAt",
    ])
    if not out:
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return []


def main():
    ap = argparse.ArgumentParser(description="GitHub issue + PR stats for value side.")
    ap.add_argument("--repo", default="i2group-FIS/Wraith")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", default="-")
    ap.add_argument("--issues", help="Comma-separated issue numbers to limit to (skip listing).")
    args = ap.parse_args()

    if args.issues:
        issue_nums = [int(x) for x in args.issues.split(",")]
        issues = [{"number": n, "title": "", "state": "", "createdAt": "", "closedAt": "", "labels": []} for n in issue_nums]
    else:
        issues = list_issues(args.repo, args.days)

    rows = []
    for i, issue in enumerate(issues, 1):
        n = issue["number"]
        if i % 10 == 0:
            print(f"  [{i}/{len(issues)}]", file=sys.stderr)
        prs = prs_for_issue(args.repo, n)
        added = sum(p.get("additions", 0) or 0 for p in prs)
        removed = sum(p.get("deletions", 0) or 0 for p in prs)
        files = sum(p.get("changedFiles", 0) or 0 for p in prs)
        prs_open = sum(1 for p in prs if p.get("state") == "OPEN")
        prs_merged = sum(1 for p in prs if p.get("mergedAt"))
        prs_closed = sum(1 for p in prs if p.get("state") == "CLOSED" and not p.get("mergedAt"))
        age_days = ""
        if issue.get("createdAt"):
            try:
                created = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
                end = datetime.fromisoformat((issue.get("closedAt") or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
                age_days = (end - created).days
            except ValueError:
                pass
        rows.append({
            "issue": n,
            "title": (issue.get("title") or "").replace("\n", " ")[:120],
            "state": issue.get("state", ""),
            "closed_at": issue.get("closedAt") or "",
            "prs_open": prs_open,
            "prs_merged": prs_merged,
            "prs_closed": prs_closed,
            "lines_added": added,
            "lines_removed": removed,
            "files_changed": files,
            "age_days": age_days,
        })

    if args.out == "-":
        out = sys.stdout
    else:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        out = open(args.out, "w", newline="")
    writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()) if rows else [
        "issue", "title", "state", "closed_at", "prs_open", "prs_merged",
        "prs_closed", "lines_added", "lines_removed", "files_changed", "age_days",
    ])
    writer.writeheader()
    writer.writerows(rows)
    if out is not sys.stdout:
        out.close()
    print(f"Issues: {len(rows)}", file=sys.stderr)


if __name__ == "__main__":
    main()
