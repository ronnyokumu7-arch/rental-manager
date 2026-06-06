from io import BytesIO
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from sqlalchemy.orm import Session

from app.models.invoices import Invoice
from app.models.tenants import Tenant


def generate_invoice_pdf(invoice: Invoice, db: Session) -> bytes:
    tenant = db.query(Tenant).filter(Tenant.id == invoice.tenant_id).first()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    brand_color = colors.HexColor("#1a1a2e")
    accent_color = colors.HexColor("#4f8cff")

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=brand_color,
        spaceAfter=4,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#888888"),
        spaceAfter=2,
    )
    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontSize=11,
        textColor=brand_color,
        spaceAfter=8,
    )
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#555555"),
    )

    elements = []

    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Paragraph(f"#{invoice.invoice_number}", ParagraphStyle(
        "InvNum", parent=styles["Normal"], fontSize=13,
        textColor=accent_color, spaceAfter=16,
    )))

    meta = [
        ["Billed to", "Invoice date", "Due date", "Status"],
        [
            tenant.name if tenant else "—",
            invoice.created_at.strftime("%d %b %Y") if invoice.created_at else "—",
            invoice.due_date.strftime("%d %b %Y") if invoice.due_date else "—",
            invoice.status.value.upper(),
        ],
    ]
    meta_table = Table(meta, colWidths=[50 * mm, 40 * mm, 40 * mm, 40 * mm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#888888")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 11),
        ("TEXTCOLOR", (0, 1), (-1, 1), brand_color),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#dddddd")),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 10 * mm))

    line_items = [
        ["Description", "Amount"],
        [f"Subscription — {invoice.subscription_id or 'Manual'}", f"{invoice.currency_code} {invoice.amount_due:,.2f}"],
    ]
    if invoice.notes:
        line_items.append([invoice.notes, ""])

    items_table = Table(line_items, colWidths=[130 * mm, 40 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), brand_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 6 * mm))

    totals = [
        ["Amount due", f"{invoice.currency_code} {invoice.amount_due:,.2f}"],
        ["Amount paid", f"{invoice.currency_code} {invoice.amount_paid:,.2f}"],
        ["Balance", f"{invoice.currency_code} {max(invoice.amount_due - invoice.amount_paid, 0):,.2f}"],
    ]
    totals_table = Table(totals, colWidths=[130 * mm, 40 * mm])
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 2), (-1, 2), 12),
        ("TEXTCOLOR", (0, 2), (-1, 2), brand_color),
        ("LINEABOVE", (0, 2), (-1, 2), 1, brand_color),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 16 * mm))

    elements.append(Paragraph(
        "Thank you for your business. Please settle any outstanding balance by the due date.",
        small_style,
    ))
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph(
        f"Generated on {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M')} UTC",
        small_style,
    ))

    doc.build(elements)
    return buffer.getvalue()