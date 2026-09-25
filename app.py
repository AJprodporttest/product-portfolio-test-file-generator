from __future__ import annotations

import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from tens_parser import average_curve, curve_summary, parse_id_tens


st.set_page_config(page_title="Material Data Sheet", page_icon="▣", layout="wide")
st.markdown("""<style>
.stApp {background:#f4f6f7;color:#101820}.block-container {max-width:1420px;padding-top:1.5rem}.sheet-title{border:2px solid #13293d;background:#fff;padding:16px 20px;margin-bottom:14px}.sheet-title h1{font-family:Arial,sans-serif;font-size:1.55rem;letter-spacing:.11em;margin:0;color:#13293d}.sheet-title p{font-family:Arial,sans-serif;font-size:.75rem;letter-spacing:.08em;margin:4px 0 0;color:#4d5b66}.section-label{background:#13293d;color:#fff;padding:7px 10px;font-family:Arial,sans-serif;font-size:.78rem;font-weight:700;letter-spacing:.08em;margin-top:18px;margin-bottom:0}div[data-testid="stMetric"]{border:1px solid #74828c;border-radius:0;background:#fff;padding:10px}div[data-testid="stDataFrame"]{border:1px solid #74828c;border-radius:0}.stButton button,.stDownloadButton button{border-radius:0;border:1px solid #13293d;background:#13293d;color:#fff;font-weight:700}.stTextInput input,.stNumberInput input{border-radius:0;border-color:#74828c;background:#fff}
</style>""", unsafe_allow_html=True)


def get_default(key: str, value):
    return st.session_state.get(key, value)


def section(title: str):
    st.markdown(f'<div class="section-label">{title}</div>', unsafe_allow_html=True)


def plot_tensile(average: pd.DataFrame, title: str, x_limit: float | None = None):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=average.extension_mm, y=average.mean_force_kN + average.std_force_kN, mode="lines", line={"width": 0}, hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=average.extension_mm, y=average.mean_force_kN - average.std_force_kN, mode="lines", fill="tonexty", fillcolor="rgba(19,41,61,.16)", line={"width": 0}, name="±1 standard deviation"))
    fig.add_trace(go.Scatter(x=average.extension_mm, y=average.mean_force_kN, mode="lines", name="Average tensile curve", line={"color": "#13293d", "width": 3}))
    fig.update_layout(title={"text": title, "font": {"size": 16, "color": "#13293d"}}, xaxis_title="Extension (mm)", yaxis_title="Force (kN)", template="plotly_white", legend={"orientation": "h", "y": -0.25}, margin={"l": 58, "r": 20, "t": 55, "b": 75}, paper_bgcolor="#fff", plot_bgcolor="#fff")
    fig.update_xaxes(showline=True, linewidth=1, linecolor="#13293d", mirror=True, gridcolor="#d9dfe3")
    fig.update_yaxes(showline=True, linewidth=1, linecolor="#13293d", mirror=True, gridcolor="#d9dfe3")
    if x_limit:
        fig.update_xaxes(range=[0, x_limit])
    return fig


def figure_png(fig) -> io.BytesIO:
    image = io.BytesIO(fig.to_image(format="png", width=1200, height=650, scale=2))
    image.seek(0)
    return image


def average_metrics(summary: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"Metric": ["Specimens included", "Average peak force (kN)", "Average peak force (kgf)", "Peak force standard deviation (kgf)", "Average extension at peak (mm)", "Average end extension (mm)"], "Value": [len(summary), summary["Peak force (kN)"].mean(), summary["Peak force (kgf)"].mean(), summary["Peak force (kgf)"].std(), summary["Extension at peak (mm)"].mean(), summary["End extension (mm)"].mean()]})


def pdf_report(details: dict, metrics: pd.DataFrame, full_fig, early_fig, logo_bytes: bytes | None) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(letter), leftMargin=.35*inch, rightMargin=.35*inch, topMargin=.35*inch, bottomMargin=.35*inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SheetHeading", parent=styles["Heading2"], textColor=colors.HexColor("#13293d"), fontName="Helvetica-Bold", fontSize=11, leading=13, spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name="SmallCaps", parent=styles["Normal"], textColor=colors.HexColor("#4d5b66"), fontName="Helvetica-Bold", fontSize=7.5, leading=9))
    try:
        logo = Image(io.BytesIO(logo_bytes), width=.95*inch, height=.6*inch, kind="proportional") if logo_bytes else Paragraph("LOGO", styles["SmallCaps"])
    except Exception:
        logo = Paragraph("LOGO", styles["SmallCaps"])
    header = Table([[logo, [Paragraph("MATERIAL DATA SHEET", styles["Title"]), Paragraph("TENSILE PERFORMANCE AND PHYSICAL PROPERTIES", styles["SmallCaps"])], [Paragraph(f"<b>ITEM NUMBER</b><br/>{details['item_number']}", styles["Normal"]), Paragraph(f"<b>DESCRIPTION</b><br/>{details['description'] or '—'}", styles["Normal"])]]], colWidths=[1.15*inch, 5.3*inch, 3.45*inch])
    header.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 1.3, colors.HexColor("#13293d")), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8), ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8)]))
    physical = Table([["PRODUCT NAME", details["product_name"], "AVERAGE DIAMETER", f"{details['diameter_avg']:.4f} mm"], ["CROSS-SECTIONAL AREA", f"{details['area']:.4f} mm²", "DENIER", f"{details['denier']:.0f} den"], ["THERMAL SHRINKAGE", f"{details['shrink_pct']:.1f}%", "TEST CONDITION", "200 °C for 3 min"]], colWidths=[1.8*inch, 2.7*inch, 1.8*inch, 3.6*inch])
    physical.setStyle(TableStyle([("GRID", (0,0), (-1,-1), .7, colors.HexColor("#74828c")), ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8), ("PADDING", (0,0), (-1,-1), 6)]))
    display = metrics.copy()
    display.loc[display["Metric"] != "Specimens included", "Value"] = display.loc[display["Metric"] != "Specimens included", "Value"].map(lambda value: f"{value:.3f}")
    display.loc[display["Metric"] == "Specimens included", "Value"] = display.loc[display["Metric"] == "Specimens included", "Value"].map(lambda value: f"{value:.0f}")
    metric_table = Table([list(display.columns)] + display.values.tolist(), colWidths=[3.3*inch, 1.4*inch])
    metric_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#13293d")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .5, colors.HexColor("#74828c")), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 7.5), ("PADDING", (0,0), (-1,-1), 4)]))
    story = [header, Spacer(1,.12*inch), Paragraph("MATERIAL IDENTIFICATION AND PHYSICAL PROPERTIES", styles["SheetHeading"]), physical, Spacer(1,.14*inch), Image(figure_png(full_fig), width=9.9*inch, height=5.35*inch), Spacer(1,.16*inch), Paragraph("EARLY-STRETCH TENSILE RESPONSE", styles["SheetHeading"]), Image(figure_png(early_fig), width=9.9*inch, height=5.35*inch), Spacer(1,.12*inch), Paragraph("TENSILE AVERAGE SUMMARY", styles["SheetHeading"]), metric_table]
    doc.build(story)
    return output.getvalue()


