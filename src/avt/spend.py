"""Walk Claude Code JSONL logs, attribute spend per session, branch, issue.

Output CSV columns:
  session_id, started, cwd, branch, issue, title,
  cost_usd, tokens_in, tokens_out, tokens_cache_w, tokens_cache_r
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# USD per 1M tokens. Approximate. Update when pricing changes.
PRICES = {
    "claude-opus-4-7":    {"in": 15.00, "out": 75.00, "cache_w": 18.75, "cache_r": 1.50},
    "claude-opus-4-6":    {"in": 15.00, "out": 75.00, "cache_w": 18.75, "cache_r": 1.50},
    "claude-sonnet-4-6":  {"in":  3.00, "out": 15.00, "cache_w":  3.75, "cache_r": 0.30},
    "claude-haiku-4-5":   {"in":  0.80, "out":  4.00, "cache_w":  1.00, "cache_r": 0.08},
}

_HOME = os.path.expanduser("~")
DEFAULT_PROJECT = os.environ.get("AVT_PROJECT", os.path.join(_HOME, ".claude", "projects"))
ISSUE_RE = re.compile(r"issue[-_/](\d+)", re.IGNORECASE)
COMMIT_ISSUE_RE = re.compile(r"#(\d{2,6})\b")


def model_price(model):
    if not model:
        return None
    for key, prices in PRICES.items():
        if model.startswith(key):
            return prices
    base = re.sub(r"-\d{8}$", "", model)
    return PRICES.get(base)


def session_cost(usage_records):
    total = 0.0
    tok_in = tok_out = tok_cw = tok_cr = 0
    for model, u in usage_records:
        p = model_price(model)
        if not p:
            continue
        ti = u.get("input_tokens", 0) or 0
        to = u.get("output_tokens", 0) or 0
        cw = u.get("cache_creation_input_tokens", 0) or 0
        cr = u.get("cache_read_input_tokens", 0) or 0
        total += (ti * p["in"] + to * p["out"] + cw * p["cache_w"] + cr * p["cache_r"]) / 1_000_000
        tok_in += ti
        tok_out += to
        tok_cw += cw
        tok_cr += cr
    return total, tok_in, tok_out, tok_cw, tok_cr


def parse_jsonl(path):
    cwd = None
    start_ts = None
    title = None
    first_prompt = None
    usage = []
    with open(path, errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not cwd and "cwd" in d:
                cwd = d["cwd"]
            if not start_ts and "timestamp" in d:
                start_ts = d["timestamp"]
            if not title and d.get("type") == "ai-title":
                title = d.get("title") or d.get("text")
            if not first_prompt and d.get("type") == "user":
                msg = d.get("message", {})
                if isinstance(msg, dict):
                    c = msg.get("content")
                    if isinstance(c, str):
                        first_prompt = c[:120]
                    elif isinstance(c, list) and c:
                        first = c[0]
                        if isinstance(first, dict):
                            first_prompt = (first.get("text") or "")[:120]
            msg = d.get("message")
            if isinstance(msg, dict) and "usage" in msg:
                usage.append((msg.get("model"), msg["usage"]))
    return {
        "cwd": cwd,
        "start_ts": start_ts,
        "title": title,
        "first_prompt": first_prompt,
        "usage": usage,
    }


def git_branch_at(cwd, when_iso):
    if not cwd or not Path(cwd).is_dir():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "reflog", "--date=iso-strict",
             "--format=%gd %gs %cd"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    if result.returncode != 0 or not when_iso:
        try:
            r = subprocess.run(
                ["git", "-C", cwd, "branch", "--show-current"],
                capture_output=True, text=True, timeout=5,
            )
            return r.stdout.strip() or None
        except Exception:
            return None
    try:
        target = datetime.fromisoformat(when_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    best = None
    best_delta = timedelta.max
    for line in result.stdout.splitlines():
        m = re.search(r"checkout: moving from \S+ to (\S+)", line)
        if not m:
            continue
        ts_m = re.search(r"\b(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2})\b", line)
        if not ts_m:
            continue
        try:
            ts = datetime.fromisoformat(ts_m.group(1))
        except ValueError:
            continue
        delta = abs(target - ts)
        if delta < best_delta:
            best_delta = delta
            best = m.group(1)
    return best


def git_user(cwd):
    if not cwd or not Path(cwd).is_dir():
        return None
    try:
        r = subprocess.run(
            ["git", "-C", cwd, "config", "user.email"],
            capture_output=True, text=True, timeout=3,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    return r.stdout.strip() or None


def issue_from_branch(branch):
    if not branch:
        return None
    m = ISSUE_RE.search(branch)
    return m.group(1) if m else None


def issue_from_commits(cwd, branch):
    if not cwd or not branch or not Path(cwd).is_dir():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "log", "-n", "20", "--format=%s%n%b", branch],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    if result.returncode != 0:
        return None
    counts = {}
    for m in COMMIT_ISSUE_RE.finditer(result.stdout):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda x: x[1])[0]


def main():
    ap = argparse.ArgumentParser(description="Spend per Claude Code session, attributed to branch/issue.")
    ap.add_argument("--project", default=DEFAULT_PROJECT)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", default="-")
    args = ap.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    project_dir = Path(args.project)
    if not project_dir.is_dir():
        print(f"project dir not found: {project_dir}", file=sys.stderr)
        sys.exit(1)

    rows = []
    jsonl_files = list(project_dir.glob("*.jsonl"))
    if not jsonl_files:
        for sub in project_dir.iterdir():
            if sub.is_dir():
                jsonl_files.extend(sub.glob("*.jsonl"))
    for jsonl in jsonl_files:
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
        issue = issue_from_branch(branch) or issue_from_commits(info["cwd"], branch) or ""
        user = git_user(info["cwd"]) or ""
        rows.append({
            "session_id": jsonl.stem,
            "started": info["start_ts"] or "",
            "cwd": info["cwd"] or "",
            "branch": branch or "",
            "issue": issue,
            "user": user,
            "title": (info["title"] or info["first_prompt"] or "").replace("\n", " "),
            "cost_usd": round(cost, 4),
            "tokens_in": ti,
            "tokens_out": to,
            "tokens_cache_w": cw,
            "tokens_cache_r": cr,
        })

    rows.sort(key=lambda r: r["cost_usd"], reverse=True)

    if args.out == "-":
        out = sys.stdout
    else:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        out = open(args.out, "w", newline="")
    writer = csv.DictWriter(out, fieldnames=[
        "session_id", "started", "cwd", "branch", "issue", "user", "title",
        "cost_usd", "tokens_in", "tokens_out", "tokens_cache_w", "tokens_cache_r",
    ])
    writer.writeheader()
    writer.writerows(rows)
    if out is not sys.stdout:
        out.close()

    total = sum(r["cost_usd"] for r in rows)
    by_issue = {}
    for r in rows:
        key = r["issue"] or "(unattributed)"
        by_issue[key] = by_issue.get(key, 0) + r["cost_usd"]
    print(f"\nSessions: {len(rows)}  Total: ${total:.2f}", file=sys.stderr)
    print("Top issues by spend:", file=sys.stderr)
    for issue, cost in sorted(by_issue.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  #{issue:<10}  ${cost:>8.2f}", file=sys.stderr)


if __name__ == "__main__":
    main()
