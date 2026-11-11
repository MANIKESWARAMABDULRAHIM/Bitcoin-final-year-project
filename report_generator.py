import os
from datetime import datetime
from django.conf import settings

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors


def generate_pdf(wallets, fraud_analysis=None, wallet_details=None):
    """Generate detailed forensic PDF report with fraud explanations"""
    
    # Ensure media folder exists
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    # Unique filename
    filename = f"forensic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    file_path = os.path.join(settings.MEDIA_ROOT, filename)

    # Create document
    doc = SimpleDocTemplate(file_path, pagesize=LETTER)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#1a0033')
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading1'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#0066ff')
    )
    
    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=10,
        spaceBefore=6,
        spaceAfter=6,
        leading=14
    )

    # Title
    elements.append(Paragraph("Bitcoin Forensic Investigation Report", title_style))
    elements.append(Spacer(1, 10))
    
    # Summary section
    elements.append(Paragraph("Executive Summary", heading_style))
    
    if fraud_analysis and fraud_analysis.get('total_transactions', 0) > 0:
        total_tx = fraud_analysis.get('total_transactions', len(wallets))
        high_cent = len(fraud_analysis.get('high_centrality_nodes', []))
        circular = len(fraud_analysis.get('circular_flow_nodes', []))
        rapid = len(fraud_analysis.get('rapid_exchange_pairs', []))
        mean_amt = fraud_analysis.get('mean_amount', 0)
        large_thresh = fraud_analysis.get('large_amount_threshold', 0)
        
        summary_text = f"""This report analyzes {total_tx} Bitcoin transactions. The analysis detected {high_cent} high-centrality hub nodes, {circular} wallets involved in circular money flows, and {rapid} rapid exchange pairs. Average Transaction Amount: {mean_amt:.8f} BTC. Large Transaction Threshold: {large_thresh:.8f} BTC."""
        elements.append(Paragraph(summary_text, normal_style))
    else:
        elements.append(Paragraph(f"Analysis of {len(wallets)} wallet addresses.", normal_style))

    elements.append(Spacer(1, 20))

    # Risk Assessment Summary
    suspicious_wallets = [w for w in wallets if w.suspicious]
    if len(wallets) > 0:
        elements.append(Paragraph("Risk Assessment", heading_style))
        risk_text = f"Total Wallets Analyzed: {len(wallets)}. High-Risk Wallets: {len(suspicious_wallets)} ({len(suspicious_wallets)/len(wallets)*100:.1f}%). Low-Risk Wallets: {len(wallets) - len(suspicious_wallets)}."
        elements.append(Paragraph(risk_text, normal_style))
        elements.append(Spacer(1, 15))

    # Wallet Details Table
    elements.append(Paragraph("Wallet Details", heading_style))
    
    table_data = [["Wallet Address", "Centrality", "Clustering", "Total TX", "Suspicious TX", "Status"]]
    
    for w in wallets:
        table_data.append([
            w.address[:12] + "...",
            f"{round(w.centrality or 0, 4)}",
            f"{round(w.clustering or 0, 4)}",
            str(w.total_transactions),
            str(w.suspicious_transaction_count),
            "Suspicious" if w.suspicious else "Normal"
        ])

    # Create Table
    table = Table(table_data, colWidths=[1.8*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.9*inch, 0.9*inch])
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a0033')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 25))

    # Detailed Fraud Explanations
    elements.append(Paragraph("Detailed Fraud Analysis", heading_style))
    
    for i, w in enumerate(wallets):
        # Get reasons if wallet_details is available
        reasons = []
        if wallet_details:
            for wd in wallet_details:
                if wd.get('wallet') == w:
                    reasons = wd.get('reasons', [])
                    break
        
        explanation = get_fraud_explanation(w, reasons)
        
        # Wallet header
        status_text = "SUSPICIOUS" if w.suspicious else "NORMAL"
        elements.append(Paragraph(f"<b>Wallet:</b> {w.address[:20]}... | <b>Status:</b> {status_text}", normal_style))
        elements.append(Spacer(1, 8))
        
        # Explanation - use simple text without HTML tags
        elements.append(Paragraph(explanation, normal_style))
        elements.append(Spacer(1, 12))
        
        # Add page break after every 3 wallets
        if (i + 1) % 3 == 0:
            elements.append(PageBreak())

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        f"Report generated on {datetime.now().strftime('%d %B %Y, %I:%M %p')}",
        normal_style
    ))
    elements.append(Paragraph(
        "For educational and investigative purposes only. Not intended for illegal activity.",
        normal_style
    ))

    # Build PDF
    doc.build(elements)

    return file_path, filename


def get_fraud_explanation(wallet, reasons_list):
    """Generate detailed fraud explanation for a wallet"""
    explanations = []
    
    if wallet.suspicious:
        explanations.append(
            "HIGH RISK: This wallet has been flagged as potentially suspicious based on "
            "multiple risk factors detected in the transaction network."
        )
    else:
        explanations.append(
            "LOW RISK: This wallet appears to have normal transaction patterns with "
            "no significant risk indicators detected."
        )
    
    # Centrality analysis
    if wallet.centrality and wallet.centrality > 0.3:
        explanations.append(
            f"HIGH CENTRALITY ({wallet.centrality:.4f}): This wallet acts as a major hub "
            f"in the transaction network, handling a disproportionately large share of transactions. "
            f"This pattern is often associated with exchange wallets, mining pools, or potentially "
            f"money laundering hubs that aggregate funds from multiple sources."
        )
    
    # Transaction analysis
    if wallet.suspicious_transaction_count > 0:
        explanations.append(
            f"{wallet.suspicious_transaction_count} SUSPICIOUS TRANSACTIONS DETECTED: "
            f"Out of {wallet.total_transactions} total transactions, {wallet.suspicious_transaction_count} "
            f"showed risk indicators such as: unusual transaction amounts, circular flow patterns, "
            f"or rapid back-and-forth exchanges between the same addresses."
        )
    
    # Clustering analysis
    if wallet.clustering and wallet.clustering > 0.5:
        explanations.append(
            f"HIGH CLUSTERING ({wallet.clustering:.4f}): This wallet is highly connected to "
            f"other addresses, forming tight transaction clusters. This often indicates coordinated "
            f"activity, possibly related to mixer services, darknet markets, or organized trading rings."
        )
    
    # Specific reasons
    if reasons_list:
        unique_reasons = list(set(reasons_list))
        explanations.append(f"DETECTED RISK INDICATORS: {', '.join(unique_reasons[:5])}")
    
    return " ".join(explanations)
