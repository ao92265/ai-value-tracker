"""Customer-side telemetry reader.

Once a product instrumented with AI-vs-human action logging is connected,
this module reads the events and produces a per-issue value CSV that
replaces value_score in report.py.

The event schema is documented in docs/telemetry-spec.md.

Usage (once table exists):
    avt-telemetry --db-url <conn> --issue 8579 --since 2026-04-01
"""

import argparse
import csv
import os
import sys


EXPECTED_SCHEMA = """
Table: ai_action_event
  id              uuid PK
  tenant_id       uuid       -- tenant-scoped; never leak across customers
  feature_key     text       -- e.g. 'email-intake', 'allegation-draft'
  issue_number    int        -- the GitHub issue this feature traces to
  case_id         uuid NULL
  field_name      text       -- which field on the artifact
  ai_value        text       -- what the AI produced
  human_value     text       -- what the human kept (may equal ai_value)
  outcome         enum('accepted', 'edited', 'rejected')
  seconds_saved   int        -- optional estimate
  created_at      timestamptz
"""


def main():
    ap = argparse.ArgumentParser(description="Read AI-action telemetry, output per-feature value CSV.")
    ap.add_argument("--db-url", help="Postgres/MSSQL connection string. Reads $DATABASE_URL if unset.")
    ap.add_argument("--issue", type=int, help="Restrict to one issue.")
    ap.add_argument("--since", help="ISO date.")
    ap.add_argument("--out", default="-")
    ap.add_argument("--print-schema", action="store_true")
    args = ap.parse_args()

    if args.print_schema:
        print(EXPECTED_SCHEMA)
        return

    print("telemetry reader is a stub until the ai_action_event table lands in your product.", file=sys.stderr)
    print("Run `avt-telemetry --print-schema` for the expected schema.", file=sys.stderr)
    print("Spec: docs/telemetry-spec.md", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
