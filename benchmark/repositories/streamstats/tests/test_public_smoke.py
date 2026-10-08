from streamstats.analytics import summarize
from streamstats.models import Sample
from streamstats.parser import parse_rows
from streamstats.pipeline import run_report
from streamstats.report import render_summary

def test_public_analytics_flow():
    rows = parse_rows("timestamp,group,value\n1,alpha,2\n2,alpha,4\n")
    summary = summarize(rows)
    assert summary[0].count == 2 and summary[0].mean == 3
    assert "alpha,2,6,3" in render_summary(summary)
    assert "alpha,2,6,3" in run_report("timestamp,group,value\n1,alpha,2\n2,alpha,4\n")
    assert Sample(1, "x", 3).value == 3