header_logo, header_title, header_identity = st.columns([1.2, 3.2, 3.2])
with header_logo:
    logo_upload = st.file_uploader("Logo", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    if logo_upload:
        st.image(logo_upload, use_container_width=True)
    else:
        st.markdown('<div style="border:2px solid #13293d;background:#fff;padding:16px 8px;text-align:center;font-weight:700;letter-spacing:.08em;">LOGO</div>', unsafe_allow_html=True)
with header_title:
    st.markdown('<div class="sheet-title"><h1>MATERIAL DATA SHEET</h1><p>TENSILE PERFORMANCE AND PHYSICAL PROPERTIES</p></div>', unsafe_allow_html=True)
with header_identity:
    item_number = st.text_input("Item number", get_default("item_number", "######"), key="item_number")
    description = st.text_input("Description", get_default("description", ""), key="description")

section("MATERIAL IDENTIFICATION AND MANUAL MEASUREMENTS")
left, center, right = st.columns(3)
with left:
    product_name = st.text_input("Product name", get_default("product_name", ".35 Hytrel"), key="product_name")
    diameter_avg = st.number_input("Average diameter (mm)", value=float(get_default("diameter_avg", .3503)), format="%.4f", key="diameter_avg")
with center:
    area = st.number_input("Cross-sectional area (mm²)", value=float(get_default("area", .0964)), format="%.4f", key="area")
    denier = st.number_input("Denier", value=float(get_default("denier", 1122)), format="%.0f", key="denier")
with right:
    shrink_pct = st.number_input("Shrinkage at 200 °C for 3 min (%)", value=float(get_default("shrink_pct", 20.1)), format="%.1f", key="shrink_pct")
    early_limit = st.number_input("Early-stretch plot maximum (mm)", min_value=.1, value=float(get_default("early_limit", 20.0)), step=1.0, key="early_limit")

section("TENSILE TEST DATA")
uploaded = st.file_uploader("Bluehill tensile file (.id_tens)", type=["id_tens"])
if uploaded is None:
    st.info("Upload a Bluehill .id_tens file to calculate the average tensile curve. The fields above remain available for manual material data entry.")
    st.stop()
try:
    curves = parse_id_tens(uploaded.getvalue())
except ValueError as error:
    st.error(str(error))
    st.stop()
st.success(f"Found {len(curves)} raw specimen curves in {uploaded.name}.")
labels = [curve.specimen for curve in curves]
selected_labels = st.multiselect("Specimens included in average", labels, default=labels)
selected = [curve for curve in curves if curve.specimen in selected_labels]
if not selected:
    st.warning("Select at least one specimen.")
    st.stop()
average = average_curve(selected)
metrics = average_metrics(curve_summary(selected))
full_fig = plot_tensile(average, "AVERAGE TENSILE FORCE VS. EXTENSION")
early_fig = plot_tensile(average, f"AVERAGE EARLY-STRETCH RESPONSE (0–{early_limit:g} mm)", early_limit)
section("AVERAGE TENSILE RESPONSE")
plot_left, plot_right = st.columns(2)
with plot_left:
    st.plotly_chart(full_fig, use_container_width=True)
with plot_right:
    st.plotly_chart(early_fig, use_container_width=True)
section("TENSILE AVERAGE SUMMARY")
st.dataframe(metrics, use_container_width=True, hide_index=True, column_config={"Value": st.column_config.NumberColumn(format="%.3f")})
details = {"product_name": product_name, "item_number": item_number, "description": description, "diameter_avg": diameter_avg, "area": area, "denier": denier, "shrink_pct": shrink_pct}
try:
    pdf = pdf_report(details, metrics, full_fig, early_fig, logo_upload.getvalue() if logo_upload else None)
    st.download_button("DOWNLOAD MATERIAL DATA SHEET PDF", pdf, file_name=f"{product_name}_material_data_sheet.pdf", mime="application/pdf")
except Exception as error:
    st.warning(f"The app is working, but PDF export needs Kaleido available on the host: {error}")
