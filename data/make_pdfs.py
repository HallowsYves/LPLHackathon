"""Generate dense brokerage-style PDFs from data/ground_truth/*.json.

Every figure printed is read from (or summed from) the JSON, never retyped.
Output: data/pdfs/<id>.pdf. Synthetic sample data only.
"""
import glob
import json
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = os.path.dirname(os.path.abspath(__file__))
FOOTER = "SYNTHETIC SAMPLE, NOT A REAL STATEMENT"
INFLOWS = {"deposit", "dividend"}
NAVY = colors.HexColor("#1f3a5f")
GRID = colors.HexColor("#b8c2cc")
BAND = colors.HexColor("#eef2f6")

styles = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=15, textColor=NAVY, alignment=0, spaceAfter=2)
H2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=10.5, textColor=NAVY, spaceBefore=8, spaceAfter=3)
BODY = ParagraphStyle("body", parent=styles["BodyText"], fontSize=8.5, leading=10.5)
SMALL = ParagraphStyle("small", parent=styles["BodyText"], fontSize=6.2, leading=7.6, textColor=colors.HexColor("#444444"))


def money(x):
    return f"${x:,.2f}"


def signed(x):
    return f"-${-x:,.2f}" if x < 0 else f"${x:,.2f}"


def table(rows, widths, right_cols=()):
    t = Table(rows, colWidths=widths, repeatRows=1)
    st = [
        ("FONTSIZE", (0, 0), (-1, -1), 7.8),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BAND]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    for c in right_cols:
        st.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(st))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(NAVY)
    canvas.drawCentredString(letter[0] / 2, 0.45 * inch, FOOTER)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(letter[0] - 0.6 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build(statement_id, s):
    out = os.path.join(HERE, "pdfs", f"{statement_id}.pdf")
    doc = SimpleDocTemplate(out, pagesize=letter, leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.8 * inch,
                            title=f"Sample statement {statement_id}", author="Clear Statement (synthetic)")
    txns, fees = s["transactions"], s["fees"]
    story = [
        Paragraph("Sample Brokerage Services: Account Statement", H1),
        Paragraph(f"<b>Client:</b> {s['client']['name']} (age {s['client']['age']}) &nbsp;&nbsp; "
                  f"<b>Statement period:</b> {s['period']} (Jul 1 to Sep 30, 2026)", BODY),
        Paragraph("Account summary", H2),
    ]

    rows = [["Acct", "Type", "Start\nvalue", "Deposits", "Dividends", "Withdrawals\n& wires",
             "Fees", "Market\nchange", "End\nvalue"]]
    tot = [0.0] * 7
    for a in s["accounts"]:
        def flow(kinds):
            return sum(t["amount"] for t in txns if t.get("account") == a["id"] and t["type"] in kinds)
        dep, div = flow({"deposit"}), flow({"dividend"})
        out_ = flow({"withdrawal", "wire"})
        fee = sum(f["amount"] for f in fees if f.get("account") == a["id"])
        mkt = a["end_value"] - (a["start_value"] + dep + div - out_ - fee)
        vals = [a["start_value"], dep, div, -out_, -fee, mkt, a["end_value"]]
        rows.append([a["id"], a["type"]] + [signed(v) if i in (3, 4, 5) else money(v) for i, v in enumerate(vals)])
        tot = [x + v for x, v in zip(tot, vals)]
    rows.append(["", "Total"] + [signed(v) if i in (3, 4, 5) else money(v) for i, v in enumerate(tot)])
    t = table(rows, [0.45 * inch, 1.15 * inch, 0.9 * inch, 0.7 * inch, 0.7 * inch, 0.95 * inch,
                     0.65 * inch, 0.8 * inch, 0.9 * inch], right_cols=range(2, 9))
    t.setStyle(TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
    story += [t, Paragraph("Market change is the calculated difference between start value, "
                           "end value and the activity listed below.", SMALL)]

    story.append(Paragraph("Fees and charges", H2))
    frows = [["Description", "Account", "Amount"]]
    frows += [[f["label"], f.get("account", ""), money(f["amount"])] for f in fees]
    frows.append(["Total fees this period", "", money(sum(f["amount"] for f in fees))])
    frows.append(["Total fees, prior period", "", money(s["prior_fee_total"])])
    ft = table(frows, [3.6 * inch, 1.0 * inch, 1.2 * inch], right_cols=(2,))
    story.append(ft)

    story.append(Paragraph("Account activity", H2))
    trows = [["Date", "ID", "Account", "Type", "Description / payee", "Amount"]]
    for t_ in sorted(txns, key=lambda x: (x["date"], x["id"])):
        sign = 1 if t_["type"] in INFLOWS else -1
        trows.append([t_["date"], t_["id"], t_.get("account", ""), t_["type"].title(),
                      t_.get("payee", ""), signed(sign * t_["amount"])])
    story.append(table(trows, [0.8 * inch, 0.45 * inch, 0.6 * inch, 0.85 * inch, 3.1 * inch, 1.0 * inch],
                       right_cols=(5,)))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "IMPORTANT INFORMATION. This is a fictional document created for a software demonstration. "
        "The client, payees, accounts and amounts are invented and do not describe any real person, "
        "firm or account. Nothing here is investment, tax or legal advice. Values are shown in US "
        "dollars. Market change is calculated and not an official performance figure. Please review "
        "this statement and report any questions to your advisor promptly. Results shown by the "
        "Clear Statement prototype were tested on sample data only.", SMALL))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out


def main():
    os.makedirs(os.path.join(HERE, "pdfs"), exist_ok=True)
    for p in sorted(glob.glob(os.path.join(HERE, "ground_truth", "*.json"))):
        sid = os.path.splitext(os.path.basename(p))[0]
        with open(p) as fh:
            print("wrote", build(sid, json.load(fh)))


if __name__ == "__main__":
    main()
