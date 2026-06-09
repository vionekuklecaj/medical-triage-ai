import os
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT

URGENCY_COLORS = {
    "critical": colors.HexColor("#C0392B"),
    "high":     colors.HexColor("#E67E22"),
    "medium":   colors.HexColor("#F1C40F"),
    "low":      colors.HexColor("#27AE60"),
}

RISK_COLORS = {
    "severe":   colors.HexColor("#C0392B"),
    "moderate": colors.HexColor("#E67E22"),
    "none":     colors.HexColor("#27AE60"),
}


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontSize=20, spaceAfter=4, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontSize=10, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=16),
        "section": ParagraphStyle("section", parent=base["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#2C3E50")),
        "subsection": ParagraphStyle("subsection", parent=base["Heading3"], fontSize=11, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#34495E")),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=10, spaceAfter=4, leading=15),
        "flag": ParagraphStyle("flag", parent=base["Normal"], fontSize=10, textColor=colors.HexColor("#C0392B"), spaceAfter=3),
        "footer": ParagraphStyle("footer", parent=base["Normal"], fontSize=8, textColor=colors.grey, alignment=TA_CENTER),
    }


def _md_inline(text: str) -> str:
    """
    Convert inline Markdown to ReportLab's mini-markup and escape XML specials.
    Order matters: escape first, then inject <b>/<i> tags.
    """
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)   # **bold**
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)       # __bold__
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)  # *italic*
    return text.strip()


def _render_markdown(md_text: str, s: dict) -> list:
    """
    Turn an LLM-generated Markdown summary into a list of ReportLab flowables.
    Handles headers, bullets, blockquotes, bold/italic, horizontal rules, and
    simple tables. Wrapped prose lines are joined with spaces (fixes the
    'word-mashing' you get from dumping raw Markdown into a single Paragraph).
    """
    flowables = []
    para_buf = []

    def flush_para():
        if para_buf:
            joined = " ".join(para_buf).strip()
            if joined:
                flowables.append(Paragraph(_md_inline(joined), s["body"]))
            para_buf.clear()

    for raw in md_text.splitlines():
        line = raw.strip()

        # Blank line -> end current paragraph
        if not line:
            flush_para()
            continue

        # Horizontal rule (---, ***, ___) -> skip
        if re.fullmatch(r"[-*_]{3,}", line):
            flush_para()
            continue

        # Table separator row (|---|---|) -> skip
        if "|" in line and set(line) <= set("|-: "):
            continue

        # Table data row -> render as "cell: cell" (avoids broken tables;
        # the report already has its own Patient Information table)
        if line.startswith("|") and line.endswith("|"):
            flush_para()
            cells = [c.strip() for c in line.strip("|").split("|") if c.strip()]
            if cells and not all(c.lower() in ("field", "details", "value") for c in cells):
                flowables.append(Paragraph(_md_inline(": ".join(cells)), s["body"]))
            continue

        # Headers (#, ##, ### ...)
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush_para()
            style = s["section"] if len(m.group(1)) <= 2 else s["subsection"]
            flowables.append(Paragraph(_md_inline(m.group(2)), style))
            continue

        # Blockquote (>)
        if line.startswith(">"):
            flush_para()
            flowables.append(Paragraph(_md_inline(line.lstrip(">").strip()), s["body"]))
            continue

        # Bullet list (-, *, +)
        m = re.match(r"^[-*+]\s+(.*)$", line)
        if m:
            flush_para()
            flowables.append(Paragraph("&bull;&nbsp;" + _md_inline(m.group(1)), s["body"]))
            continue

        # Numbered list (1. 2. ...)
        m = re.match(r"^(\d+)\.\s+(.*)$", line)
        if m:
            flush_para()
            flowables.append(Paragraph(f"{m.group(1)}.&nbsp;" + _md_inline(m.group(2)), s["body"]))
            continue

        # Ordinary prose line -> accumulate into current paragraph
        para_buf.append(line)

    flush_para()
    return flowables


