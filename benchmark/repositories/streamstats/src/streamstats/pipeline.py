"""Public pipeline composing parsing, cleaning, aggregation and reporting."""
from .analytics import summarize
from .cleaning import keep_valid
from .parser import parse_rows
from .report import render_summary

def run_report(text):
    samples = keep_valid(parse_rows(text))
    return render_summary(summarize(samples))
