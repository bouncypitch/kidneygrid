// KidneyGrid live demo: renders coordinator events from Replay logs or live Flower runs.

const $ = (s) => document.querySelector(s);
const svg = $("#net");
const NS = "http://www.w3.org/2000/svg";
const HUB = { x: 400, y: 300 };
const RADIUS = 235;

const state = {
  mode: "replay",
  busy: false,
  hospitals: {},        // hospital id -> private record (audience view)
  nodes: [],            // SuperNode ids in discovery order
  pos: {},              // node id -> {x, y}
  hospitalOf: {},       // node id -> hospital id
  nodeOf: {},           // hospital id -> node id
  owner: {},            // patient token -> hospital id
  queue: [],
  draining: false,
};

// Pacing so every step is visible on a projector.
const DELAY = {
  nodes_found: 700, hospitals: 500, msg_sent: 110, msg_received: 170, graph: 1100,
  cycle_rejected_long: 2400, plan_siloed: 1300, plan_naive: 2000, plan_optimal: 2200,
  approval_requested: 1400, rejected: 2600, replanned: 1200, confirmed: 1200, reveal: 1200,
  injection_blocked: 1800, narrative: 400, done: 0, courier: 200,
  schedule_requested: 1200, schedule_proposed: 1800, booking_declined: 2600, schedule_confirmed: 1600, transport_booked: 1800,
};

