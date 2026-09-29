"""Record coordinator event logs for the web app's Replay mode.

Runs the real protocol in-process (LocalTransport) so replays match what the
Flower deployment emits, event for event.
"""

import json
from pathlib import Path

from kidneygrid.coordinator import Coordinator, LocalTransport
from kidneygrid.exchange import CourierAgent, HospitalAgent, load_hospitals

OUT = Path(__file__).resolve().parent.parent / "web" / "replays"
SCENARIOS = {
    "match": dict(action="match"),
    "confirm": dict(action="confirm"),
    "reject": dict(action="confirm", scenario="surgeon-reject"),
    "inject": dict(action="inject"),
    "cancel": dict(action="confirm", scenario="or-cancel"),
}


def record(action: str, scenario: str = "") -> list[dict]:
    hospitals = load_hospitals()
    # Node ids mimic Flower's uint64 SuperNode ids.
    agents = {str(1_000_000 + i * 7919): HospitalAgent(hid, rec) for i, (hid, rec) in enumerate(hospitals.items(), 1)}
    courier = json.loads((Path(__file__).resolve().parent.parent / "data" / "nodes" / "golden-gate-courier.json").read_text())
    agents["9990001"] = CourierAgent(courier.pop("hospital"), courier)
    events: list[dict] = []
    Coordinator(LocalTransport(agents), lambda kind, data: events.append({"type": kind, **data})).run(
        action=action, scenario=scenario, salt="demo"
    )
    return events


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, kwargs in SCENARIOS.items():
        events = record(**kwargs)
        (OUT / f"{name}.json").write_text(json.dumps(events, indent=1))
        done = next(e for e in events if e["type"] == "done")
        print(f"{name:8s} {len(events):3d} events  {done}")


if __name__ == "__main__":
    main()
