"""KidneyGrid demo server.

    uv run uvicorn web.server:app --port 8765

Replay mode serves recorded event logs; Live mode starts a real run on the
configured SuperLink (KIDNEYGRID_SUPERLINK, default "local-agent") and streams
its events over Server-Sent Events.
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from kidneygrid.exchange import load_hospitals

WEB = Path(__file__).resolve().parent
REPLAYS = WEB / "replays"
PROMPTS = {
    "match": "Run tonight's exchange across the network",
    "confirm": "Approve the plan and notify surgeons",
    "reject": "Approve the plan; surgeon may reject",
    "inject": "Security test: inject attack",
    "cancel": "Approve the plan; an operating room may cancel",
}

app = FastAPI(title="KidneyGrid")
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "static" / "index.html")


@app.get("/api/hospitals")
def hospitals() -> dict:
    """Synthetic records, shown in the UI as 'inside each hospital' for the audience."""
    return load_hospitals()


@app.get("/api/replay/{scenario}")
def replay(scenario: str) -> list[dict]:
    path = REPLAYS / f"{scenario}.json"
    if scenario not in PROMPTS or not path.exists():
        raise HTTPException(404, "unknown scenario")
    return json.loads(path.read_text())


@app.get("/api/benchmark")
def benchmark() -> dict:
    path = REPLAYS / "benchmark.json"
    if not path.exists():
        raise HTTPException(404, "run scripts/benchmark.py first")
    return json.loads(path.read_text())


@app.get("/api/live/{scenario}")
def live(scenario: str) -> StreamingResponse:
    if scenario not in PROMPTS:
        raise HTTPException(404, "unknown scenario")

    def events():
        from web.flower_client import stream_run  # Imported lazily: needs a reachable SuperLink.

        try:
            for event in stream_run(PROMPTS[scenario]):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # Surface failures in the UI instead of a silent stall.
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
        yield "data: {\"type\": \"stream_end\"}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
