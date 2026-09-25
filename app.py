from __future__ import annotations

import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from tens_parser import TensileCurve, average_curve, curve_summary, parse_id_tens


st.set_page_config(page_title="Tensile Manual Builder", page_icon="📈", layout="wide")
st.title("Tensile Manual Builder")
st.caption("Upload a Bluehill .id_tens file, review the curves, and create a product manual PDF.")


def get_default(key: str, value):
    return st.session_state.get(key, value)


with st.sidebar:
    st.header("Product details")
    product_name = st.text_input("Product name", get_default("product_name", ".35 Hytrel"), key="product_name")
    item_number = st.text_input("Item number", get_default("item_number", "######"), key="item_number")
    description = st.text_input("Description", get_default("description", ""), key="description")

    st.subheader("Physical properties")
    diameter_min = st.number_input("Diameter minimum (mm)", value=float(get_default("diameter_min", 0.3471)), format="%.4f", key="diameter_min")
    diameter_max = st.number_input("Diameter maximum (mm)", value=float(get_default("diameter_max", 0.3552)), format="%.4f", key="diameter_max")
    diameter_avg = st.number_input("Diameter average (mm)", value=float(get_default("diameter_avg", 0.3503)), format="%.4f", key="diameter_avg")
    area = st.number_input("Cross-sectional area (mm²)", value=float(get_default("area", 0.0964)), format="%.4f", key="area")
    denier = st.number_input("Denier", value=float(get_default("denier", 1122)), format="%.0f", key="denier")

    st.subheader("Shrinkage")
    shrink_pct = st.number_input("Shrinkage average (%)", value=float(get_default("shrink_pct", 20.1)), format="%.1f", key="shrink_pct")
    shrink_temp = st.number_input("Test temperature (°C)", value=float(get_default("shrink_temp", 200)), format="%.0f", key="shrink_temp")
    shrink_minutes = st.number_input("Test duration (min)", value=float(get_default("shrink_minutes", 3)), format="%.1f", key="shrink_minutes")

    st.subheader("Plot settings")
    early_limit = st.number_input("Early-stretch maximum (mm)", min_value=0.1, value=float(get_default("early_limit", 20.0)), step=1.0, key="early_limit")
    uploaded = st.file_uploader("Bluehill tensile file (.id_tens)", type=["id_tens"])


