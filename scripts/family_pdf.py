"""One-page, non-technical project summary to share with family."""

import math
import sys

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfgen import canvas

OUT = sys.argv[1] if len(sys.argv) > 1 else "KidneyGrid_for_family.pdf"
W, H = letter
INK, MUTED, ACCENT, SOFT, GREEN = (HexColor(c) for c in ("#1d2433", "#5b6475", "#d9485f", "#fdf0f2", "#2f9e6f"))

body = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK)
small = ParagraphStyle("small", parent=body, fontSize=8, leading=11, textColor=MUTED)


def para(c, text, x, y, w, style=body):
    p = Paragraph(text, style)
    _, h = p.wrap(w, 1000)
    p.drawOn(c, x, y - h)
    return y - h


def heading(c, text, x, y, color=ACCENT):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x, y, text)
    return y - 8


c = canvas.Canvas(OUT, pagesize=letter)
c.setTitle("KidneyGrid")

# Header band
c.setFillColor(ACCENT)
c.rect(0, H - 118, W, 118, stroke=0, fill=1)
c.setFillColor(white)
c.setFont("Helvetica-Bold", 34)
c.drawString(48, H - 62, "KidneyGrid")
c.setFont("Helvetica", 13)
c.drawString(48, H - 86, "Helping strangers swap kidneys so families can save each other")
c.setFont("Helvetica-Oblique", 10)
c.drawString(48, H - 104, "Mahesh's project for the Flower Collaborative Agent Hackathon  ·  Stanford  ·  Sept 29, 2026")

x, col_w = 48, W - 96
y = H - 146

y = heading(c, "The problem", x, y)
y = para(c, "More than <b>95,000</b> people in the US are waiting for a kidney. In 2024, over <b>8,000</b> of them "
            "died or became too sick while waiting. Many already have a husband, wife or partner who wants to give them "
            "a kidney, but for at least a third of them, the kidney is the wrong match.", x, y, col_w) - 14

y = heading(c, "The clever fix: swap!", x, y)
y = para(c, "If Tom can't give to his wife Maria, maybe he can give to James. James's wife Linda gives to Priya, and "
            "Priya's partner Sam gives to Maria. Everyone gives, everyone receives. The catch: those families are often at "
            "<b>different hospitals</b>, and hospitals can't share patient records. So these loops are rarely found.",
     x, y, col_w) - 6

# Diagram: three couples in a loop
cx, cy, r, rx = W / 2, y - 88, 62, 150
couples = [("Tom", "Maria", "Bay General · San Francisco"), ("Linda", "James", "Mission Medical · Oakland"), ("Sam", "Priya", "Valley Health · San Jose")]
pts = [(cx + rx * math.cos(math.radians(90 + i * 120)), cy + r * math.sin(math.radians(90 + i * 120))) for i in range(3)]
c.setStrokeColor(ACCENT)
c.setLineWidth(2)
for i in range(3):
    (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % 3]
    c.line(x1, y1, x2, y2)
    # Arrowhead at the midpoint, pointing from donor couple to recipient couple.
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    ang = math.atan2(y2 - y1, x2 - x1)
    tip = (mx + 7 * math.cos(ang), my + 7 * math.sin(ang))
    left = (mx - 7 * math.cos(ang - 0.5), my - 7 * math.sin(ang - 0.5))
    right = (mx - 7 * math.cos(ang + 0.5), my - 7 * math.sin(ang + 0.5))
    path = c.beginPath()
    path.moveTo(*tip); path.lineTo(*left); path.lineTo(*right); path.close()
    c.setFillColor(ACCENT)
    c.drawPath(path, stroke=0, fill=1)
for (px, py), (donor, patient, hosp) in zip(pts, couples):
    c.setFillColor(SOFT)
    c.roundRect(px - 82, py - 22, 164, 44, 10, stroke=1, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(px, py + 5, f"{donor} + {patient}")
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    c.drawCentredString(px, py - 9, hosp)
c.setFont("Helvetica-Oblique", 8.5)
c.setFillColor(MUTED)
c.drawCentredString(cx, cy - r - 30, "Each donor gives a kidney to a stranger so their own loved one receives one.")
y = cy - r - 50

y = heading(c, "What KidneyGrid does", x, y)
y = para(c, "Every hospital gets its own AI helper (an \"agent\") that keeps its patients' information <b>locked inside "
            "that hospital</b>. The agents only share anonymous yes/no answers like \"this donor could work for one of my "
            "patients\". A coordinator agent puts the puzzle together, finds the best loops, and doctors approve every "
            "match before anyone's name is revealed. It's built on <b>Flower</b>, a platform for AI that learns and works "
            "together without pooling private data.", x, y, col_w) - 14

# Result tiles
y = heading(c, "It already works", x, y) - 6
tiles = [("0", "matches when each hospital\nworks alone"), ("3", "with simple first-come\nmatching"), ("5", "with KidneyGrid, including\nMaria, the hardest match")]
tw, gap = (col_w - 2 * 14) / 3, 14
for i, (num, label) in enumerate(tiles):
    tx = x + i * (tw + gap)
    c.setFillColor(GREEN if i == 2 else SOFT)
    c.roundRect(tx, y - 78, tw, 78, 10, stroke=0, fill=1)
    c.setFillColor(white if i == 2 else ACCENT)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(tx + tw / 2, y - 38, num)
    c.setFont("Helvetica", 9)
    c.setFillColor(white if i == 2 else INK)
    for j, line in enumerate(label.split("\n")):
        c.drawCentredString(tx + tw / 2, y - 54 - j * 11, line)
y -= 92

y = para(c, "It ran tonight on a real Flower network of five hospital computers: five transplants found in about "
            "8 seconds, with no patient record ever leaving its hospital. Tomorrow: build the live demo, present to "
            "judges from Nvidia, Meta, AMD, ARM and Nebius, and hope to win!", x, y, col_w)

para(c, "People and hospitals shown are fictional and the data is simulated. Statistics: OPTN (July 2026), SRTR 2024 "
        "Annual Data Report, Segev et al., JAMA 2005. KidneyGrid is a hackathon prototype, not a medical tool.",
     x, 44, col_w, small)
c.save()
print(OUT)
