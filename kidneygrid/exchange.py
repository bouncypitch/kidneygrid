"""Protocol logic shared by the Flower AgentApp and the offline replay.

Hospital-side functions only ever see their own records. Coordinator-side
functions only ever see what hospitals chose to send: anonymous donor tokens,
patient pseudonyms, a coarse sensitization bucket and yes/no compatibility.
"""

import hashlib
import hmac
import json
from importlib import resources

from kidneygrid.compat import is_compatible
from kidneygrid.optimizer import (
    MAX_CYCLE_LEN,
    SENSITIZED_CPRA,
    best_packing,
    find_cycles,
    myopic_matching,
    transplants,
)

# Message types a hospital node will answer. Anything else is refused.
REGISTER, CHECK, CONFIRM, REVEAL = "REGISTER", "CHECK", "CONFIRM", "REVEAL"
ALLOWED_TYPES = frozenset({REGISTER, CHECK, CONFIRM, REVEAL})


def load_hospitals() -> dict[str, dict]:
    raw = resources.files("kidneygrid").joinpath("data/hospitals.json").read_text()
    return json.loads(raw)["hospitals"]


def _pseudonym(secret: str, salt: str, kind: str, pair_id: str) -> str:
    digest = hmac.new(secret.encode(), f"{salt}:{kind}:{pair_id}".encode(), hashlib.sha256)
    return f"{kind}-{digest.hexdigest()[:6]}"


def _cpra_bucket(cpra: int) -> str:
    if cpra >= SENSITIZED_CPRA:
        return "high"
    return "medium" if cpra >= 20 else "low"


# ---------------------------------------------------------------- hospital side


class HospitalAgent:
    """Answers protocol messages from a single hospital's private records."""

    def __init__(self, hospital_id: str, record: dict, secret: str | None = None):
        self.hospital_id = hospital_id
        self.record = record
        self.secret = secret or f"local-secret-{hospital_id}"

    def _ids(self, salt: str, pair: dict) -> tuple[str, str]:
        pid = pair["pair_id"]
        return _pseudonym(self.secret, salt, "D", pid), _pseudonym(self.secret, salt, "P", pid)

    def handle(self, message: dict) -> dict:
        mtype = message.get("type")
        if mtype not in ALLOWED_TYPES:
            return {"hospital": self.hospital_id, "error": "unsupported request"}
        salt = str(message.get("salt", ""))
        if mtype == REGISTER:
            return self.register(salt)
        if mtype == CHECK:
            return self.check(salt, message.get("donors", []))
        if mtype == CONFIRM:
            return self.confirm(salt, message.get("legs", []), message.get("scenario", ""))
        return self.reveal(salt, message.get("legs", []))

    def register(self, salt: str) -> dict:
        pairs = []
        for pair in self.record["pairs"]:
            donor_token, patient_token = self._ids(salt, pair)
            pairs.append(
                {
                    "donor_token": donor_token,
                    "patient_token": patient_token,
                    # Donor typing leaves as an anonymous token; the patient's
                    # antibody profile never leaves.
                    "donor_abo": pair["donor"]["abo"],
                    "donor_hla": pair["donor"]["hla"],
                    "patient_sensitization": _cpra_bucket(pair["patient"]["cpra"]),
                }
            )
        return {
            "hospital": self.hospital_id,
            "display_name": self.record["display_name"],
            "arrival": self.record.get("arrival", 0),
            "pairs": pairs,
        }

    def check(self, salt: str, donors: list[dict]) -> dict:
        """Virtual crossmatch every donor token against local patients."""
        compatible = []
        for pair in self.record["pairs"]:
            own_donor, patient_token = self._ids(salt, pair)
            for donor in donors:
                if donor["donor_token"] == own_donor:
                    continue
                if is_compatible({"abo": donor["donor_abo"], "hla": donor["donor_hla"]}, pair["patient"]):
                    compatible.append({"donor_token": donor["donor_token"], "patient_token": patient_token})
        return {
            "hospital": self.hospital_id,
            "checked": len(donors) * len(self.record["pairs"]),
            "compatible": compatible,
        }

    def confirm(self, salt: str, legs: list[dict], scenario: str) -> dict:
        """Surgeon sign-off on legs where this hospital's patient receives a kidney."""
        holds = self.record.get("holds", {}).get(scenario, {})
        decisions = []
        for pair in self.record["pairs"]:
            _, patient_token = self._ids(salt, pair)
            for leg in legs:
                if leg["patient_token"] != patient_token:
                    continue
                held = holds.get("pair_id") == pair["pair_id"]
                decisions.append(
                    {
                        **leg,
                        "approved": not held,
                        # The clinical reason stays local; only a category leaves.
                        "category": "physical crossmatch positive" if held else "approved",
                    }
                )
        return {"hospital": self.hospital_id, "decisions": decisions}

    def reveal(self, salt: str, legs: list[dict]) -> dict:
        """After all approvals: disclose identities only for this hospital's legs."""
        people = []
        for pair in self.record["pairs"]:
            donor_token, patient_token = self._ids(salt, pair)
            if any(leg["patient_token"] == patient_token or leg["donor_token"] == donor_token for leg in legs):
                people.append(
                    {
                        "donor_token": donor_token,
                        "patient_token": patient_token,
                        "patient": pair["patient"]["name"],
                        "donor": pair["donor"]["name"],
                        "relation": pair["donor"]["relation"],
                        "years_waiting": pair["patient"]["years_waiting"],
                    }
                )
        return {"hospital": self.hospital_id, "people": people}


