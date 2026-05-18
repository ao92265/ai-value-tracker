"""Anthropic console usage export adapter.

Anthropic console exports CSV from console.anthropic.com/settings/usage.
Expected columns (case-insensitive, missing tolerated):
    date | workspace | api_key_name | model
    input_tokens | output_tokens | cache_creation_input_tokens | cache_read_input_tokens
    cost (usd) | requests

Pass the path with `--anthropic-csv path/to/export.csv`.
"""

import csv
from pathlib import Path


def _num(s, default=0):
    if s is None or s == "":
        return default
    try:
        return float(str(s).replace("$", "").replace(",", ""))
    except ValueError:
        return default


def read(csv_path):
    p = Path(csv_path)
    if not p.is_file():
        return []
    rows = []
    with open(p) as f:
        reader = csv.DictReader(f)
        lower = {k.lower(): k for k in (reader.fieldnames or [])}

        def col(name):
            return lower.get(name)

        for r in reader:
            cost = (
                _num(r.get(col("cost (usd)") or col("cost") or col("cost_usd") or ""))
            )
            date = r.get(col("date") or "", "")
            workspace = r.get(col("workspace") or "", "")
            api_key = r.get(col("api_key_name") or col("api key") or "", "")
            model = r.get(col("model") or "", "")
            ti = int(_num(r.get(col("input_tokens") or "", 0)))
            to = int(_num(r.get(col("output_tokens") or "", 0)))
            cw = int(_num(r.get(col("cache_creation_input_tokens") or "", 0)))
            cr = int(_num(r.get(col("cache_read_input_tokens") or "", 0)))
            attr = f"workspace:{workspace}" if workspace else (f"key:{api_key}" if api_key else "anthropic-api")
            rows.append({
                "source": "anthropic-api",
                "started": date,
                "cost_usd": round(cost, 4),
                "attributed_to": attr,
                "units": ti + to + cw + cr,
                "notes": f"model={model}",
            })
    return rows
