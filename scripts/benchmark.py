"""Scale benchmark: siloed hospitals vs first-come national vs KidneyGrid.

Pool generator follows Saidman et al. 2006 as specified in Roth, Sonmez & Unver
(AER 2007, Table 1 and Sec. III.B) and Dickerson's SaidmanPoolGenerator:
patient/donor ABO O .4814 A .3373 B .1428 AB .0385; PRA low/med/high
.7019/.2000/.0981 with positive-crossmatch probability .05/.45/.90; female
patient .4090, spouse donor .4897, spousal crossmatch adjustment 1-.75(1-p)
applied to the patient's own donor only. Assigning pairs to hospitals is our
own modelling choice (uniform). Saidman pools are known to be denser than
real pools, so absolute numbers are optimistic; the siloed-vs-pooled gap is
the point.
"""

import argparse
import json
import random
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from kidneygrid.optimizer import MAX_CYCLE_LEN, find_cycles, myopic_matching

ABO = {"O": 0.4814, "A": 0.3373, "B": 0.1428, "AB": 0.0385}
PRA = [(0.7019, 0.05, "low"), (0.2000, 0.45, "medium"), (0.0981, 0.90, "high")]
CAN_GIVE = {"O": {"O", "A", "B", "AB"}, "A": {"A", "AB"}, "B": {"B", "AB"}, "AB": {"AB"}}


def sample_abo(rng: random.Random) -> str:
    return rng.choices(list(ABO), weights=list(ABO.values()))[0]


def generate(n: int, hospitals: int, rng: random.Random) -> tuple[list[dict], list[tuple[int, int]]]:
    pairs: list[dict] = []
    while len(pairs) < n:
        pt, dn = sample_abo(rng), sample_abo(rng)
        _, pxm, bucket = rng.choices(PRA, weights=[p[0] for p in PRA])[0]
        wife = rng.random() < 0.4090 and rng.random() < 0.4897
        own = 1 - 0.75 * (1 - pxm) if wife else pxm
        compatible = pt in CAN_GIVE[dn] and rng.random() >= own
        if not compatible:  # Only incompatible pairs enter an exchange.
            pairs.append({"pt": pt, "dn": dn, "pxm": pxm, "pra": bucket, "hospital": rng.randrange(hospitals)})
    edges = [
        (i, j)
        for i, a in enumerate(pairs)
        for j, b in enumerate(pairs)
        if i != j and b["pt"] in CAN_GIVE[a["dn"]] and rng.random() >= b["pxm"]
    ]
    return pairs, edges


def optimal(nodes: list[int], edges: list[tuple[int, int]], pairs: list[dict]) -> list[tuple]:
    """Max transplants (small bonus for high-PRA patients), node-disjoint cycles <= 3, via an ILP (SciPy/HiGHS)."""
    names = [str(n) for n in nodes]
    edge_str = [(str(a), str(b)) for a, b in edges]
    cycles = find_cycles(names, edge_str, MAX_CYCLE_LEN)
    if not cycles:
        return []
    weight = np.array([len(c) + sum(0.1 for n in c if pairs[int(n)]["pra"] == "high") for c in cycles])
    index = {n: i for i, n in enumerate(names)}
    a = np.zeros((len(names), len(cycles)))
    for j, c in enumerate(cycles):
        for n in c:
            a[index[n], j] = 1
    res = milp(-weight, constraints=LinearConstraint(a, 0, 1), integrality=np.ones(len(cycles)), bounds=Bounds(0, 1))
    return [c for c, v in zip(cycles, res.x) if v > 0.5]


def count(cycles) -> int:
    return sum(len(c) for c in cycles)


def run_trial(n: int, hospitals: int, seed: int) -> dict:
    rng = random.Random(seed)
    pairs, edges = generate(n, hospitals, rng)
    nodes = list(range(n))

    siloed = []
    for h in range(hospitals):
        own = [i for i in nodes if pairs[i]["hospital"] == h]
        own_set = set(own)
        siloed += optimal(own, [(a, b) for a, b in edges if a in own_set and b in own_set], pairs)

    arrival = nodes[:]
    rng.shuffle(arrival)
    naive = myopic_matching([str(i) for i in arrival], [(str(a), str(b)) for a, b in edges])
    best = optimal(nodes, edges, pairs)

    def high_matched(cycles):
        return sum(1 for c in cycles for node in c if pairs[int(node)]["pra"] == "high")

    return {
        "siloed": count(siloed), "naive": count(naive), "kidneygrid": count(best),
        "high_pra_total": sum(1 for p in pairs if p["pra"] == "high"),
        "high_siloed": high_matched(siloed), "high_naive": high_matched(naive), "high_kidneygrid": high_matched(best),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=300)
    ap.add_argument("--hospitals", type=int, default=10)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "web" / "replays" / "benchmark.json"))
    args = ap.parse_args()

    trials = [run_trial(args.pairs, args.hospitals, args.seed + t) for t in range(args.trials)]
    avg = {k: sum(t[k] for t in trials) / len(trials) for k in trials[0]}
    summary = {
        "pairs": args.pairs, "hospitals": args.hospitals, "trials": args.trials, "seed": args.seed,
        "average": {k: round(v, 1) for k, v in avg.items()},
        "gain_vs_siloed_pct": round(100 * (avg["kidneygrid"] - avg["siloed"]) / max(avg["siloed"], 1), 1),
        "gain_vs_naive_pct": round(100 * (avg["kidneygrid"] - avg["naive"]) / max(avg["naive"], 1), 1),
        "trials_detail": trials,
    }
    Path(args.out).write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "trials_detail"}, indent=1))


if __name__ == "__main__":
    main()
