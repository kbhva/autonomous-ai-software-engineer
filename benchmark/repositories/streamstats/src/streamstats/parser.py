"""CSV-like row parsing without third-party dependencies."""
import csv
from io import StringIO
from .models import Sample

def parse_rows(text):
    """Parse timestamp,group,value records, skipping the header."""
    rows = csv.DictReader(StringIO(text))
    output = []
    for row in rows:
        raw = row.get("value", "")
        value = float(raw) if raw else 0.0
        output.append(Sample(int(row["timestamp"]), row["group"], value))
    return output
