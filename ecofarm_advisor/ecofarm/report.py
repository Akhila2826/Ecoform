"""Eco-report generator: downloadable PDF."""
import re
from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def _plain(md: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(md))


def build_pdf(farmer, result, companions, pollinators, advice: str) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="EcoFarm Report")
    s = getSampleStyleSheet()
    els = [Paragraph("EcoFarm Advisor - Eco Report", s["Title"]),
           Paragraph(f"Farmer: {escape(farmer.name)} | Crop: {escape(farmer.crop_type)} | "
                     f"Land: {farmer.land_area:.2f} ha | Date: {date.today():%d %b %Y}", s["Normal"]),
           Spacer(1, 12),
           Paragraph(f"Eco-score: {result.eco_score}/100 ({result.rating})", s["Heading2"])]
    rows = [["Source", "kg CO2e"]] + [[k, f"{v:,.1f}"] for k, v in result.breakdown().items()]
    rows += [["Total", f"{result.total:,.1f}"], ["Per hectare", f"{result.per_hectare:,.1f}"]]
    t = Table(rows, colWidths=[300, 120])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2e7d32")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("FONTNAME", (0, -2), (-1, -1), "Helvetica-Bold")]))
    els += [t, Spacer(1, 12), Paragraph("Companion crops", s["Heading2"])]
    els += [Paragraph(f"- <b>{escape(c['name'])}</b>: {escape(c['benefit'])}", s["Normal"]) for c in companions]
    els += [Spacer(1, 8), Paragraph("Pollinator-friendly plants", s["Heading2"])]
    els += [Paragraph(f"- <b>{escape(p['plant'])}</b>: attracts {escape(p['attracts'])} "
                      f"(blooms {escape(p['bloom'])})", s["Normal"]) for p in pollinators]
    els += [Spacer(1, 8), Paragraph("Recommendations", s["Heading2"])]
    for line in advice.splitlines():
        if line.strip():
            els.append(Paragraph(_plain(line.lstrip("-# ").strip()), s["Normal"]))
    els += [Spacer(1, 12), Paragraph("<i>Figures are indicative estimates; validate with your local "
                                     "agricultural extension officer.</i>", s["Normal"])]
    doc.build(els)
    return buf.getvalue()
