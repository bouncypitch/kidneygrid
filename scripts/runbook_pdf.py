"""Demo run-book as a printable PDF."""

import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = sys.argv[1] if len(sys.argv) > 1 else "KidneyGrid_demo_runbook.pdf"
INK, MUTED, PLUM, PINK, MINT, SOFT, LINE = (HexColor(c) for c in
                                            ("#1d0c17", "#6e5f69", "#5b1a63", "#ec2d7a", "#d7f2e3", "#f7f3f6", "#e6dde4"))

base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK)
small = ParagraphStyle("small", parent=base, fontSize=8.5, leading=11.5)
h1 = ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=INK)
sub = ParagraphStyle("sub", parent=base, fontSize=11, leading=15, textColor=MUTED)
h2 = ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=PLUM, spaceBefore=10, spaceAfter=4)
cell = ParagraphStyle("cell", parent=base, fontSize=8.8, leading=11.8)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")


def P(text, style=base):
    return Paragraph(text, style)


def bullets(items, style=base):
    return [P(f"&bull;&nbsp; {t}", style) for t in items]


def table(rows, widths, header=True):
    data = [[P(c, cellb if (header and i == 0) else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), SOFT))
    t.setStyle(TableStyle(style))
    return t


def box(flowables, color):
    t = Table([[flowables]], colWidths=[7.0 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


story = [
    P('Kidney<font color="#ec2d7a">Grid</font> &mdash; demo run-book', h1),
    P("Flower Collaborative Agent Hackathon &middot; Stanford &middot; Sept 29, 2026 &middot; demos 5:30 pm &middot; ~4 minutes", sub),
    Spacer(1, 8),
    box([P("<b>Links</b> &nbsp; Web app: http://127.0.0.1:8765 &nbsp;&middot;&nbsp; Hub: flower.ai/apps/kdotmahesh/kidneygrid "
           "&nbsp;&middot;&nbsp; GitHub: github.com/bouncypitch/kidneygrid &nbsp;&middot;&nbsp; Federation: @kdotmahesh/kidneygrid "
           "&nbsp;&middot;&nbsp; Submit (by 5:15): flowerlabs.typeform.com/to/rQuplUGG", small)], MINT),

    P("1. Thirty minutes before (about 5:00)", h2),
    *bullets([
        "<b>Laptop:</b> plugged in, never sleep, on venue Wi-Fi, notifications off.",
        "<b>Nodes up:</b> <font face='Courier'>grep -l \"SuperNode ID\" .stack/grid-*.log | wc -l</font> should print <b>5</b> "
        "(Capitol Hospital runs on Nebius). If fewer: <font face='Courier'>scripts/supergrid_nodes.sh</font> and wait ~90 s.",
        "<b>Nebius:</b> console.nebius.com &rarr; Endpoints &rarr; <i>kidneygrid-capitol-hospital</i> shows <b>Running</b>.",
        "<b>Tabs, in order:</b> (1) deck in present mode &middot; (2) web app, press <b>L</b> for Live &middot; (3) opener.mp4.",
        "<b>Warm-up:</b> press <b>1</b> once in the web app so SuperGrid is warm. Browser zoom 100% at projector resolution.",
    ]),

    P("2. The pitch", h2),
    table([
        ["Time", "Do", "Say (short version)"],
        ["0:00", "Play <b>opener video</b> (40 s)", "(let it play)"],
        ["0:40", "Slides 2&ndash;3: stakes, Maria", "&ldquo;95,000 Americans are waiting for a kidney. Maria has waited 7 years. Her husband can't donate: wrong blood type.&rdquo;"],
        ["1:05", "Slides 4&ndash;5: swap, silos", "&ldquo;Swaps work &mdash; Stanford's Alvin Roth shared a Nobel for them. But hospitals can't share patient data, so the matches are never found.&rdquo;"],
        ["1:25", "Slide 6, then switch to web app", "&ldquo;KidneyGrid puts a Flower agent inside every hospital.&rdquo;"],
        ["1:35", "Press <b>2</b> (Approve)", "&ldquo;Five hospitals and a courier on Flower's SuperGrid &mdash; Capitol Hospital is running on Nebius. Alone: 0. First-come: 3, Maria left out. KidneyGrid: 5.&rdquo; Point at the <b>privacy ledger</b> and a <b>surgeon briefing</b>: &ldquo;Endeavor 1.0 writes each surgeon's briefing, inside the hospital.&rdquo;"],
        ["2:35", "Press <b>5</b> (OR cancels)", "&ldquo;Valley Health loses its operating room. The agents move the whole loop from Tuesday to Thursday, and a courier books a cold-chain van for every kidney without seeing a patient.&rdquo;"],
        ["3:15", "Press <b>4</b> (Attack)", "&ldquo;Prompt injection is refused &mdash; privacy is enforced in code, not in a prompt.&rdquo;"],
        ["3:25", "Press <b>S</b> (scale), back to deck", "&ldquo;On 300 simulated pairs: +41% transplants and 2.4&times; the hardest-to-match patients.&rdquo;"],
        ["3:40", "Slides: Built on Flower, Path forward", "&ldquo;Native Flower: SuperNodes, Grid messaging, Flower Hub. Next: a real pilot. <b>Zero matches alone. Five together.</b>&rdquo;"],
    ], [0.5 * inch, 1.75 * inch, 4.75 * inch]),

    KeepTogether([
        P("3. If something goes wrong", h2),
        *bullets([
            "<b>Live run slow or stalls:</b> press <b>L</b> for Replay, press the same key again. Identical visuals, no network. "
            "Say: &ldquo;Here's the recorded run from 20 minutes ago.&rdquo;",
            "<b>Wi-Fi dies:</b> Replay mode, plus the full film (video/out/kidneygrid.mp4).",
            "<b>A node dropped:</b> don't fix it on stage &mdash; use Replay.",
        ]),
    ]),

    KeepTogether([
        P("4. Likely judge questions", h2),
        table([
            ["Question", "Answer"],
            ["Is this real patient data?", "No &mdash; all synthetic. The architecture is real: each hospital's node reads only its own disk."],
            ["Doesn't HLA typing leave the hospital?", "Only as anonymous donor tokens with no identity, as national registries already do. Antibody profiles and records never leave."],
            ["How does it scale?", "Stanford fragmentation research estimates +30&ndash;63%; our simulation shows +41%."],
            ["Why Flower?", "Data stays where it lives and agents collaborate across organizations &mdash; exactly what SuperNodes and the Grid are for."],
            ["Where is Endeavor used?", "Each hospital's agent uses Endeavor 1.0 to write its surgeon's briefing from non-identifying facts."],
        ], [2.0 * inch, 5.0 * inch]),
    ]),

    KeepTogether([
        P("5. Running KidneyGrid from Flower itself (for judges who ask)", h2),
        *bullets([
            "<b>Browser:</b> flower.ai/app &rarr; choose federation <b>@kdotmahesh/kidneygrid</b> &rarr; New chat &rarr; pick agent "
            "<b>KidneyGrid</b> &rarr; type &ldquo;Approve the plan&rdquo; (or &ldquo;&hellip; an operating room may cancel&rdquo;).",
            "<b>Terminal:</b> <font face='Courier'>uv run flwr chat</font> &rarr; <font face='Courier'>/federation @kdotmahesh/kidneygrid</font> "
            "&rarr; <font face='Courier'>@kdotmahesh/kidneygrid Approve the plan</font>.",
            "The Hub page's <b>Run App</b> button fails for all AgentApps (Flower requires a chat prompt) &mdash; use chat instead. "
            "In a federation without hospital nodes, KidneyGrid runs a clearly labelled simulation.",
        ]),
    ]),

    KeepTogether([
        P("6. After demos", h2),
        *bullets([
            "<b>Delete the Nebius endpoint</b> (Endpoints &rarr; the &hellip; menu &rarr; Delete) &mdash; it bills about $1.59/hour.",
            "Rotate the Flower API key that was shared in chat. Run <font face='Courier'>claude update</font>.",
        ]),
    ]),
]

doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                        topMargin=0.6 * inch, bottomMargin=0.6 * inch, title="KidneyGrid demo run-book")
doc.build(story)
print(OUT)