def _urgency_badge(urgency_level: str) -> Table:
    label = urgency_level.upper()
    bg = URGENCY_COLORS.get(urgency_level.lower(), colors.grey)
    data = [[label]]
    t = Table(data, colWidths=[60 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 16),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [bg]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def generate_pdf_report(report, pdf_path: str) -> None:
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    s = _styles()
    story = []

    # Header
    story.append(Paragraph("Medical Intake & Triage Summary", s["title"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#BDC3C7")))
    story.append(Spacer(1, 8))

    # Patient info
    if report.intake:
        p = report.intake.patient
        story.append(Paragraph("Patient Information", s["section"]))
        info_data = [
            ["Name", p.full_name, "Age", str(p.age)],
            ["Gender", p.gender, "Severity (self-reported)", p.severity.capitalize()],
            ["Symptom Duration", p.symptom_duration, "Intake Status", report.intake.intake_status.upper()],
        ]
        info_table = Table(info_data, colWidths=[40 * mm, 60 * mm, 50 * mm, 40 * mm])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#F8F9FA"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 6))

        # Symptoms
        story.append(Paragraph("Reported Symptoms", s["section"]))
        for sym in p.symptoms:
            story.append(Paragraph(f"&bull;&nbsp;{sym}", s["body"]))

        # Red flags
        if report.intake.red_flags:
            story.append(Spacer(1, 4))
            story.append(Paragraph("Red Flags Detected", s["section"]))
            for flag in report.intake.red_flags:
                story.append(Paragraph(f"&#9888; {flag}", s["flag"]))

        # AI intake summary (Markdown -> rendered flowables)
        story.append(Paragraph("Intake Summary (AI-Generated)", s["section"]))
        if report.intake.parsed_summary:
            for fl in _render_markdown(report.intake.parsed_summary, s):
                story.append(fl)
        else:
            story.append(Paragraph("Not available.", s["body"]))

    # Triage
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#BDC3C7"), spaceAfter=8))
    story.append(Paragraph("Triage Assessment", s["section"]))
    if report.triage:
        t = report.triage
        story.append(_urgency_badge(t.urgency_level))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Urgency Score:</b> {t.urgency_score}/10", s["body"]))
        story.append(Paragraph(f"<b>Recommended Action:</b> {t.recommended_action}", s["body"]))
        if t.critical_flags:
            story.append(Paragraph("<b>Critical Flags:</b>", s["body"]))
            for flag in t.critical_flags:
                story.append(Paragraph(f"&#9888; {flag}", s["flag"]))
    else:
        story.append(Paragraph("Triage agent unavailable — manual assessment required.", s["body"]))

    # Drug & history
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#BDC3C7"), spaceAfter=8))
    story.append(Paragraph("Drug Interactions & Medical History", s["section"]))
    if report.drug_history:
        d = report.drug_history
        risk_color = RISK_COLORS.get(d.risk_level.lower(), colors.grey)
        story.append(Paragraph(f"<b>Interaction Risk Level:</b> <font color='#{risk_color.hexval()[2:] if hasattr(risk_color, 'hexval') else '000000'}'>{d.risk_level.upper()}</font>", s["body"]))

        if d.interactions_found:
            story.append(Paragraph("<b>Drug Interactions Found:</b>", s["body"]))
            for interaction in d.interactions_found:
                story.append(Paragraph(f"&bull;&nbsp;{interaction}", s["body"]))
        else:
            story.append(Paragraph("No drug interactions detected.", s["body"]))

        if d.history_flags:
            story.append(Paragraph("<b>Medical History Flags:</b>", s["body"]))
            for flag in d.history_flags:
                story.append(Paragraph(f"&bull;&nbsp;{flag}", s["body"]))

        story.append(Paragraph(f"<b>Recommendations:</b> {d.recommendations}", s["body"]))
    else:
        story.append(Paragraph("Drug history agent unavailable — manual review required.", s["body"]))

    # Medications & allergies
    if report.intake:
        p = report.intake.patient
        story.append(Spacer(1, 4))
        if p.current_medications:
            story.append(Paragraph("<b>Current Medications:</b> " + ", ".join(p.current_medications), s["body"]))
        if p.known_allergies:
            story.append(Paragraph("<b>Known Allergies:</b> " + ", ".join(p.known_allergies), s["body"]))

    # Footer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#BDC3C7")))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "DISCLAIMER: This report is AI-generated and intended to assist — not replace — professional medical judgement. "
        "Always verify with a qualified healthcare provider.",
        s["footer"]
    ))

    doc.build(story)