const el = (tag, attrs = {}, parent = svg) => {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  parent.appendChild(n);
  return n;
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const short = (id) => "…" + String(id).slice(-4);
const hname = (hid) => state.hospitals[hid]?.display_name || hid;

function fmtDay(iso) {
  return new Date(iso + "T12:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function status(text) { $("#status").textContent = text; }

function banner(text, kind = "", ms = 2600) {
  const b = $("#banner");
  b.className = "banner show " + kind;
  b.textContent = text;
  clearTimeout(banner.t);
  banner.t = setTimeout(() => (b.className = "banner " + kind), ms);
}

function setScore(id, value) {
  const s = $("#s-" + id);
  s.querySelector(".num").textContent = value;
  s.classList.add("bump");
  setTimeout(() => s.classList.remove("bump"), 350);
}

// ------------------------------------------------------------------ layout

function drawHospitalCards() {
  const wrap = $("#hospitals");
  wrap.innerHTML = "";
  for (const [hid, rec] of Object.entries(state.hospitals)) {
    const pair = rec.pairs[0];
    const node = state.nodeOf[hid];
    wrap.insertAdjacentHTML("beforeend", `
      <div class="hcard" id="card-${hid}">
        <div class="hname">${rec.display_name}<span class="node">${node ? "node " + short(node) : "SuperNode"}</span></div>
        <div class="private">
          <div class="row"><span>Patient: <b>${pair.patient.name}</b> · type ${pair.patient.abo}</span><span class="tag">cPRA ${pair.patient.cpra}%</span></div>
          <div class="row"><span>Donor: ${pair.donor.name} (${pair.donor.relation}) · type ${pair.donor.abo}</span><span class="tag">${pair.patient.years_waiting} yrs</span></div>
          <div class="tag">Antibodies: ${pair.patient.unacceptable.slice(0, 6).join(" ")}${pair.patient.unacceptable.length > 6 ? " …" : ""}</div>
        </div>
      </div>`);
  }
}

function drawNetwork(nodes) {
  svg.innerHTML = "";
  el("g", { id: "links" });
  el("g", { id: "compat" });
  el("g", { id: "loops" });
  el("g", { id: "packets" });
  const nodeLayer = el("g", { id: "nodes" });
  state.pos = {};
  nodes.forEach((n, i) => {
    const a = (-90 + (360 / nodes.length) * i) * (Math.PI / 180);
    state.pos[n] = { x: HUB.x + RADIUS * Math.cos(a), y: HUB.y + RADIUS * Math.sin(a) };
    el("line", { class: "link", x1: HUB.x, y1: HUB.y, x2: state.pos[n].x, y2: state.pos[n].y }, $("#links"));
    const g = el("g", { class: "hnode", id: "n-" + n }, nodeLayer);
    el("circle", { cx: state.pos[n].x, cy: state.pos[n].y, r: 54 }, g);
    const t = el("text", { x: state.pos[n].x, y: state.pos[n].y - 1, "font-size": 12.5, "font-weight": 700 }, g);
    t.textContent = n.startsWith("pending") ? "Hospital" : "SuperNode";
    const s = el("text", { x: state.pos[n].x, y: state.pos[n].y + 15, "font-size": 11, fill: "#6e5f69" }, g);
    s.textContent = n.startsWith("pending") ? "" : short(n);
  });
  const hub = el("g", { class: "hub" }, nodeLayer);
  el("circle", { cx: HUB.x, cy: HUB.y, r: 56 }, hub);
  el("text", { x: HUB.x, y: HUB.y - 4, "font-size": 14, "font-weight": 800 }, hub).textContent = "Coordinator";
  el("text", { x: HUB.x, y: HUB.y + 14, "font-size": 11, fill: "#f3d9f0" }, hub).textContent = "SuperLink";
}

function labelNodes() {
  for (const n of state.nodes) {
    const hid = state.hospitalOf[n];
    if (!hid) continue;
    const texts = document.querySelectorAll(`#n-${n} text`);
    const words = hname(hid).split(" ");
    texts[0].textContent = words.slice(0, 2).join(" ");
    texts[1].textContent = words.slice(2).join(" ") || short(n);
  }
  drawHospitalCards();
}

// ------------------------------------------------------------- animations

function packet(node, outbound, color) {
  const p = state.pos[node];
  if (!p) return;
  const dot = el("circle", { r: 6, fill: color }, $("#packets"));
  const [from, to] = outbound ? [HUB, p] : [p, HUB];
  const start = performance.now();
  const dur = 520;
  (function step(now) {
    const t = Math.min(1, (now - start) / dur);
    const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    dot.setAttribute("cx", from.x + (to.x - from.x) * e);
    dot.setAttribute("cy", from.y + (to.y - from.y) * e);
    if (t < 1) requestAnimationFrame(step);
    else dot.remove();
  })(start);
  flash(node);
}

function flash(node) {
  const hid = state.hospitalOf[node];
  const g = document.getElementById("n-" + node);
  g?.classList.add("on");
  const card = hid && document.getElementById("card-" + hid);
  card?.classList.add("active");
  setTimeout(() => { g?.classList.remove("on"); card?.classList.remove("active"); }, 600);
}

function curve(fromNode, toNode, bend = 0.28) {
  const a = state.pos[fromNode], b = state.pos[toNode];
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
  // Bend towards the hub so loops read as a ring inside the network.
  const cx = mx + (HUB.x - mx) * bend, cy = my + (HUB.y - my) * bend;
  const shrink = (p, q) => { const d = Math.hypot(q.x - p.x, q.y - p.y); return { x: p.x + ((q.x - p.x) * 58) / d, y: p.y + ((q.y - p.y) * 58) / d }; };
  const s = shrink(a, { x: cx, y: cy }), e = shrink(b, { x: cx, y: cy });
  return { d: `M${s.x},${s.y} Q${cx},${cy} ${e.x},${e.y}`, mid: { x: 0.25 * s.x + 0.5 * cx + 0.25 * e.x, y: 0.25 * s.y + 0.5 * cy + 0.25 * e.y } };
}

function ensureArrow(id, color) {
  if (document.getElementById(id)) return;
  let defs = svg.querySelector("defs") || el("defs");
  const m = el("marker", { id, viewBox: "0 0 10 10", refX: 7, refY: 5, markerWidth: 5, markerHeight: 5, orient: "auto-start-reverse" }, defs);
  el("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: color }, m);
}

function drawLegs(legs, cls) {
  const layer = $("#loops");
  layer.querySelectorAll(".loop." + cls).forEach((n) => n.remove());
  const color = { opt: "#0e9f6e", naive: "#d97706", rejected: "#dc2626" }[cls];
  ensureArrow("arrow-" + cls, color);
  const drawn = [];
  legs.forEach((leg, i) => {
    const a = state.nodeOf[leg.from_hospital], b = state.nodeOf[leg.to_hospital];
    if (!a || !b) return;
    const { d } = curve(a, b, cls === "naive" ? 0.45 : 0.28);
    const path = el("path", { class: "loop " + cls, d, "marker-end": `url(#arrow-${cls})` }, layer);
    const len = path.getTotalLength();
    path.style.strokeDasharray = cls === "naive" ? "10 8" : `${len}`;
    if (cls !== "naive") {
      path.style.strokeDashoffset = len;
      path.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: 700, delay: i * 260, fill: "forwards", easing: "ease-out" });
    }
    drawn.push(path);
  });
  return drawn;
}

function legsFromCycles(cycles) {
  const legs = [];
  for (const c of cycles) c.forEach((src, i) => legs.push({ from_hospital: state.owner[src], to_hospital: state.owner[c[(i + 1) % c.length]] }));
  return legs;
}

// ------------------------------------------------------------------ ledger

function summarize(ev) {
  const p = ev.payload || {};
  if (ev.type === "msg_sent") {
    if (ev.round === "ATTACK") return `ATTACK: "${String(p.type).slice(0, 38)}…"`;
    if (ev.round === "CHECK") return `CHECK ${p.donors?.length ?? 0} anonymous donor tokens`;
    if (ev.round === "CONFIRM") return `CONFIRM ${p.legs?.length ?? 0} proposed legs`;
    if (ev.round === "REVEAL") return `REVEAL request (after approval)`;
    if (ev.round === "SCHEDULE") return `SCHEDULE ${p.requests?.length ?? 0} loop(s), ${p.requests?.[0]?.days?.length ?? 0} candidate days`;
    if (ev.round === "BOOK") return `BOOK ${p.bookings?.map((b) => b.day.slice(5)).join(", ")}`;
    if (ev.round === "TRANSPORT") return `TRANSPORT ${p.legs?.length ?? 0} kidney(s): hospitals + day only`;
    return `${ev.round} request`;
  }
  if (p.error) return `refused: "${p.error}"`;
  if (ev.round === "REGISTER" && p.role === "courier") return `courier registered (no patient data)`;
  if (ev.round === "REGISTER") return `${p.pairs.length} donor token(s): ${p.pairs.map((x) => x.donor_token).join(", ")}`;
  if (ev.round === "CHECK") return `${p.compatible.length} yes-answer(s) of ${p.checked} checks`;
  if (ev.round === "CONFIRM") return p.decisions.map((d) => (d.approved ? "approved" : "declined: " + d.category)).join(", ") || "no legs here";
  if (ev.round === "REVEAL") return `${p.people.length} identity released (consented)`;
  if (ev.round === "SCHEDULE") return p.availability.map((a) => `${a.days.length} day(s) free`).join(", ");
  if (ev.round === "BOOK") return p.results.map((r) => (r.booked ? `booked ${r.day.slice(5)}` : `declined ${r.day.slice(5)}: ${r.category}`)).join(", ");
  if (ev.round === "TRANSPORT") return `${p.bookings.filter((b) => b.booked).length} van(s) booked`;
  return ev.round;
}

function ledger(ev) {
  const out = ev.type === "msg_sent";
  const node = out ? ev.to : ev.from;
  const who = (node === state.courierNode && state.courierName) || hname(state.hospitalOf[node]) || "node " + short(node);
  const bad = !out && ev.payload?.error;
  const row = document.createElement("div");
  row.className = "lrow";
  row.innerHTML = `<span class="dir ${out ? "out" : bad ? "bad" : "in"}">${out ? "→" : "←"}</span>
    <span>${who} · ${summarize(ev)}</span><span class="bytes">${ev.bytes} B</span>
    <pre></pre>`;
  row.querySelector("pre").textContent = JSON.stringify(ev.payload, null, 1);
  row.onclick = () => row.classList.toggle("open");
  const box = $("#ledger");
  box.appendChild(row);
  box.scrollTop = box.scrollHeight;
}

// ---------------------------------------------------------------- handlers

const handlers = {
  run_started: (e) => status(`Flower run ${short(e.run_id)} started on the SuperLink…`),
  nodes_found: (e) => {
    state.nodes = e.nodes;
    drawNetwork(e.nodes);
    labelNodes();
    status(`Coordinator found ${e.count} hospital SuperNodes on the federation.`);
  },
  msg_sent: (e) => {
    if (e.round === "REGISTER" && !state.announced) { status("Asking each hospital for anonymous donor tokens…"); state.announced = true; }
    if (e.round === "CHECK" && state.phase !== "check") { status("Each hospital checks every donor token against its own patients, locally."); state.phase = "check"; }
    if (e.round === "CONFIRM" && state.phase !== "confirm") { status("Asking each hospital's surgeon to approve…"); state.phase = "confirm"; }
    packet(e.to, true, e.round === "ATTACK" ? "#dc2626" : "#5b1a63");
    ledger(e);
  },
  msg_received: (e) => { packet(e.from, false, e.payload?.error ? "#dc2626" : "#0e9f6e"); ledger(e); },
  hospitals: (e) => {
    for (const h of e.hospitals) { state.hospitalOf[h.node] = h.id; state.nodeOf[h.id] = h.node; }
    labelNodes();
  },
  graph: (e) => {
    for (const n of e.nodes) state.owner[n.id] = n.hospital;
    const layer = $("#compat");
    layer.innerHTML = "";
    for (const edge of e.edges) {
      const a = state.nodeOf[state.owner[edge.from]], b = state.nodeOf[state.owner[edge.to]];
      if (a && b) el("path", { class: "compat", d: curve(a, b, 0.12).d }, layer);
    }
    status(`Anonymous compatibility map: ${e.edges.length} possible donations. The coordinator never saw a single record.`);
  },
  cycle_rejected_long: (e) => banner(`${e.cycle.length}-way loop found, rejected: needs ${e.surgeries} simultaneous surgeries`, "", 2300),
  plan_siloed: (e) => { setScore("siloed", e.transplants); status(`Each hospital on its own: ${e.transplants} transplants.`); },
  plan_naive: (e) => {
    setScore("naive", e.transplants);
    drawLegs(legsFromCycles(e.cycles), "naive");
    status(`First-come matching grabs the first loop it finds: ${e.transplants} transplants. Maria is left out.`);
  },
  plan_optimal: (e) => {
    $("#loops").querySelectorAll(".loop.naive").forEach((n) => n.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 500, fill: "forwards" }));
    setTimeout(() => $("#loops").querySelectorAll(".loop.naive").forEach((n) => n.remove()), 520);
    setScore("optimal", e.transplants);
    drawLegs(e.legs, "opt");
    for (const hid of new Set(e.legs.flatMap((l) => [l.from_hospital, l.to_hospital]))) {
      document.getElementById("n-" + state.nodeOf[hid])?.classList.add("matched");
    }
    status(`KidneyGrid finds ${e.transplants} transplants, prioritizing the hardest-to-match patients.`);
  },
  approval_requested: () => status("Plan ready. Nothing is final until every surgeon approves."),
  rejected: (e) => {
    const leg = e.leg;
    const legs = drawLegs([leg], "rejected");
    const mid = curve(state.nodeOf[leg.from_hospital], state.nodeOf[leg.to_hospital]).mid;
    el("text", { class: "xmark", x: mid.x, y: mid.y + 10 }, $("#loops")).textContent = "✕";
    legs.forEach((p) => p.animate([{ opacity: 1 }, { opacity: 0.35 }], { duration: 1600, fill: "forwards" }));
    banner(`${hname(leg.to_hospital)} surgeon declined a leg: ${leg.category}`, "", 2600);
    status(`${hname(leg.to_hospital)} declined. The reason stays at the hospital; only a category is shared.`);
  },
  replanned: (e) => {
    $("#loops").innerHTML = "";
    document.querySelectorAll(".hnode.matched").forEach((n) => n.classList.remove("matched"));
    status(`Re-planning around the declined leg…`);
  },
  confirmed: () => banner("All surgeons approved", "good", 1800),
  reveal: (e) => {
    const people = Object.values(e.people);
    const byDonor = Object.fromEntries(people.map((p) => [p.donor_token, p]));
    const maxYears = Math.max(...people.map((p) => p.years_waiting));
    const box = $("#reveal");
    box.innerHTML = "";
    e.legs.forEach((leg, i) => {
      const giver = byDonor[leg.donor_token], receiver = e.people[leg.patient_token];
      if (!giver || !receiver) return;
      const star = receiver.years_waiting === maxYears;
      setTimeout(() => box.insertAdjacentHTML("beforeend", `
        <div class="person ${star ? "star" : ""}"><b>${giver.donor}</b> → <b>${receiver.patient}</b>
        <div class="meta">${hname(giver.hospital)} → ${hname(receiver.hospital)}${star ? ` · waited ${receiver.years_waiting} years` : ""}</div></div>`), i * 350);
      document.getElementById("card-" + receiver.hospital)?.classList.add("matched");
    });
    status(`Identities revealed only now, after consent. ${e.legs.length} families, one gift each.`);
  },
  courier: (e) => {
    state.courierNode = e.node;
    state.courierName = e.name;
    const g = document.getElementById("n-" + e.node);
    if (g) {
      g.classList.add("courier");
      const t = g.querySelectorAll("text");
      t[0].textContent = "Courier";
      t[1].textContent = "Golden Gate";
    }
  },
  schedule_requested: () => {
    $("#reveal").innerHTML = "";
    status("Transplant Day: each hospital checks its own operating rooms and beds, privately.");
  },
  schedule_proposed: (e) => {
    const loops = Object.keys(e.days);
    const box = $("#day");
    if (!box.querySelector(".day-title")) box.innerHTML = `<div class="day-title">Transplant Day <span>all surgeries in a loop happen together</span></div>`;
    loops.forEach((i) => {
      let row = document.getElementById("loop-" + i);
      if (!row) {
        row = document.createElement("div");
        row.className = "loop-row";
        row.id = "loop-" + i;
        row.innerHTML = `<div class="loop-head"><span><b>Loop ${String.fromCharCode(65 + +i)}</b> · ${e.hospitals[i].map(hname).join(", ")}</span><span class="dates"></span></div><div class="vans"></div>`;
        box.appendChild(row);
      }
      const dates = row.querySelector(".dates");
      dates.querySelectorAll(".proposed").forEach((d) => d.remove());
      dates.insertAdjacentHTML("beforeend", `<span class="date proposed">${fmtDay(e.days[i])}</span>`);
    });
    status("Coordinator proposes the earliest day every hospital in each loop can do.");
  },
  booking_declined: (e) => {
    const d = document.querySelector(`#loop-${e.cycle} .date.proposed`);
    if (d) { d.className = "date struck"; }
    banner(`${hname(e.hospital)}: ${e.category} on ${fmtDay(e.day)}. Re-planning the whole loop.`, "", 2600);
    status(`${hname(e.hospital)} lost its operating room. Every surgery in the loop must move together.`);
  },
  schedule_confirmed: (e) => {
    Object.entries(e.days).forEach(([i]) => {
      const row = document.getElementById("loop-" + i);
      const d = row?.querySelector(".date.proposed");
      if (d) d.className = "date ok";
      row?.classList.add("ok");
    });
    banner("Operating rooms booked at every hospital", "good", 1600);
  },
  transport_booked: (e) => {
    e.bookings.forEach((b) => {
      const row = [...document.querySelectorAll(".loop-row")].find((r) => r.querySelector(".date.ok")?.textContent === fmtDay(b.day));
      row?.querySelector(".vans").insertAdjacentHTML("beforeend",
        `<div class="van">🚐 <b>${b.vehicle || "unassigned"}</b> · ${hname(b.from_hospital)} → ${hname(b.to_hospital)} · ${b.pickup}–${b.delivery || "?"}</div>`);
    });
    status(`${state.courierName || "The courier"} booked ${e.bookings.filter((b) => b.booked).length} cold-chain vans. It saw hospitals and days, never patients.`);
  },
  injection_blocked: (e) => {
    banner(`🛡 Attack refused by ${hname(e.reply.hospital)}: "${e.reply.error}". No data returned.`, "shield", 3200);
    status("Privacy is enforced in code, not by a prompt: the hospital agent only answers four message types.");
  },
  narrative: (e) => status(e.text),
  error: (e) => { status("Error: " + (typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail)).slice(0, 160)); },
  done: () => { state.busy = false; setButtons(); },
  stream_end: () => { state.busy = false; setButtons(); },
};

