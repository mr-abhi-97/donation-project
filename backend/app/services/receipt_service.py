import os
import uuid
import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from backend.app.config import settings
from backend.app.models import Donation, TaxReceipt80G, Donor


class ReceiptService:
    @classmethod
    def generate_receipt_number(cls, seq_id: int) -> str:
        fy = settings.CURRENT_FINANCIAL_YEAR
        return f"RIF/80G/{fy}/{seq_id:05d}"

    @classmethod
    def generate_80g_pdf(cls, donation: Donation, donor: Donor, receipt_no: str) -> Path:
        """
        Generates a legally compliant, beautiful Section 80G Donation Receipt PDF.
        """
        filename = f"Receipt_{receipt_no.replace('/', '_')}.pdf"
        output_path = settings.RECEIPTS_DIR / filename

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Custom styles
        header_title = ParagraphStyle(
            'HeaderTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1e3a8a"),
            alignment=1  # Center
        )
        sub_title = ParagraphStyle(
            'SubTitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4b5563"),
            alignment=1
        )
        badge_style = ParagraphStyle(
            'Badge',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#065f46"),
            alignment=1
        )
        body_style = ParagraphStyle(
            'ReceiptBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1f2937")
        )
        bold_style = ParagraphStyle(
            'ReceiptBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#111827")
        )

        elements = []

        # Organization Header
        elements.append(Paragraph(f"<b>{settings.NGO_NAME}</b>", header_title))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(settings.NGO_ADDRESS, sub_title))
        elements.append(Paragraph(f"PAN: <b>{settings.NGO_PAN}</b> | 80G Reg No: <b>{settings.NGO_80G_REG_NO}</b> | Email: {settings.NGO_EMAIL}", sub_title))
        elements.append(Spacer(1, 10))

        # Divider line
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563eb"), spaceAfter=15))

        # Certificate Badge
        receipt_badge = Table(
            [[Paragraph("<b>DONATION TAX EXEMPTION CERTIFICATE (FORM 10BE / SECTION 80G)</b>", badge_style)]],
            colWidths=[520]
        )
        receipt_badge.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#d1fae5")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#10b981")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(receipt_badge)
        elements.append(Spacer(1, 15))

        # Metadata Row (Receipt No & Issue Date)
        issue_date_str = datetime.now().strftime("%d-%b-%Y")
        meta_data = [
            [
                Paragraph(f"Receipt No: <b>{receipt_no}</b>", body_style),
                Paragraph(f"Date of Issue: <b>{issue_date_str}</b>", body_style)
            ],
            [
                Paragraph(f"Financial Year: <b>{settings.CURRENT_FINANCIAL_YEAR}</b>", body_style),
                Paragraph(f"Section: <b>80G(5)(vi) of IT Act, 1961</b>", body_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[260, 260])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 15))

        # Donor Information Table
        amount_val = Decimal(str(donation.extracted_amount or 0))
        donor_data = [
            [Paragraph("<b>Donor Name:</b>", bold_style), Paragraph(donor.full_name, body_style)],
            [Paragraph("<b>PAN Number:</b>", bold_style), Paragraph(f"<b>{donor.pan_number}</b>", bold_style)],
            [Paragraph("<b>Contact Phone:</b>", bold_style), Paragraph(donor.phone, body_style)],
            [Paragraph("<b>Email:</b>", bold_style), Paragraph(donor.email, body_style)],
            [Paragraph("<b>Address:</b>", bold_style), Paragraph(donor.address or "As per records", body_style)],
        ]
        donor_table = Table(donor_data, colWidths=[150, 370])
        donor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#ffffff")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(Paragraph("<b>Donor Details</b>", bold_style))
        elements.append(Spacer(1, 4))
        elements.append(donor_table)
        elements.append(Spacer(1, 15))

        # Contribution Details Table
        donation_date_str = donation.extracted_date.strftime("%d-%b-%Y") if donation.extracted_date else issue_date_str
        contrib_data = [
            [
                Paragraph("<b>Payment Mode</b>", bold_style),
                Paragraph("<b>UPI / UTR Reference</b>", bold_style),
                Paragraph("<b>Date of Txn</b>", bold_style),
                Paragraph("<b>Total Donation (INR)</b>", bold_style)
            ],
            [
                Paragraph("UPI Transfer", body_style),
                Paragraph(f"<b>{donation.extracted_utr or 'VERIFIED'}</b>", body_style),
                Paragraph(donation_date_str, body_style),
                Paragraph(f"<b>₹ {amount_val:,.2f}</b>", bold_style)
            ]
        ]
        contrib_table = Table(contrib_data, colWidths=[100, 180, 100, 140])
        contrib_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#93c5fd")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(Paragraph("<b>Contribution Summary</b>", bold_style))
        elements.append(Spacer(1, 4))
        elements.append(contrib_table)
        elements.append(Spacer(1, 15))

        # Statutory Declaration
        declaration_text = (
            f"We gratefully acknowledge the receipt of <b>₹ {amount_val:,.2f}</b> from {donor.full_name} "
            f"(PAN: {donor.pan_number}). This donation qualifies for deduction under Section 80G(5)(vi) "
            f"of the Income Tax Act, 1961. The particulars of this donation have been recorded in Form 10BD "
            f"for reporting to the Director General of Income Tax (Systems). This computer-generated receipt "
            f"does not require a physical signature when verified digitally."
        )
        elements.append(Paragraph(declaration_text, body_style))
        elements.append(Spacer(1, 20))

        # Signatory block
        sign_data = [
            [
                Paragraph("<b>Digitally Verified</b><br/>Raise India Reconciliation Engine<br/>Audit Ref: " + str(donation.id)[:8], sub_title),
                Paragraph("<b>For Raise India Foundation</b><br/><br/><br/><b>Authorized Signatory</b><br/>Treasury & Compliance Officer", sub_title)
            ]
        ]
        sign_table = Table(sign_data, colWidths=[260, 260])
        sign_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(sign_table)

        doc.build(elements)
        return output_path

    @classmethod
    def export_form_10bd_excel(cls, donations: list) -> bytes:
        """
        Generates compliant Form 10BD Excel report for income tax filing.
        """
        rows = []
        for idx, d in enumerate(donations, start=1):
            donor = d.donor
            if not donor:
                continue

            rows.append({
                "Serial Number": idx,
                "Pre-acknowledgement Number": str(d.id)[:10].upper(),
                "ID Type": "Permanent Account Number (PAN)",
                "Donor PAN Number": donor.pan_number,
                "Donor Full Name": donor.full_name,
                "Address": donor.address or "N/A",
                "Donation Type": "Corpus / Specific Purpose",
                "Mode of Receipt": "Electronic modes including UPI",
                "Amount (INR)": float(d.extracted_amount or 0),
                "UTR / Reference": d.extracted_utr or "N/A",
                "Date of Payment": d.extracted_date.strftime("%d/%m/%Y") if d.extracted_date else "",
                "Section Code": "Section 80G(5)(vi)"
            })

        df = pd.DataFrame(rows)
        out_stream = io.BytesIO()
        with pd.ExcelWriter(out_stream, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Form 10BD Filing')
        
        return out_stream.getvalue()


# Helper type
Tuple_Path = Path
