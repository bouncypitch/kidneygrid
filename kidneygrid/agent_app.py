"""KidneyGrid AgentApp.

The same app runs on the SuperLink (coordinator) and on every hospital
SuperNode. Its role is decided by which Grid tools the runtime exposes.
Privacy-critical steps run as plain code; the model only writes explanations.
"""

import json
import os
import uuid
from importlib import resources

from flwr.agentapp import AgentApp, AgentSession
from flwr.app import Context
from openai import OpenAI

from kidneygrid.coordinator import Coordinator, LocalTransport
from kidneygrid.exchange import CourierAgent, HospitalAgent, load_local_records, make_agent

EVENT_PREFIX = "KIDNEYGRID_EVENT "
PULL_TIMEOUT = 240

app = AgentApp()


def _grid_call(agent: AgentSession, name: str, arguments: dict) -> dict:
    item = agent.grid.call({"type": "function_call", "name": name, "call_id": f"kg-{uuid.uuid4().hex[:8]}",
                            "arguments": json.dumps(arguments)})
    return json.loads(item["output"])


class GridTransport:
    """Coordinator transport over the Flower federation Grid."""

    def __init__(self, agent: AgentSession):
        self.agent = agent

    def nodes(self) -> list[str]:
        return [n["id"] for n in _grid_call(self.agent, "get_nodes", {"sample_size": None})["nodes"]]

    def send(self, messages: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
        pushed = _grid_call(self.agent, "push_messages", {"messages": [
            {"dst_node_id": node, "payload": json.dumps(payload), "reply_to_message_id": None}
            for node, payload in messages
        ]})["results"]
        ids = {r["message_id"]: node for r, (node, _) in zip(pushed, messages) if r["message_id"]}
        pulled = _grid_call(self.agent, "pull_messages", {"message_ids": list(ids), "timeout": PULL_TIMEOUT})
        replies = []
        for msg in pulled["messages"]:
            node = ids.get(msg["reply_to_message_id"], msg["src_node_id"])
            body = json.loads(msg["payload"]) if msg["payload"] else {"error": msg["error"]}
            replies.append((node, body))
        if pulled["pending_message_ids"]:
            raise RuntimeError(f"No reply from nodes: {[ids[m] for m in pulled['pending_message_ids']]}")
        return sorted(replies, key=lambda r: [n for n, _ in messages].index(r[0]))


def _model_client() -> OpenAI | None:
    if "FLWR_RUNTIME_BASE_URL" not in os.environ:
        return None
    return OpenAI(base_url=os.environ["FLWR_RUNTIME_BASE_URL"], api_key=os.environ["FLWR_RUNTIME_API_KEY"], max_retries=0)


COORDINATOR_INSTRUCTIONS = (
    "You are the KidneyGrid exchange coordinator. In 2-3 warm, plain sentences, explain the result to transplant "
    "surgeons. Use only the facts given. Mention that patient records never left their hospitals.")


def _narrator(models: list[str], instructions: str = COORDINATOR_INSTRUCTIONS):
    client = _model_client()

    def narrate(facts: dict) -> tuple[str, str]:
        """Write with the first model that answers; returns (text, model used)."""
        c = facts.get("counts")
        fallback = (f"Each hospital alone: {c['siloed']} transplants. First-come matching: {c['naive']}. "
                    f"KidneyGrid: {c['optimal']}, with no patient record leaving any hospital.") if c else (
                    "Proposed swap ready for your review.")
        if client is None:
            return fallback, "template"
        for model in models:
            for _attempt in range(2):  # Preview endpoints can fail transiently; retry once before falling back.
                try:
                    resp = client.responses.create(
                        model=model,
                        instructions=instructions,
                        input=json.dumps(facts),
                        max_output_tokens=1200,  # Reasoning models spend part of the budget thinking.
                        reasoning={"effort": "low"},
                    )
                    text = resp.output_text.strip()
                    if len(text) >= 20:  # Reject truncated fragments.
                        return text, model
                except Exception as exc:  # The explanation is optional; the exchange result is not.
                    print(f"[narrator] {model} unavailable: {type(exc).__name__}", flush=True)
        return fallback, "template"

    return narrate


def _chat_line(kind: str, d: dict, names: dict) -> str | None:
    """Human-readable transcript for Flower chat (browser or `flwr chat`)."""
    n = lambda h: names.get(h, h)  # noqa: E731
    if kind == "nodes_found":
        return f"🔎 Found **{d['count']}** organizations on the federation.\n\n"
    if kind == "hospitals":
        names.update({h["id"]: h["name"] for h in d["hospitals"]})
        return "🏥 Hospitals: " + ", ".join(h["name"] for h in d["hospitals"]) + "\n\n"
    if kind == "graph":
        return f"🔒 Each hospital checked every anonymous donor token locally → **{len(d['edges'])}** possible donations. No patient record left any hospital.\n\n"
    if kind == "cycle_rejected_long":
        return f"⛔ Skipped a {len(d['cycle'])}-way loop: it would need {d['surgeries']} simultaneous surgeries.\n\n"
    if kind in ("plan_siloed", "plan_naive", "plan_optimal"):
        label = {"plan_siloed": "Each hospital alone", "plan_naive": "First-come matching", "plan_optimal": "**KidneyGrid**"}[kind]
        return f"- {label}: **{d['transplants']}** transplants\n" + ("\n" if kind == "plan_optimal" else "")
    if kind == "rejected":
        return f"❌ {n(d['leg']['to_hospital'])} surgeon declined a leg ({d['leg']['category']}). Re-planning…\n\n"
    if kind == "briefing":
        who = "Endeavor 1.0" if d.get("model") == "flwrlabs/endeavor-1.0" else d.get("model")
        return f"🩺 {n(d['hospital'])} surgeon briefing ({who}): _{d['text']}_\n\n"
    if kind == "booking_declined":
        return f"🚨 {n(d['hospital'])}: {d['category']} on {d['day']}. Moving the whole loop…\n\n"
    if kind == "schedule_confirmed":
        return "📅 Transplant Day: " + ", ".join(f"loop {chr(65 + int(i))} on {day}" for i, day in d["days"].items()) + "\n\n"
    if kind == "transport_booked":
        ok = [b for b in d["bookings"] if b["booked"]]
        return f"🚐 Courier booked {len(ok)} cold-chain vans (it saw hospitals and days, never patients).\n\n"
    if kind == "reveal":
        pairs = ", ".join(f"{p['patient']} ({n(p['hospital'])})" for p in d["people"].values())
        return f"🎉 Surgeons approved. Identities released only now: {pairs}\n\n"
    if kind == "injection_blocked":
        return f"🛡 Prompt-injection attack refused: \"{d['reply'].get('error')}\". No data returned.\n\n"
    if kind == "narrative":
        return f"{d['text']}\n"
    return None


def _emitter(agent: AgentSession):
    names: dict = {}

    def emit(kind: str, data: dict) -> None:
        print(EVENT_PREFIX + json.dumps({"type": kind, **data}), flush=True)
        agent.events.emit({"type": "kidneygrid." + kind, "data": data})
        line = _chat_line(kind, data, names)
        if line:
            agent.events.emit({"type": "response.output_text.delta", "delta": line})

    return emit


def _demo_transport() -> LocalTransport:
    """Simulated hospitals from bundled synthetic data, for federations without KidneyGrid nodes."""
    data = json.loads(resources.files("kidneygrid").joinpath("demo/demo_data.json").read_text())
    agents = {hid: HospitalAgent(hid, rec) for hid, rec in data["hospitals"].items()}
    courier = dict(data["courier"])
    agents["courier"] = CourierAgent(courier.pop("hospital"), courier)
    return LocalTransport(agents)


def _run_coordinator(agent: AgentSession, context: Context) -> None:
    cfg = context.run_config
    prompt = (agent.prompt or "").lower()
    action = str(cfg.get("action", "match"))
    if "approve" in prompt or "confirm" in prompt:
        action = "confirm"
    elif "attack" in prompt or "inject" in prompt:
        action = "inject"
    scenario = "surgeon-reject" if ("reject" in prompt or cfg.get("reject-edge")) else ""
    if "cancel" in prompt:
        action, scenario = "confirm", "or-cancel"
    models = [str(cfg.get("model", "flwrlabs/endeavor-1.0")), str(cfg.get("fallback-model", "openai/gpt-5.6-sol"))]
    emit = _emitter(agent)
    try:
        transport = GridTransport(agent)
        if not transport.nodes():
            agent.events.emit({"type": "response.output_text.delta", "delta": (
                "ℹ️ No KidneyGrid hospital nodes in this federation, so this is a **simulated** 5-hospital exchange "
                "with synthetic data. For the live network, run in federation `@kdotmahesh/kidneygrid`.\n\n")})
            transport = _demo_transport()
        result = Coordinator(transport, emit, _narrator(models)).run(action=action, scenario=scenario)
    except Exception as exc:
        agent.events.emit({"type": "response.output_text.delta", "delta": f"\n⚠️ KidneyGrid run failed: {type(exc).__name__}: {exc}\n"})
        raise
    finally:
        # Flower chat waits for a terminal event before it considers the answer complete.
        agent.events.emit({"type": "response.completed"})


def _run_hospital(agent: AgentSession, context: Context) -> None:
    envelope = json.loads(agent.prompt)
    try:
        message = json.loads(envelope.get("payload", "{}"))
    except json.JSONDecodeError:
        message = {"type": envelope.get("payload", "")}
    # Each hospital's records live on its own SuperNode's disk, never in the app bundle.
    records_path = str(context.node_config.get("records", ""))
    try:
        hospital_id, record = load_local_records(records_path)
    except (OSError, ValueError, KeyError):
        reply = {"error": "no local hospital records configured on this node"}
    else:
        reply = make_agent(hospital_id, record).handle(message)
        if message.get("type") == "CONFIRM" and reply.get("decisions"):
            reply["briefing"], reply["briefing_model"] = _surgeon_briefing(context, record, reply["decisions"])
    _grid_call(agent, "push_reply_message", {"payload": json.dumps(reply)})


def _surgeon_briefing(context: Context, record: dict, decisions: list[dict]) -> tuple[str, str]:
    """This hospital's model writes a short note for its own surgeon, from non-identifying facts only."""
    patient = record["pairs"][0]["patient"]
    facts = {
        "hospital": record["display_name"],
        "patient_highly_sensitized": patient["cpra"] >= 80,
        "incoming_kidneys": [
            {"from_hospital": d.get("from_hospital"), "decision": d["category"]} for d in decisions
        ],
    }
    cfg = context.run_config
    models = [str(cfg.get("model", "flwrlabs/endeavor-1.0")), str(cfg.get("fallback-model", "openai/gpt-5.6-sol"))]
    narrate = _narrator(models, instructions=(
        "You are the transplant coordinator agent inside this hospital. Write ONE short sentence (max 30 words) "
        "briefing the surgeon on the proposed kidney swap, using only the facts given. No names."))
    return narrate(facts)


@app.main()
def main(agent: AgentSession, context: Context) -> None:
    tool_names = {t["name"] for t in agent.grid.tools()}
    if "get_nodes" in tool_names:
        _run_coordinator(agent, context)
    else:
        _run_hospital(agent, context)