async function drain() {
  if (state.draining) return;
  state.draining = true;
  while (state.queue.length) {
    const ev = state.queue.shift();
    try {
      (handlers[ev.type] || (() => {}))(ev);
    } catch (err) {
      console.error("KidneyGrid handler failed", ev.type, err);
    }
    await sleep(DELAY[ev.type] ?? 150);
  }
  state.draining = false;
}

function push(ev) { state.queue.push(ev); drain(); }

// -------------------------------------------------------------------- runs

function reset() {
  state.queue = [];
  state.owner = {};
  state.announced = false;
  state.phase = "";
  $("#ledger").innerHTML = "";
  $("#reveal").innerHTML = "";
  $("#day").innerHTML = "";
  for (const id of ["siloed", "naive", "optimal"]) $("#s-" + id + " .num").textContent = "–";
  document.querySelectorAll(".hcard").forEach((c) => c.classList.remove("matched"));
  if (state.nodes.length) drawNetwork(state.nodes), labelNodes();
}

async function run(scenario) {
  if (state.busy) return;
  state.busy = true;
  setButtons();
  reset();
  if (state.mode === "replay") {
    const events = await (await fetch(`/api/replay/${scenario}`)).json();
    events.forEach(push);
  } else {
    status("Starting a live run on Flower…");
    const src = new EventSource(`/api/live/${scenario}`);
    src.onmessage = (m) => {
      const ev = JSON.parse(m.data);
      if (ev.type === "stream_end") src.close();
      push(ev);
    };
    src.onerror = () => { src.close(); push({ type: "error", detail: "Lost connection to the live run" }); push({ type: "stream_end" }); };
  }
}

