def score_axis(count: int) -> float:
    """Computes a deterministic score based on matched keyword count.
    If no keywords matched, returns None (leave axis null).
    """
    if count == 0:
        return None
    return min(100.0, 50.0 + count * 10.0)
