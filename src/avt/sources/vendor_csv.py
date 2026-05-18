"""Generic vendor CSV adapter. Map any vendor export into the common row shape.

Specify column names with the cols kwarg:

    read("export.csv", source="intercom-fin",
         cols={"cost": "Total Cost", "date": "Day", "user": "Agent", "units": "Resolutions"})

Defaults try sensible column-name guesses if cols is not given.
"""

import csv
from pathlib import Path


DEFAULT_COLS = {
    "cost": ["cost", "cost_usd", "amount", "total", "spend"],
    "date": ["date", "day", "month", "period", "timestamp"],
    "attr": ["user", "team", "tenant", "customer", "workspace", "assignee"],
    "units": ["units", "count", "resolutions", "minutes", "seats", "tokens"],
    "notes": ["notes", "description", "category", "product"],
}


def _resolve(headers, candidates, explicit=None):
    if explicit:
        return explicit if explicit in headers else None
    lower = {h.lower(): h for h in headers}
    for c in candidates:
        if c in lower:
            return lower[c]
    return None


def _num(s, default=0.0):
    if s is None or s == "":
        return default
    try:
        return float(str(s).replace("$", "").replace(",", ""))
    except ValueError:
        return default


def read(csv_path, source, cols=None):
    cols = cols or {}
    p = Path(csv_path)
    if not p.is_file():
        return []
    rows = []
    with open(p) as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        cost_col = _resolve(headers, DEFAULT_COLS["cost"], cols.get("cost"))
        date_col = _resolve(headers, DEFAULT_COLS["date"], cols.get("date"))
        attr_col = _resolve(headers, DEFAULT_COLS["attr"], cols.get("user"))
        units_col = _resolve(headers, DEFAULT_COLS["units"], cols.get("units"))
        notes_col = _resolve(headers, DEFAULT_COLS["notes"], cols.get("notes"))
        if not cost_col:
            return []
        for r in reader:
            attr_val = r.get(attr_col, "") if attr_col else ""
            rows.append({
                "source": source,
                "started": r.get(date_col, "") if date_col else "",
                "cost_usd": round(_num(r.get(cost_col)), 4),
                "attributed_to": f"{attr_col or 'row'}:{attr_val}" if attr_val else source,
                "units": int(_num(r.get(units_col, 0))) if units_col else 0,
                "notes": r.get(notes_col, "") if notes_col else "",
            })
    return rows
