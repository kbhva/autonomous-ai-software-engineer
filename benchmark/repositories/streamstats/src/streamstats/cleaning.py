"""Filtering and normalization for parsed samples."""
from .models import Sample

def keep_valid(samples):
    return [sample for sample in samples if sample.value is not None]

def normalize_groups(samples):
    return [Sample(s.timestamp, s.group.strip().lower(), s.value) for s in samples]
