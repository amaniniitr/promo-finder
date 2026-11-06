"""Small, dependency-free metrics used to measure each stage."""
from __future__ import annotations

import math
from itertools import combinations


def ranks(values: list[float]) -> list[float]:
    """Average ranks (ties share the mean rank)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    r = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(x: list[float], y: list[float]) -> float:
    if len(x) < 3:
        return float("nan")
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def kendall_tau(x: list[float], y: list[float]) -> float:
    c = d = 0
    for i, j in combinations(range(len(x)), 2):
        s = (x[i] - x[j]) * (y[i] - y[j])
        c += s > 0
        d += s < 0
    return (c - d) / (c + d) if c + d else float("nan")


def topk_overlap(order_a: list[str], order_b: list[str], k: int) -> float:
    return len(set(order_a[:k]) & set(order_b[:k])) / k if k else float("nan")


def tie_share(values: list[float]) -> float:
    """Share of items whose score equals at least one other item's (coarse scores -> arbitrary order)."""
    from collections import Counter
    c = Counter(round(v, 2) for v in values)
    return sum(n for n in c.values() if n > 1) / len(values) if values else float("nan")


def cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    return num / den if den else 0.0


def mean(v):
    v = list(v)
    return sum(v) / len(v) if v else float("nan")
