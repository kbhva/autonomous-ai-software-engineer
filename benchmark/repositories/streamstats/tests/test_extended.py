from streamstats.analytics import above_threshold, summarize
from streamstats.cleaning import keep_valid, normalize_groups
from streamstats.models import Sample
from streamstats.ordering import chronological
from streamstats.parser import parse_rows
from streamstats.pipeline import run_report

def test_parser_reads_numeric_observations():
    assert parse_rows("timestamp,group,value\n1,a,2\n")[0].value == 2.0
def test_group_normalization_trims_and_lowercases():
    row = normalize_groups([Sample(1, " Alpha ", 2)])[0]
    assert row.group == "alpha"
def test_valid_rows_keep_known_values():
    assert keep_valid([Sample(1, "a", 2)]) == [Sample(1, "a", 2)]
def test_summary_counts_and_averages():
    result = summarize([Sample(1, "a", 2), Sample(2, "a", 4)])[0]
    assert (result.count, result.total, result.mean) == (2, 6, 3)
def test_threshold_returns_values_above_limit():
    row = Sample(1, "a", 3)
    assert above_threshold([row], 2) == [row]
def test_chronological_orders_distinct_timestamps():
    rows = [Sample(2, "a", 1), Sample(1, "b", 2)]
    assert [r.timestamp for r in chronological(rows)] == [1, 2]
def test_report_has_header_and_summary():
    text = run_report("timestamp,group,value\n1,a,2\n")
    assert text.startswith("group,count,total,mean\n") and "a,1,2,2" in text