def plot_tensile(curves: list[TensileCurve], average: pd.DataFrame, title: str, x_limit: float | None = None):
    fig = go.Figure()
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]
    for index, curve in enumerate(curves):
        fig.add_trace(
            go.Scatter(
                x=curve.data.extension_mm,
                y=curve.data.force_kN,
                mode="lines",
                name=curve.specimen,
                line={"color": palette[index % len(palette)], "width": 1.2},
                opacity=0.45,
            )
        )
    fig.add_trace(
        go.Scatter(
            x=average.extension_mm,
            y=average.mean_force_kN + average.std_force_kN,
            mode="lines",
            line={"width": 0},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=average.extension_mm,
            y=average.mean_force_kN - average.std_force_kN,
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(0, 70, 160, 0.15)",
            line={"width": 0},
            name="±1 SD",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=average.extension_mm,
            y=average.mean_force_kN,
            mode="lines",
            name="Average curve",
            line={"color": "#003f7f", "width": 3},
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Extension (mm)",
        yaxis_title="Force (kN)",
        template="plotly_white",
        legend={"orientation": "h", "y": -0.25},
        margin={"l": 55, "r": 20, "t": 50, "b": 75},
    )
    if x_limit:
        fig.update_xaxes(range=[0, x_limit])
    return fig


def figure_png(fig) -> io.BytesIO:
    image = io.BytesIO(fig.to_image(format="png", width=1200, height=650, scale=2))
    image.seek(0)
    return image


def pdf_report(details: dict, summary: pd.DataFrame, full_fig, early_fig) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(letter), leftMargin=0.35 * inch, rightMargin=0.35 * inch, topMargin=0.35 * inch, bottomMargin=0.35 * inch)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"<b>{details['product_name']}</b> &nbsp;&nbsp; Item: {details['item_number']}", styles["Title"])]
    if details["description"]:
        story.append(Paragraph(details["description"], styles["Normal"]))
    story.append(Spacer(1, 0.12 * inch))
    properties = [
        ["Diameter min", f"{details['diameter_min']:.4f} mm", "Diameter max", f"{details['diameter_max']:.4f} mm", "Denier", f"{details['denier']:.0f}"],
        ["Diameter avg", f"{details['diameter_avg']:.4f} mm", "Area", f"{details['area']:.4f} mm²", "Shrinkage", f"{details['shrink_pct']:.1f}% at {details['shrink_temp']:.0f} °C for {details['shrink_minutes']:g} min"],
    ]
    table = Table(properties, colWidths=[0.85 * inch, 0.95 * inch, 0.85 * inch, 1.05 * inch, 0.7 * inch, 2.7 * inch])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef3f8")), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b0bcc8")), ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"), ("FONTNAME", (4, 0), (4, -1), "Helvetica-Bold"), ("PADDING", (0, 0), (-1, -1), 5)]))
    story.extend([table, Spacer(1, 0.14 * inch), Image(figure_png(full_fig), width=9.9 * inch, height=5.35 * inch)])
    story.extend([Spacer(1, 0.18 * inch), Paragraph("Early-stretch tensile plot", styles["Heading2"]), Image(figure_png(early_fig), width=9.9 * inch, height=5.35 * inch)])
    display = summary.copy()
    for col in display.columns[1:]:
        display[col] = display[col].map(lambda value: f"{value:.3f}")
    summary_table = Table([list(display.columns)] + display.values.tolist(), repeatRows=1)
    summary_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003f7f")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7), ("PADDING", (0, 0), (-1, -1), 3)]))
    story.extend([Spacer(1, 0.1 * inch), Paragraph("Individual specimen summary", styles["Heading2"]), summary_table])
    doc.build(story)
    return output.getvalue()


if uploaded is None:
    st.info("Upload a Bluehill .id_tens file to begin. The defaults in the sidebar are filled with the .35 Hytrel example.")
    st.stop()

try:
    curves = parse_id_tens(uploaded.getvalue())
except ValueError as error:
    st.error(str(error))
    st.stop()

st.success(f"Found {len(curves)} raw specimen curves in {uploaded.name}.")
labels = [curve.specimen for curve in curves]
selected_labels = st.multiselect("Specimens included in average curve", labels, default=labels)
selected = [curve for curve in curves if curve.specimen in selected_labels]
if not selected:
    st.warning("Select at least one specimen.")
    st.stop()

average = average_curve(selected)
summary = curve_summary(selected)
full_fig = plot_tensile(selected, average, "Tensile force vs. extension")
early_fig = plot_tensile(selected, average, f"Early stretch: 0–{early_limit:g} mm", early_limit)

left, right = st.columns(2)
with left:
    st.plotly_chart(full_fig, use_container_width=True)
with right:
    st.plotly_chart(early_fig, use_container_width=True)

st.subheader("Specimen tensile summary")
st.dataframe(summary, use_container_width=True, hide_index=True, column_config={
    "Peak force (kN)": st.column_config.NumberColumn(format="%.4f"),
    "Peak force (kgf)": st.column_config.NumberColumn(format="%.2f"),
    "Extension at peak (mm)": st.column_config.NumberColumn(format="%.2f"),
    "End extension (mm)": st.column_config.NumberColumn(format="%.2f"),
    "End time (s)": st.column_config.NumberColumn(format="%.2f"),
})

details = {
    "product_name": product_name,
    "item_number": item_number,
    "description": description,
    "diameter_min": diameter_min,
    "diameter_max": diameter_max,
    "diameter_avg": diameter_avg,
    "area": area,
    "denier": denier,
    "shrink_pct": shrink_pct,
    "shrink_temp": shrink_temp,
    "shrink_minutes": shrink_minutes,
}
try:
    pdf = pdf_report(details, summary, full_fig, early_fig)
    st.download_button("Download product manual PDF", pdf, file_name=f"{product_name}_manual.pdf", mime="application/pdf")
except Exception as error:
    st.warning(f"The app is working, but PDF export needs Kaleido available on the host: {error}")

