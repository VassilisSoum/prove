"""Two membership-check implementations, compared on a DETERMINISTIC cost metric:
the number of element comparisons to answer a batch of "is x in items?" queries.

`count_naive` (floor) rescans the list for every query — O(targets x items).
`count_setbased` (candidate) builds a set once, then does O(1) lookups.

The metric is an exact integer (no timing flakiness), so it's reproducible in CI —
the harness still flags that trials add no information for a deterministic metric, while
the bootstrap CI confirms the improvement is real (not noise).
"""


def make_workload(n, present):
    """Deterministic workload: items 0..n-1, plus 20 queries that are all present
    (worst case for the naive scan) or all absent."""
    items = list(range(n))
    targets = [n - 1] * 20 if present else [n + 1] * 20
    return items, targets


def count_naive(items, targets):
    comparisons = 0
    for t in targets:
        for it in items:
            comparisons += 1
            if it == t:
                break
    return comparisons


def count_setbased(items, targets):
    comparisons = len(items)        # one pass to build the set
    seen = set(items)
    for t in targets:
        comparisons += 1            # a hash lookup, counted as one comparison
        _ = t in seen
    return comparisons
