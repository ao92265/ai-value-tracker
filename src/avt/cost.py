"""Unified cost command. Pulls from every enabled source, merges, emits CSV.

Examples:

    avt-cost --claude --days 30 --out out/cost.csv
    avt-cost --claude --anthropic-csv anthropic-export.csv --copilot-org myorg
    avt-cost --vendor-csv intercom.csv --vendor-source intercom-fin
"""

import argparse
import csv
import os
import sys
from collections import defaultdict

from avt.sources import ROW_FIELDS
from avt.sources import claude_jsonl, anthropic_invoice, copilot_admin, vendor_csv


def main():
    ap = argparse.ArgumentParser(description="Unified AI cost across all configured sources.")
    ap.add_argument("--out", default="-")

    # claude code
    ap.add_argument("--claude", action="store_true", help="Include Claude Code JSONL spend.")
    ap.add_argument("--claude-project", default=claude_jsonl.DEFAULT_PROJECT)
    ap.add_argument("--days", type=int, default=30)

    # anthropic console csv
    ap.add_argument("--anthropic-csv", help="Path to Anthropic console usage export.")

    # github copilot
    ap.add_argument("--copilot-org", help="GitHub org slug for Copilot admin pull.")
    ap.add_argument("--copilot-price", type=float, default=None, help="Override seat price USD.")
    ap.add_argument("--copilot-month", help="YYYY-MM tag for the snapshot.")

    # generic vendor csv (repeatable via shell)
    ap.add_argument("--vendor-csv", help="Vendor CSV path.")
    ap.add_argument("--vendor-source", default="vendor", help="Label for this vendor source.")

    args = ap.parse_args()

    rows = []

    if args.claude:
        r = claude_jsonl.read(project=args.claude_project, days=args.days)
        rows.extend(r)
        print(f"  claude-code: {len(r)} rows, ${sum(x['cost_usd'] for x in r):.2f}", file=sys.stderr)

    if args.anthropic_csv:
        r = anthropic_invoice.read(args.anthropic_csv)
        rows.extend(r)
        print(f"  anthropic-api: {len(r)} rows, ${sum(x['cost_usd'] for x in r):.2f}", file=sys.stderr)

    if args.copilot_org:
        r = copilot_admin.read(args.copilot_org, price_per_seat=args.copilot_price,
                               month_yyyy_mm=args.copilot_month)
        rows.extend(r)
        print(f"  copilot: {len(r)} rows, ${sum(x['cost_usd'] for x in r):.2f}", file=sys.stderr)

    if args.vendor_csv:
        r = vendor_csv.read(args.vendor_csv, source=args.vendor_source)
        rows.extend(r)
        print(f"  {args.vendor_source}: {len(r)} rows, ${sum(x['cost_usd'] for x in r):.2f}", file=sys.stderr)

    if not rows:
        print("no sources enabled. pass --claude / --anthropic-csv / --copilot-org / --vendor-csv", file=sys.stderr)
        sys.exit(1)

    if args.out == "-":
        out = sys.stdout
    else:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        out = open(args.out, "w", newline="")
    w = csv.DictWriter(out, fieldnames=ROW_FIELDS)
    w.writeheader()
    w.writerows(rows)
    if out is not sys.stdout:
        out.close()

    total = sum(r["cost_usd"] for r in rows)
    by_source = defaultdict(float)
    for r in rows:
        by_source[r["source"]] += r["cost_usd"]
    print(f"\nTotal: ${total:.2f} across {len(rows)} rows", file=sys.stderr)
    for src, cost in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        pct = (cost / total * 100) if total else 0
        print(f"  {src:<20} ${cost:>10.2f}  ({pct:>5.1f}%)", file=sys.stderr)


if __name__ == "__main__":
    main()