function setButtons() { document.querySelectorAll("[data-run]").forEach((b) => (b.disabled = state.busy)); }

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll("#mode button").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
}

async function showScale() {
  const modal = $("#scale");
  modal.classList.remove("hidden");
  const body = $("#scaleBody");
  try {
    const b = await (await fetch("/api/benchmark")).json();
    const a = b.average;
    const max = Math.max(a.siloed, a.naive, a.kidneygrid);
    const bar = (label, v, color) => `<div class="bar"><span>${label}</span><div class="track"><div class="fill" style="background:${color}" data-w="${(100 * v) / max}"></div></div><span class="val">${Math.round(v)}</span></div>`;
    body.innerHTML = `
      <div class="bars">
        ${bar("Each hospital alone", a.siloed, "#b8aab4")}
        ${bar("First-come national", a.naive, "#d97706")}
        ${bar("KidneyGrid", a.kidneygrid, "#0e9f6e")}
      </div>
      <div class="gain">+${b.gain_vs_siloed_pct}% transplants vs. siloed hospitals</div>
      <p>Highly sensitized patients matched: <b>${Math.round(a.high_siloed)}</b> siloed · <b>${Math.round(a.high_naive)}</b> first-come · <b style="color:#0e9f6e">${Math.round(a.high_kidneygrid)}</b> KidneyGrid (of ${Math.round(a.high_pra_total)}). Average of ${b.trials} simulated pools.</p>`;
    requestAnimationFrame(() => body.querySelectorAll(".fill").forEach((f) => (f.style.width = f.dataset.w + "%")));
  } catch {
    body.innerHTML = "<p>Run scripts/benchmark.py to generate results.</p>";
  }
}

// ------------------------------------------------------------------- init

document.querySelectorAll("[data-run]").forEach((b) => (b.onclick = () => run(b.dataset.run)));
document.querySelectorAll("#mode button").forEach((b) => (b.onclick = () => setMode(b.dataset.mode)));
$("#scaleBtn").onclick = showScale;
$("#scale").onclick = () => $("#scale").classList.add("hidden");
document.addEventListener("keydown", (e) => {
  const k = e.key.toLowerCase();
  if (["1", "2", "3", "4", "5"].includes(k)) run(["match", "confirm", "reject", "inject", "cancel"][+k - 1]);
  else if (k === "p") document.body.classList.toggle("peek");
  else if (k === "s") ($("#scale").classList.contains("hidden") ? showScale() : $("#scale").classList.add("hidden"));
  else if (k === "l") setMode(state.mode === "live" ? "replay" : "live");
  else if (k === "escape") $("#scale").classList.add("hidden");
});

(async () => {
  state.hospitals = await (await fetch("/api/hospitals")).json();
  drawHospitalCards();
  const placeholder = Object.keys(state.hospitals).map((_, i) => "pending" + i);
  drawNetwork(placeholder);
})();
