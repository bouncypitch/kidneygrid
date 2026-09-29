---
tags: [agentapp, healthcare, privacy, collaborative-agents]
dataset: []
framework: [flower-agent]
---

# KidneyGrid

**Kidney swaps across hospitals, with no patient data shared.**

95,492 people in the US are waiting for a kidney (OPTN, July 2026). Many have a loved one willing to donate
who is the wrong match: at least a third of patients with a willing living donor are blocked by blood type or
crossmatch incompatibility (Segev et al., JAMA 2005). Paired exchange fixes this by swapping donors between
couples, but the couples are usually at different hospitals, and hospitals can't pool patient records:
62% of US exchange transplants stayed within one hospital, and fixing that fragmentation could add 30–63%
more transplants (Agarwal, Ashlagi et al., AER 2019).

KidneyGrid puts a Flower agent in every hospital. Hospitals share only anonymous donor typing tokens and
yes/no compatibility answers; a coordinator agent finds the best swap loops; surgeons approve before any
identity is revealed.

## How it works

```
Coordinator AgentApp (SuperLink)                 Hospital AgentApp (one SuperNode per hospital)
 1. get_nodes
 2. push REGISTER ─────────────────────────────▶ anonymous donor tokens (ABO + HLA), pseudonyms, cPRA bucket
 3. push CHECK (all tokens) ───────────────────▶ virtual crossmatch vs. OWN patients' antibodies → yes/no only
 4. anonymous graph → best loops (≤3-way, sensitized priority) vs. first-come baseline
 5. push CONFIRM ──────────────────────────────▶ surgeon approves / declines (category only; reason stays local)
 6. re-plan if declined → push REVEAL ─────────▶ identities released only for approved legs
```

* **One AgentApp, two roles.** The same FAB runs on the SuperLink and on every SuperNode; the role is picked
  from the Grid tools the runtime exposes (`get_nodes/push_messages/pull_messages` vs. `push_reply_message`).
* **Privacy enforced in code, not prompts.** Hospital agents answer only four message types with deterministic
  handlers; the model never sees private records. A prompt-injection request returns `unsupported request`.
* **The model explains.** The coordinator uses the runtime's model endpoint to explain the plan from redacted facts.

## Results

| Scenario | Each hospital alone | First-come matching | KidneyGrid |
|---|---|---|---|
| Demo: 5 couples, 5 hospitals | 0 | 3 (Maria left out) | **5** |
| Simulated: 300 pairs, 10 hospitals (avg of 5) | 126 | 160 | **178 (+41%)** |
| Highly sensitized patients matched (simulated) | 24 | 35 | **57 (2.4×)** |

Simulated pools follow Saidman et al. (2006) as specified by Roth, Sönmez & Ünver (AER 2007); hospital
assignment is uniform. Saidman pools are denser than real ones, so absolute counts are optimistic.

## Run it

```shell
uv sync
uv run pytest                                  # compatibility + optimizer scenarios
scripts/local_stack.sh                         # local SuperLink + 5 hospital SuperNodes
uv run python -m web.flower_client "Run the exchange"   # one live run, events to stdout
uv run uvicorn web.server:app --port 8765      # demo UI at http://127.0.0.1:8765
```

Local runs need `[superlink.local-agent]` (address `127.0.0.1:8000`, `insecure = true`) in `~/.flwr/config.toml`.
On SuperGrid: `uv run flwr login supergrid`, then set `KIDNEYGRID_SUPERLINK=supergrid` and
`KIDNEYGRID_FEDERATION=@<account>/<federation>` for the web app's Live mode. Hospital nodes are started with
`--node-config 'hospital="<id>"'`.

Demo keys: `1` match · `2` approve · `3` surgeon rejects · `4` prompt-injection attack · `S` scale · `P` peek
at private records · `L` toggle Live/Replay.

Other scripts: `scripts/make_replay.py` (Replay-mode event logs), `scripts/benchmark.py` (scale study),
`scripts/family_pdf.py` (one-page explainer), `video/` (Remotion film and script).

## Data and scope

All people, hospitals and records are fictional and synthetic. Compatibility is simplified (ABO + virtual
crossmatch); real programs add antibody strength, donor age/size and logistics as further local checks.
KidneyGrid is a hackathon prototype, not a medical device.

Built for the Flower Collaborative Agent Hackathon, Stanford, September 29, 2026.
