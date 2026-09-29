"""KidneyGrid AgentApp.

The same app runs on the SuperLink (coordinator) and on every hospital
SuperNode. Its role is decided by which Grid tools the runtime exposes.
Privacy-critical steps run as plain code; the model only writes explanations.
"""

import json
import os
import uuid

from flwr.agentapp import AgentApp, AgentSession
from flwr.app import Context
from openai import OpenAI

from kidneygrid.coordinator import Coordinator
from kidneygrid.exchange import load_local_records, make_agent

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


def _emitter(agent: AgentSession):
    def emit(kind: str, data: dict) -> None:
        print(EVENT_PREFIX + json.dumps({"type": kind, **data}), flush=True)
        agent.events.emit({"type": "kidneygrid." + kind, "data": data})

    return emit


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
    coord = Coordinator(GridTransport(agent), _emitter(agent), _narrator(models))
    result = coord.run(action=action, scenario=scenario)
    agent.events.emit({"type": "message", "role": "assistant", "content": result.get("narrative", json.dumps(result))})


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
