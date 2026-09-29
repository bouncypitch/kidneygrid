"""Start KidneyGrid runs on a SuperLink and stream their events.

Uses the same Control API calls as `flwr chat` (build the local FAB, start a
run with a user prompt, stream run events).
"""

import os
from collections.abc import Iterator
from pathlib import Path

from flwr.cli.chat.chat_app import parse_task_event, start_chat_run
from flwr.cli.chat.chat_local_agent import build_local_agent
from flwr.cli.flower_config import read_superlink_connection
from flwr.cli.utils import init_http_client_from_connection
from flwr.proto.control_pb2 import StreamRunEventsRequest  # pylint: disable=E0611

APP_PATH = Path(__file__).resolve().parent.parent
PREFIX = "kidneygrid."


def stream_run(prompt: str, connection: str | None = None, federation: str | None = None) -> Iterator[dict]:
    """Yield KidneyGrid events ({"type": ..., **data}) from a fresh run."""
    conn = read_superlink_connection(connection or os.environ.get("KIDNEYGRID_SUPERLINK", "local-agent"))
    client = init_http_client_from_connection(conn)
    try:
        agent = build_local_agent(APP_PATH)
        run_id, _ = start_chat_run(
            client, prompt, federation or os.environ.get("KIDNEYGRID_FEDERATION") or conn.federation,
            None, agent.app_spec, agent.fab_hash, agent.fab_content,
        )
        yield {"type": "run_started", "run_id": run_id}
        for res in client.StreamRunEvents(StreamRunEventsRequest(run_id=run_id)):
            etype, payload = parse_task_event(res.task_event)
            if etype.startswith(PREFIX):
                yield {"type": etype[len(PREFIX):], **payload.get("data", {})}
            elif etype in {"error", "response.failed", "run.failed"}:
                yield {"type": "error", "detail": payload}
    finally:
        client.close()


if __name__ == "__main__":
    import json
    import sys

    for event in stream_run(" ".join(sys.argv[1:]) or "Run the exchange"):
        brief = {k: v for k, v in event.items() if k not in ("payload", "legs", "nodes", "edges")}
        print(json.dumps(brief)[:200], flush=True)
