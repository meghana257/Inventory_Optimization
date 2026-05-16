import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Inventory Health Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# LIGHT THEME STYLING
# ─────────────────────────────────────────
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .block-container { padding-top: 1.5rem; }
        .metric-card {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
            text-align: center;
        }
        .metric-label {
            font-size: 0.78rem;
            color: #6c757d;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .metric-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: #212529;
            margin-top: 0.2rem;
        }
        .metric-sub {
            font-size: 0.75rem;
            color: #adb5bd;
            margin-top: 0.1rem;
        }
        .section-title {
            font-size: 1rem;
            font-weight: 700;
            color: #343a40;
            margin-bottom: 0.5rem;
            padding-bottom: 0.3rem;
            border-bottom: 2px solid #e9ecef;
        }
        div[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e9ecef;
        }
        .status-stockout    { color: #dc3545; font-weight: 700; }
        .status-reorder     { color: #fd7e14; font-weight: 700; }
        .status-low         { color: #ffc107; font-weight: 700; }
        .status-healthy     { color: #198754; font-weight: 700; }
        .status-overstock   { color: #6c757d; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

COLORS = {
    "primary"   : "#4361ee",
    "success"   : "#2dc653",
    "warning"   : "#f4a261",
    "danger"    : "#e63946",
    "neutral"   : "#6c757d",
    "A"         : "#4361ee",
    "B"         : "#f4a261",
    "C"         : "#e63946",
    "STOCKOUT"  : "#e63946",
    "REORDER NOW": "#fd7e14",
    "LOW"       : "#ffc107",
    "HEALTHY"   : "#2dc653",
    "OVERSTOCK" : "#6c757d",
}

# ─────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────
@st.cache_data
def load_data():
    kpi       = pd.read_csv("output/inventory_kpis_sku_country.csv")
    country   = pd.read_csv("output/country_summary.csv")
    reorders  = pd.read_csv("output/sku_country_needs_reorder.csv")

    kpi["latest_date"] = pd.to_datetime(kpi["latest_date"])
    kpi["year"]        = kpi["year"].astype(int)

    return kpi, country, reorders

kpi_df, country_df, reorder_df = load_data()

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/box.png", width=60)
    st.markdown("## 📦 Inventory Dashboard")
    st.markdown("---")

    dashboard = st.radio(
        "Select Dashboard",
        ["📈 Demand Trends", "🏥 Inventory Health"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("### 🔽 Filters")

    # Country filter
    countries = sorted(kpi_df["country"].unique())
    selected_country = st.selectbox("Country", countries)

    # Filter data by country
    filtered = kpi_df[kpi_df["country"] == selected_country]

    # Category filter
    categories = ["All"] + sorted(filtered["category"].unique())
    selected_category = st.selectbox("Category", categories)
    if selected_category != "All":
        filtered = filtered[filtered["category"] == selected_category]

    # Year filter
    years = sorted(filtered["year"].unique(), reverse=True)
    selected_years = st.multiselect("Year", years, default=years)
    filtered = filtered[filtered["year"].isin(selected_years)]

    # Dashboard-specific filters
    if dashboard == "🏥 Inventory Health":
        st.markdown("---")
        abc_filter = st.multiselect("ABC Segment", ["A", "B", "C"], default=["A", "B", "C"])
        status_filter = st.multiselect(
            "Status",
            ["STOCKOUT", "REORDER NOW", "LOW", "HEALTHY", "OVERSTOCK"],
            default=["STOCKOUT", "REORDER NOW", "LOW", "HEALTHY", "OVERSTOCK"]
        )
        filtered = filtered[
            filtered["abc"].isin(abc_filter) &
            filtered["status"].isin(status_filter)
        ]

    if dashboard == "📈 Demand Trends":
        # SKU filter
        skus = ["All"] + sorted(filtered["sku_id"].unique())
        selected_sku = st.selectbox("SKU", skus)
        if selected_sku != "All":
            filtered = filtered[filtered["sku_id"] == selected_sku]

    st.markdown("---")
    st.caption(f"Showing **{len(filtered):,}** SKU × Year rows")
    st.caption(f"Country: **{selected_country}**")


# ─────────────────────────────────────────
# HELPER: METRIC CARD
# ─────────────────────────────────────────
def metric_card(label, value, sub=""):
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# DASHBOARD 1 — DEMAND TRENDS
# ═══════════════════════════════════════════════════════
if dashboard == "📈 Demand Trends":

    st.markdown(f"## 📈 Demand Trends — {selected_country}")
    st.markdown("---")

    # ── KPI Cards ──────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Total Units Sold", f"{filtered['total_units'].sum():,.0f}", "units")
    with c2:
        metric_card("Total Revenue", f"€{filtered['total_revenue'].sum():,.0f}", "EUR")
    with c3:
        metric_card("Avg Daily Demand", f"{filtered['avg_daily_demand'].mean():,.1f}", "units/day")
    with c4:
        metric_card("Avg CV (Variability)", f"{filtered['cv_demand'].mean():.3f}", "lower = steadier")
    with c5:
        metric_card("Unique SKUs", f"{filtered['sku_id'].nunique():,}", "in selection")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Demand & Revenue Trends ────────────────────────
    st.markdown('<div class="section-title">📊 Yearly Demand & Revenue Trends</div>', unsafe_allow_html=True)

    trend = (
        filtered.groupby("year")
                .agg(total_units=("total_units", "sum"), total_revenue=("total_revenue", "sum"))
                .reset_index()
    )

    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(
            trend, x="year", y="total_units",
            markers=True, title="Units Sold by Year",
            color_discrete_sequence=[COLORS["primary"]],
            labels={"total_units": "Units Sold", "year": "Year"}
        )
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.line(
            trend, x="year", y="total_revenue",
            markers=True, title="Revenue by Year (€)",
            color_discrete_sequence=[COLORS["success"]],
            labels={"total_revenue": "Revenue (€)", "year": "Year"}
        )
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Top 10 SKUs ───────────────────────────────────
    st.markdown('<div class="section-title">🏆 Top 10 SKUs by Revenue</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        top_skus_rev = (
            filtered.groupby(["sku_id", "sku_name"])["total_revenue"]
                    .sum().reset_index()
                    .sort_values("total_revenue", ascending=True)
                    .tail(10)
        )
        fig = px.bar(
            top_skus_rev, x="total_revenue", y="sku_name",
            orientation="h", title="Top 10 SKUs — Revenue (€)",
            color_discrete_sequence=[COLORS["primary"]],
            labels={"total_revenue": "Revenue (€)", "sku_name": "SKU"}
        )
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        top_skus_units = (
            filtered.groupby(["sku_id", "sku_name"])["total_units"]
                    .sum().reset_index()
                    .sort_values("total_units", ascending=True)
                    .tail(10)
        )
        fig = px.bar(
            top_skus_units, x="total_units", y="sku_name",
            orientation="h", title="Top 10 SKUs — Units Sold",
            color_discrete_sequence=[COLORS["success"]],
            labels={"total_units": "Units Sold", "sku_name": "SKU"}
        )
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Category Breakdown ─────────────────────────────
    st.markdown('<div class="section-title">🗂️ Category Breakdown</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        cat_rev = (
            filtered.groupby("category")["total_revenue"]
                    .sum().reset_index()
                    .sort_values("total_revenue", ascending=False)
        )
        fig = px.pie(
            cat_rev, names="category", values="total_revenue",
            title="Revenue Share by Category",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        cat_year = (
            filtered.groupby(["category", "year"])["total_units"]
                    .sum().reset_index()
        )
        fig = px.bar(
            cat_year, x="year", y="total_units", color="category",
            barmode="stack", title="Units Sold by Category & Year",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            labels={"total_units": "Units Sold", "year": "Year"}
        )
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Demand Variability Distribution ───────────────
    st.markdown('<div class="section-title">📉 Demand Variability (CV Distribution)</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(
            filtered, x="cv_demand", nbins=30,
            title="CV Distribution across SKUs",
            color_discrete_sequence=[COLORS["primary"]],
            labels={"cv_demand": "Coefficient of Variation"}
        )
        fig.add_vline(x=0.5, line_dash="dash", line_color="orange", annotation_text="X/Y threshold")
        fig.add_vline(x=1.0, line_dash="dash", line_color="red",    annotation_text="Y/Z threshold")
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        xyz_counts = filtered["xyz"].value_counts().reset_index()
        xyz_counts.columns = ["xyz", "count"]
        fig = px.bar(
            xyz_counts, x="xyz", y="count",
            title="XYZ Segment Distribution",
            color="xyz",
            color_discrete_map={"X": COLORS["success"], "Y": COLORS["warning"], "Z": COLORS["danger"]},
            labels={"xyz": "XYZ Segment", "count": "Number of SKUs"}
        )
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════
# DASHBOARD 2 — INVENTORY HEALTH
# ═══════════════════════════════════════════════════════
elif dashboard == "🏥 Inventory Health":

    st.markdown(f"## 🏥 Inventory Health — {selected_country}")
    st.markdown("---")

    # ── KPI Cards ──────────────────────────────────────
    stockout_count  = (filtered["status"] == "STOCKOUT").sum()
    reorder_count   = (filtered["status"] == "REORDER NOW").sum()
    overstock_count = (filtered["status"] == "OVERSTOCK").sum()
    avg_dos         = filtered["days_of_supply"].mean()
    avg_stockout_rt = filtered["stockout_rate"].mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("🔴 Stockout SKUs",   f"{stockout_count}",        "needs urgent action")
    with c2:
        metric_card("🟠 Reorder Now",     f"{reorder_count}",         "below reorder point")
    with c3:
        metric_card("⚪ Overstock SKUs",  f"{overstock_count}",       "capital tied up")
    with c4:
        metric_card("Avg Days of Supply", f"{avg_dos:.1f}",           "days remaining")
    with c5:
        metric_card("Avg Stockout Rate",  f"{avg_stockout_rt:.1%}",   "% of days out of stock")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── ABC × XYZ Matrix + Status Donut ───────────────
    st.markdown('<div class="section-title">🔲 ABC × XYZ Matrix & Status Distribution</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        from itertools import product as iproduct
        all_combos = pd.DataFrame(
            [{"abc": a, "xyz": x} for a, x in iproduct(["A","B","C"], ["X","Y","Z"])]
        )
        matrix_data = (
            filtered.groupby(["abc", "xyz"])["sku_id"]
                    .count().reset_index(name="count")
        )
        matrix_data = all_combos.merge(matrix_data, on=["abc","xyz"], how="left").fillna(0)
        matrix_pivot = matrix_data.pivot(index="abc", columns="xyz", values="count").reindex(
            index=["A","B","C"], columns=["X","Y","Z"]
        ).fillna(0)

        fig = px.imshow(
            matrix_pivot,
            text_auto=True,
            color_continuous_scale="Blues",
            title="ABC × XYZ Matrix (SKU Count)",
            labels={"color": "SKU Count"}
        )
        fig.update_layout(paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        status_counts = filtered["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        color_map = {s: COLORS[s] for s in COLORS if s in status_counts["status"].values}
        fig = px.pie(
            status_counts, names="status", values="count",
            title="Inventory Status Distribution",
            hole=0.45,
            color="status",
            color_discrete_map=color_map
        )
        fig.update_layout(paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Stock Position ─────────────────────────────────
    st.markdown('<div class="section-title">📦 Stock Position — Current vs Reorder Point vs Safety Stock</div>', unsafe_allow_html=True)

    top_n = st.slider("Number of SKUs to display", min_value=5, max_value=30, value=15)

    stock_chart = (
        filtered.sort_values("total_revenue", ascending=False)
                .head(top_n)[["sku_name", "current_stock", "reorder_point", "safety_stock"]]
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Current Stock",  x=stock_chart["sku_name"], y=stock_chart["current_stock"],  marker_color=COLORS["primary"]))
    fig.add_trace(go.Bar(name="Reorder Point",  x=stock_chart["sku_name"], y=stock_chart["reorder_point"],  marker_color=COLORS["warning"]))
    fig.add_trace(go.Bar(name="Safety Stock",   x=stock_chart["sku_name"], y=stock_chart["safety_stock"],   marker_color=COLORS["danger"]))
    fig.update_layout(
        barmode="group",
        title=f"Top {top_n} SKUs by Revenue — Stock Position",
        xaxis_tickangle=-35,
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Scatter: Days of Supply vs Stockout Rate ───────
    st.markdown('<div class="section-title">🔍 Days of Supply vs Stockout Rate</div>', unsafe_allow_html=True)

    scatter_df = filtered.dropna(subset=["days_of_supply", "stockout_rate"])
    fig = px.scatter(
        scatter_df,
        x="days_of_supply",
        y="stockout_rate",
        color="abc",
        size="total_revenue",
        hover_data=["sku_name", "status", "current_stock"],
        color_discrete_map={"A": COLORS["A"], "B": COLORS["B"], "C": COLORS["C"]},
        title="Days of Supply vs Stockout Rate (sized by Revenue)",
        labels={
            "days_of_supply": "Days of Supply",
            "stockout_rate": "Stockout Rate",
            "abc": "ABC Segment"
        }
    )
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Reorder Action Table ───────────────────────────
    st.markdown('<div class="section-title">🚨 Reorder Action List</div>', unsafe_allow_html=True)

    reorder_filtered = reorder_df[reorder_df["country"] == selected_country].copy()

    if selected_category != "All":
        reorder_filtered = reorder_filtered[reorder_filtered["category"] == selected_category]

    if len(reorder_filtered) == 0:
        st.success("✅ No SKUs require reordering for the current selection.")
    else:
        st.warning(f"⚠️ **{len(reorder_filtered)} SKUs** require immediate attention.")

        display_cols = [
            "sku_id", "sku_name", "category", "brand", "abc", "xyz",
            "current_stock", "reorder_point", "safety_stock",
            "days_of_supply", "stockout_rate", "status"
        ]
        display_cols = [c for c in display_cols if c in reorder_filtered.columns]

        st.dataframe(
            reorder_filtered[display_cols]
                .sort_values(["abc", "days_of_supply"], ascending=[True, True])
                .reset_index(drop=True),
            use_container_width=True,
            height=400
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Country Summary ────────────────────────────────
    st.markdown('<div class="section-title">🌍 Country-Level Summary</div>', unsafe_allow_html=True)
    st.dataframe(
        country_df.reset_index().sort_values("total_revenue", ascending=False),
        use_container_width=True
    )
