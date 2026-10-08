"""Group aggregation and anomaly marking."""
from collections import defaultdict
from .models import Summary

def summarize(samples):
    values = defaultdict(list)
    for sample in samples:
        if sample.value is not None: values[sample.group].append(sample.value)
    return [Summary(group, len(items), sum(items), sum(items) / len(items))
            for group, items in sorted(values.items()) if items]

def above_threshold(samples, threshold):
    """Keep samples strictly above a configured limit."""
    return [sample for sample in samples if sample.value is not None and sample.value >= threshold]
