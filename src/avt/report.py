"""Join spend.csv and value.csv per issue. Emit report.csv and bar chart.

value_score is a placeholder formula:
    value_score = lines_added + lines_removed + (prs_merged * 200)

Replace with the real customer-recognised measure once product telemetry
is wired up (see docs/telemetry-spec.md).
"""

import argparse
import csv
import os
import sys
from collections import defaultdict


def load_spend(path):
    by_issue = defaultdict(lambda: {"cost_usd": 0.0, "sessions": 0, "branches": set(), "titles": []})
    with open(path) as f:
        for r in csv.DictReader(f):
            key = r["issue"] or "(unattributed)"
            by_issue[key]["cost_usd"] += float(r["cost_usd"])
            by_issue[key]["sessions"] += 1
            if r["branch"]:
                by_issue[key]["branches"].add(r["branch"])
            if r["title"]:
                by_issue[key]["titles"].append(r["title"])
    return by_issue


def load_value(path):
    by_issue = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            by_issue[r["issue"]] = r
    return by_issue


def value_score(v):
    if not v:
        return 0
    added = int(v.get("lines_added") or 0)
    removed = int(v.get("lines_removed") or 0)
    merged = int(v.get("prs_merged") or 0)
    return added + removed + merged * 200


def main():
    ap = argparse.ArgumentParser(description="Join spend and value, emit report + chart.")
    ap.add_argument("--spend", required=True)
    ap.add_argument("--value", required=True)
    ap.add_argument("--out", default="-")
    ap.add_argument("--chart", default=None, help="Output path for PNG bar chart.")
    ap.add_argument("--top", type=int, default=20, help="Top N issues by cost in the chart.")
    args = ap.parse_args()

    spend = load_spend(args.spend)
    value = load_value(args.value)

    rows = []
    for issue, s in spend.items():
        v = value.get(issue, {})
        vs = value_score(v)
        cost = round(s["cost_usd"], 2)
        ratio = round(vs / cost, 2) if cost else 0
        rows.append({
            "issue": issue,
            "title": (v.get("title") or (s["titles"][0] if s["titles"] else ""))[:100],
            "branch": next(iter(s["branches"]), ""),
            "sessions": s["sessions"],
            "cost_usd": cost,
            "prs_open": v.get("prs_open", ""),
            "prs_merged": v.get("prs_merged", ""),
            "lines_added": v.get("lines_added", ""),
            "lines_removed": v.get("lines_removed", ""),
            "files_changed": v.get("files_changed", ""),
            "value_score": vs,
            "ratio": ratio,
        })

    rows.sort(key=lambda r: r["cost_usd"], reverse=True)

    if args.out == "-":
        out = sys.stdout
    else:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        out = open(args.out, "w", newline="")
    writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()) if rows else [])
    writer.writeheader()
    writer.writerows(rows)
    if out is not sys.stdout:
        out.close()

    total_cost = sum(r["cost_usd"] for r in rows)
    total_value = sum(r["value_score"] for r in rows)
    print(f"Issues: {len(rows)}", file=sys.stderr)
    print(f"Total cost: ${total_cost:.2f}", file=sys.stderr)
    print(f"Total value_score: {total_value}", file=sys.stderr)
    if total_cost:
        print(f"Overall ratio: {total_value / total_cost:.2f} value-units per USD", file=sys.stderr)

    if args.chart:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not installed; skipping chart", file=sys.stderr)
            return
        top = rows[: args.top]
        labels = [f"#{r['issue']}" for r in top]
        costs = [r["cost_usd"] for r in top]
        values = [r["value_score"] for r in top]
        fig, ax1 = plt.subplots(figsize=(12, 6))
        x = range(len(labels))
        ax1.bar([i - 0.2 for i in x], costs, 0.4, label="Cost (USD)", color="#d62728")
        ax1.set_ylabel("Cost (USD)", color="#d62728")
        ax1.tick_params(axis="y", labelcolor="#d62728")
        ax2 = ax1.twinx()
        ax2.bar([i + 0.2 for i in x], values, 0.4, label="Value score", color="#2ca02c")
        ax2.set_ylabel("Value score", color="#2ca02c")
        ax2.tick_params(axis="y", labelcolor="#2ca02c")
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(labels, rotation=45, ha="right")
        ax1.set_title(f"AI spend vs value, top {len(top)} issues")
        fig.tight_layout()
        os.makedirs(os.path.dirname(args.chart) or ".", exist_ok=True)
        fig.savefig(args.chart, dpi=120)
        print(f"Chart written: {args.chart}", file=sys.stderr)


if __name__ == "__main__":
    main()
