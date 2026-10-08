"""Deterministic sample ordering helpers."""
def chronological(samples):
    """Sort by timestamp, then group name for stable ties."""
    return sorted(samples, key=lambda sample: sample.timestamp)
