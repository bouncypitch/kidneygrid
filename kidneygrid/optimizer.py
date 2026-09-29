"""Exchange optimization over an anonymous compatibility graph.

Nodes are anonymous pair ids. An edge (i, j) means the donor of pair i is
compatible with the patient of pair j. A cycle of length k is k transplants
performed simultaneously.
"""

from collections.abc import Iterable, Sequence

Edge = tuple[str, str]
Cycle = tuple[str, ...]

MAX_CYCLE_LEN = 3  # Real exchanges cap loops: every surgery in a loop runs at once.
SENSITIZED_CPRA = 80
SENSITIZED_BONUS = 0.1  # Tie-breaker: prefer plans that help hard-to-match patients.


def _adjacency(edges: Iterable[Edge]) -> dict[str, list[str]]:
    adj: dict[str, list[str]] = {}
    for src, dst in edges:
        adj.setdefault(src, []).append(dst)
    for dsts in adj.values():
        dsts.sort()
    return adj


def find_cycles(nodes: Sequence[str], edges: Iterable[Edge], max_len: int) -> list[Cycle]:
    """All simple cycles up to `max_len`, each listed once starting at its smallest node."""
    adj = _adjacency(edges)
    order = {n: i for i, n in enumerate(sorted(nodes))}
    cycles: list[Cycle] = []

    def extend(path: list[str]) -> None:
        start, last = path[0], path[-1]
        for nxt in adj.get(last, []):
            if nxt == start and len(path) >= 2:
                cycles.append(tuple(path))
            elif nxt not in path and order[nxt] > order[start] and len(path) < max_len:
                path.append(nxt)
                extend(path)
                path.pop()

    for node in sorted(nodes):
        extend([node])
    return sorted(cycles, key=lambda c: (len(c), c))


def cycle_weight(cycle: Cycle, cpra: dict[str, int]) -> float:
    bonus = sum(SENSITIZED_BONUS for n in cycle if cpra.get(n, 0) >= SENSITIZED_CPRA)
    return len(cycle) + bonus


def best_packing(cycles: Sequence[Cycle], cpra: dict[str, int]) -> list[Cycle]:
    """Exact maximum-weight set of node-disjoint cycles (branch and bound).

    Suitable for demo-sized pools; the offline benchmark uses an ILP instead.
    """
    ranked = sorted(cycles, key=lambda c: -cycle_weight(c, cpra))
    weights = [cycle_weight(c, cpra) for c in ranked]
    suffix = [0.0] * (len(ranked) + 1)
    for i in range(len(ranked) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + weights[i]

    best: list[Cycle] = []
    best_w = 0.0

    def search(i: int, used: set[str], chosen: list[Cycle], w: float) -> None:
        nonlocal best, best_w
        if w > best_w:
            best, best_w = list(chosen), w
        if i == len(ranked) or w + suffix[i] <= best_w:
            return
        cyc = ranked[i]
        if not used.intersection(cyc):
            chosen.append(cyc)
            search(i + 1, used | set(cyc), chosen, w + weights[i])
            chosen.pop()
        search(i + 1, used, chosen, w)

    search(0, set(), [], 0.0)
    return sorted(best, key=lambda c: (-len(c), c))


def myopic_matching(
    arrival_order: Sequence[str], edges: Iterable[Edge], max_len: int = MAX_CYCLE_LEN
) -> list[Cycle]:
    """Baseline: match greedily as pairs arrive, executing the first loop that forms.

    Mirrors "first-accept" matching that ignores who else might join later.
    """
    edge_set = set(edges)
    pool: list[str] = []
    executed: list[Cycle] = []
    for pair in arrival_order:
        pool.append(pair)
        sub_edges = [(a, b) for a, b in edge_set if a in pool and b in pool]
        candidates = [c for c in find_cycles(pool, sub_edges, max_len) if pair in c]
        if candidates:
            chosen = max(candidates, key=len)
            executed.append(chosen)
            pool = [p for p in pool if p not in chosen]
    return executed


def transplants(cycles: Iterable[Cycle]) -> int:
    return sum(len(c) for c in cycles)