# ------------------------------------------------------------- coordinator side


class ExchangeGraph:
    """Anonymous compatibility graph built only from hospital replies."""

    def __init__(self, registrations: list[dict], checks: list[dict]):
        self.owner: dict[str, str] = {}  # pair node -> hospital id
        self.by_donor: dict[str, str] = {}
        self.by_patient: dict[str, str] = {}
        self.sensitization: dict[str, str] = {}
        self.arrival: dict[str, int] = {}
        for reg in registrations:
            for pair in reg["pairs"]:
                node = pair["patient_token"]
                self.owner[node] = reg["hospital"]
                self.by_donor[pair["donor_token"]] = node
                self.by_patient[pair["patient_token"]] = node
                self.sensitization[node] = pair["patient_sensitization"]
                self.arrival[node] = reg.get("arrival", 0)
        self.edges: list[tuple[str, str]] = sorted(
            {
                (self.by_donor[c["donor_token"]], self.by_patient[c["patient_token"]])
                for chk in checks
                for c in chk["compatible"]
                if c["donor_token"] in self.by_donor and c["patient_token"] in self.by_patient
            }
        )
        self.nodes = sorted(self.owner)
        self.donor_of = {node: donor for donor, node in self.by_donor.items()}

    def cpra_weights(self) -> dict[str, int]:
        return {n: 100 if s == "high" else 0 for n, s in self.sensitization.items()}

    def legs(self, cycles: list[tuple[str, ...]]) -> list[dict]:
        out = []
        for cyc in cycles:
            for i, src in enumerate(cyc):
                dst = cyc[(i + 1) % len(cyc)]
                out.append(
                    {
                        "donor_token": self.donor_of[src],
                        "patient_token": dst,
                        "from_hospital": self.owner[src],
                        "to_hospital": self.owner[dst],
                    }
                )
        return out


def plan_exchange(graph: ExchangeGraph, excluded: set[tuple[str, str]] | None = None) -> dict:
    """Compare siloed, first-come and optimized matching on the same graph."""
    excluded = excluded or set()
    edges = [e for e in graph.edges if e not in excluded]
    all_cycles = find_cycles(graph.nodes, edges, max_len=len(graph.nodes))
    allowed = [c for c in all_cycles if len(c) <= MAX_CYCLE_LEN]
    too_long = [c for c in all_cycles if len(c) > MAX_CYCLE_LEN]

    siloed = []
    for hospital in sorted(set(graph.owner.values())):
        own = [n for n in graph.nodes if graph.owner[n] == hospital]
        own_edges = [(a, b) for a, b in edges if a in own and b in own]
        siloed += best_packing(find_cycles(own, own_edges, MAX_CYCLE_LEN), graph.cpra_weights())

    arrival_order = sorted(graph.nodes, key=lambda n: (graph.arrival[n], n))
    naive = myopic_matching(arrival_order, edges)
    optimal = best_packing(allowed, graph.cpra_weights())
    return {
        "cycles": allowed,
        "too_long": too_long,
        "siloed": siloed,
        "naive": naive,
        "optimal": optimal,
        "counts": {
            "siloed": transplants(siloed),
            "naive": transplants(naive),
            "optimal": transplants(optimal),
        },
    }
