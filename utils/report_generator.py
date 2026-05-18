import os
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
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=10, spaceAfter=4, leading=15),
        "flag": ParagraphStyle("flag", parent=base["Normal"], fontSize=10, textColor=colors.HexColor("#C0392B"), spaceAfter=3),
        "footer": ParagraphStyle("footer", parent=base["Normal"], fontSize=8, textColor=colors.grey, alignment=TA_CENTER),
    }


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
            story.append(Paragraph(f"• {sym}", s["body"]))

        # Red flags
        if report.intake.red_flags:
            story.append(Spacer(1, 4))
            story.append(Paragraph("Red Flags Detected", s["section"]))
            for flag in report.intake.red_flags:
                story.append(Paragraph(f"⚠ {flag}", s["flag"]))

        # AI intake summary
        story.append(Paragraph("Intake Summary (AI-Generated)", s["section"]))
        story.append(Paragraph(report.intake.parsed_summary or "Not available.", s["body"]))

    # Triage
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#BDC3C7"), spaceAfter=8))
    story.append(Paragraph("Triage Assessment", s["section"]))
    if report.triage:
        t = report.triage
        story.append(_urgency_badge(t.urgency_level))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Urgency Score:</b> {t.urgency_score}/10", s["body"]))
        story.append(Paragraph(f"<b>Recommended Action:</b> {t.recommended_action}", s["body"]))
        story.append(Paragraph(f"<b>Clinical Reasoning:</b> {t.reasoning}", s["body"]))
        if t.critical_flags:
            story.append(Paragraph("<b>Critical Flags:</b>", s["body"]))
            for flag in t.critical_flags:
                story.append(Paragraph(f"⚠ {flag}", s["flag"]))
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
                story.append(Paragraph(f"• {interaction}", s["body"]))
        else:
            story.append(Paragraph("No drug interactions detected.", s["body"]))

        if d.history_flags:
            story.append(Paragraph("<b>Medical History Flags:</b>", s["body"]))
            for flag in d.history_flags:
                story.append(Paragraph(f"• {flag}", s["body"]))

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
