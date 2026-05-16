# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.2
#   kernelspec:
#     display_name: base
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Inventory Health Dashboard — SKU × Country
#
# **Dataset:** FMCG multi-country sales (Kaggle, ~1M rows, 3 years)
#
# **KPIs computed per (SKU × Country):**
# 1. **Demand stats** — total units, avg daily demand, std daily demand, CV
# 2. **Revenue stats** — total revenue, % of country revenue
# 3. **ABC segmentation** — by revenue (Pareto: A=top 70%, B=next 20%, C=last 10%)
# 4. **XYZ segmentation** — by demand variability (X<0.5, Y=0.5-1.0, Z>1.0)
# 5. **Safety Stock** — SS = Z × σ_daily × √lead_time   (Z=1.65 → 95% service level)
# 6. **Reorder Point** — ROP = (μ_daily × lead_time) + SS
# 7. **Current health** — stock_on_hand, days_of_supply, stockout_rate, status flag

# %% [markdown]
# ## 1. Load + basic inspection

# %%
## Sync notebook to PowerPoint

import subprocess
import os
from pathlib import Path

# Export notebook to PowerPoint
def sync_notebook_to_pptx():
    notebook_path = "inventory_health_dashboard.ipynb"
    output_path = "inventory_health_dashboard.pptx"
    
    # Convert using nbconvert
    cmd = [
        "jupyter", "nbconvert",
        "--to", "slides",
        "--post", "serve",  # Remove if you don't want auto-open
        notebook_path,
        "--output", output_path
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"✓ Notebook synced to → {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Conversion failed: {e}")
        print("Install nbconvert: pip install nbconvert")

# Run sync
if __name__ == "__main__":
    sync_notebook_to_pptx()


# %%
import numpy as np
import pandas as pd


df = pd.read_csv("E:/Inventory Optimization/data/sales_data.csv")
df.head()


# %%
df.info()

# %%
df.date = pd.to_datetime(df.date, format="%d-%m-%Y")
df.info()

# %%
# start with Italy data for testing

italy = df[df["country"] == "Italy"]

# SKU sold in multiple stores on same day
multi_store = (
    italy.groupby(["date", "sku_id"])["store_id"]
           .nunique()
           .reset_index(name="n_stores")
)

multi_store = multi_store[multi_store["n_stores"] > 1]

# Get required rows and columns
result = italy.merge(
    multi_store[["date", "sku_id"]],
    on=["date", "sku_id"],
    how="inner"
)[["date", "store_id", "sku_id", "units_sold"]]

result.sort_values(["date", "sku_id", "store_id"]).head()


#So the data in the dataset is at the store level, but we need to analyze it at the country level.
# We will aggregate the data by date, country, and SKU to get the total units sold per day for each SKU in France.

# %%
#Pick only the relevant columns to speed up loading and reduce memory usage

USECOLS = [
    "date", "month", "year", "country", "sku_id", "sku_name", "category", "brand",
    "units_sold", "net_sales", "stock_on_hand", "stock_out_flag",
    "lead_time_days", "purchase_cost",
]

df = italy[USECOLS].copy()
df.head()



# %% [markdown]
# ## 2. Aggregate to SKU × Country × Day
# Multiple stores per country exist. We sum to one row per (sku, country, day).

# %%
#Daily aggregation at sku and country level

df.drop_duplicates(subset=["date", "country", "sku_id"], keep="first", inplace=True)  # remove duplicates if any

daily = (
    df.groupby(["sku_id", "country", "date"], observed=True)
      .agg(
          units_sold     = ("units_sold", "sum"),
          net_sales      = ("net_sales", "sum"),
          stock_on_hand  = ("stock_on_hand", "sum"),
          stockouts      = ("stock_out_flag", "max"),  # if any store had stockout, it's a stockout day for that SKU-country
          n_store_days   = ("stock_out_flag", "size"),
          lead_time_days = ("lead_time_days", "mean"),
          purchase_cost  = ("purchase_cost", "mean"),
      )
      .reset_index()
)
print(f"Daily SKU × Country rows: {len(daily):,}")
daily.head()

# # df.to_excel("E:/Inventory Optimization/output/italy_daily_sales_data.xlsx", index=False)
daily.head()


# %% [markdown]
# ## 3. KPI table per SKU × Country - Month-Year

# %%
# Pull the latest snapshot per SKU x Country (most recent stock_on_hand)

# Convert date to datetime (format: DD-MM-YYYY)
daily["date"] = pd.to_datetime(daily["date"], format="%d-%m-%Y")
daily["year_month"] = daily["date"].dt.to_period("M")

latest = (
    daily.sort_values("date")
         .groupby(["sku_id", "country",'year_month'], observed=True)
         .tail(1)[["sku_id", "country", "year_month", "stock_on_hand"]]
         .rename(columns={"stock_on_hand": "current_stock"})
)

monthly_kpi = (
    daily.groupby(["sku_id", "country",'year_month'], observed=True)
         .agg(
             total_units    = ("units_sold", "sum"),
             total_revenue  = ("net_sales", "sum"),
             avg_daily_demand = ("units_sold", "mean"),
             std_daily_demand = ("units_sold", "std"),
             active_days    = ("units_sold", "size"),
             stockout_days  = ("stockouts", "sum"),
             lead_time_days = ("lead_time_days", "mean"),
             unit_cost      = ("purchase_cost", "mean"),
         )
         .reset_index()
         .merge(latest, on=["sku_id", "country", "year_month"], how="left")
)

# Add SKU metadata back (category, brand, name) — first non-null per SKU
meta = df[["sku_id", "sku_name", "category", "brand"]].drop_duplicates("sku_id")
monthly_kpi = monthly_kpi.merge(meta, on="sku_id", how="left")

monthly_kpi["std_daily_demand"] = monthly_kpi["std_daily_demand"].fillna(0)
monthly_kpi["cv_demand"] = (monthly_kpi["std_daily_demand"] / monthly_kpi["avg_daily_demand"]).replace([np.inf, -np.inf], np.nan).fillna(0).round(3)
monthly_kpi["stockout_rate"] = (monthly_kpi["stockout_days"] / monthly_kpi["active_days"]).round(3)

# Check for duplicates
duplicates = monthly_kpi.duplicated(subset=["sku_id", "country", "year_month"], keep=False).sum()
print(f"KPI rows: {len(monthly_kpi):,}  (= unique SKU × Country × Month)")
print(f"Duplicate rows (same sku_id, country, year_month): {duplicates}")
monthly_kpi.head()

# %% [markdown]
# ## KPI Calculation - SKU x COUNTRY - YEARLY

# %%
# Create year column from existing year_month
monthly_kpi["year"] = monthly_kpi["year_month"].dt.year

# Yearly KPI table
yearly_kpi = (
    monthly_kpi.groupby(["sku_id", "country", "year"], observed=True)
               .agg(
                   total_units       = ("total_units", "sum"),
                   total_revenue     = ("total_revenue", "sum"),
                   avg_daily_demand  = ("avg_daily_demand", "mean"),
                   std_daily_demand  = ("std_daily_demand", "mean"),
                   active_days       = ("active_days", "sum"),
                   stockout_days     = ("stockout_days", "sum"),
                   current_stock     = ("current_stock", "last"),
                   lead_time_days    = ("lead_time_days", "mean"),
                   unit_cost         = ("unit_cost", "mean"),
               )
               .reset_index()
)

# Recalculate yearly KPIs
yearly_kpi["cv_demand"] = (
    yearly_kpi["std_daily_demand"] /
    yearly_kpi["avg_daily_demand"]
).replace([np.inf, -np.inf], np.nan).fillna(0).round(3)

yearly_kpi["stockout_rate"] = (
    yearly_kpi["stockout_days"] /
    yearly_kpi["active_days"]
).round(3)

# Add SKU metadata
meta = df[["sku_id", "sku_name", "category", "brand"]].drop_duplicates("sku_id")

yearly_kpi = yearly_kpi.merge(meta, on="sku_id", how="left")

# Check duplicates
duplicates = yearly_kpi.duplicated(
    subset=["sku_id", "country", "year"],
    keep=False
).sum()

print(f"Yearly KPI rows: {len(yearly_kpi):,}")
print(f"Duplicate rows: {duplicates}")

yearly_kpi.head()


# %% [markdown]
# ## 4. ABC segmentation (per country)
# Each country gets its own Pareto: A = top 70 % of revenue, B = next 20 %, C = bottom 10 %.

# %%

def assign_abc(group):

    # Sort SKUs by revenue
    group = group.sort_values("total_revenue", ascending=False).copy()

    # Cumulative revenue contribution
    cum_pct = group["total_revenue"].cumsum() / group["total_revenue"].sum()

    # ABC classification
    group["abc"] = np.where(
        cum_pct <= 0.70, "A",
        np.where(cum_pct <= 0.90, "B", "C")
    )

    return group


# Apply country-wise
yearly_kpi = (
    yearly_kpi.groupby("country", group_keys=False)
       .apply(assign_abc)
)

# Check distribution
yearly_kpi["abc"].value_counts().sort_index()   

# %% [markdown]
# ## 5. XYZ segmentation (demand variability)
# Based on CV of daily demand. Lower CV = more predictable.
#
# - **X**: CV ≤ 0.5  (steady, easy to forecast)
# - **Y**: 0.5 < CV ≤ 1.0 (moderate variability)
# - **Z**: CV > 1.0 (lumpy / erratic)

# %%
# XYZ classification
yearly_kpi["xyz"] = "Z"

yearly_kpi.loc[
    yearly_kpi["cv_demand"] <= 1.0, "xyz"
] = "Y"

yearly_kpi.loc[
    yearly_kpi["cv_demand"] <= 0.5, "xyz"
] = "X"

# Combine ABC and XYZ
yearly_kpi["abc_xyz"] = (
    yearly_kpi["abc"] + yearly_kpi["xyz"]
)

# Count categories
yearly_kpi["abc_xyz"].value_counts().sort_index()

# %% [markdown]
# ## 6. Safety Stock + Reorder Point
# Standard formulas:
# - **Safety Stock** =  Z × σ_daily × √(lead_time_days)
# - **Reorder Point** = (μ_daily × lead_time_days) + Safety Stock

# %%
# Service levels by ABC segmentation (revenue importance)
# A = 99% service level (Z=2.33) — high-revenue items, can't stockout
# B = 95% service level (Z=1.65) — medium-revenue items
# C = 90% service level (Z=1.28) — low-revenue items, acceptable stockouts

abc_service_levels = {
    "A": 2.33,  # 99% service level
    "B": 1.65,  # 95% service level
    "C": 1.28,  # 90% service level
}

yearly_kpi["service_level_z"] = yearly_kpi["abc"].map(abc_service_levels)

yearly_kpi["safety_stock"] = (yearly_kpi["service_level_z"] * yearly_kpi["std_daily_demand"] * np.sqrt(yearly_kpi["lead_time_days"])).round().astype(int)
yearly_kpi["reorder_point"] = ((yearly_kpi["avg_daily_demand"] * yearly_kpi["lead_time_days"]) + yearly_kpi["safety_stock"]).round().astype(int)
yearly_kpi["days_of_supply"] = (yearly_kpi["current_stock"] / yearly_kpi["avg_daily_demand"]).replace([np.inf, -np.inf], np.nan).round(1)


# %% [markdown]
# ## 7. Health status flag
# - 🔴 **STOCKOUT**     — current_stock = 0
# - 🟠 **REORDER NOW**  — current_stock ≤ ROP
# - 🟡 **LOW**          — current_stock ≤ 1.5 × ROP
# - 🟢 **HEALTHY**      — current_stock > 1.5 × ROP
# - ⚪ **OVERSTOCK**    — current_stock > 4 × ROP  (capital tied up)

# %%
def status(row):
    cur, rop = row["current_stock"], row["reorder_point"]
    if cur == 0:           return "STOCKOUT"
    if rop == 0:           return "HEALTHY"
    if cur <= rop:         return "REORDER NOW"
    if cur <= 1.5 * rop:   return "LOW"
    if cur > 4 * rop:      return "OVERSTOCK"
    return "HEALTHY"

yearly_kpi["status"] = yearly_kpi.apply(status, axis=1)
yearly_kpi["status"].value_counts()

# %% [markdown]
# ## 8. Final KPI table — preview & save

# %%
# Define output paths
OUT_KPI = "E:/Inventory Optimization/output/inventory_kpis_sku_country.csv"
OUT_COUNTRY = "E:/Inventory Optimization/output/country_summary.csv"
OUT_REORDERS = "E:/Inventory Optimization/output/sku_country_needs_reorder.csv"

# Ensure yearly_kpi has country as a proper column (reset index without dropping)
if isinstance(yearly_kpi.index, pd.MultiIndex) or "country" not in yearly_kpi.columns:
    yearly_kpi = yearly_kpi.reset_index()

# Add latest date per SKU×Country
daily_max_dates = daily.groupby(["sku_id", "country"])["date"].max().reset_index().rename(columns={"date": "latest_date"})
yearly_kpi = yearly_kpi.merge(daily_max_dates, on=["sku_id", "country"], how="left")

cols = [
    "sku_id", "sku_name", "category", "brand", "country", "total_units", "total_revenue",
    "avg_daily_demand", "std_daily_demand", "cv_demand", "abc", "xyz", "abc_xyz", "lead_time_days", "safety_stock",
    "reorder_point", "current_stock", "days_of_supply", "stockout_days", "stockout_rate", "status", "latest_date",
]

# Check missing columns
missing = [c for c in cols if c not in yearly_kpi.columns]
print("Missing columns:", missing)

# Final output dataset
kpi_out = yearly_kpi[cols].copy()

# Format numeric columns
kpi_out["avg_daily_demand"] = kpi_out["avg_daily_demand"].round(2)
kpi_out["std_daily_demand"] = kpi_out["std_daily_demand"].round(2)
kpi_out["total_revenue"] = kpi_out["total_revenue"].round(2)

# Export
kpi_out.to_csv(OUT_KPI, index=False)

print(f"Saved → {OUT_KPI}")
print(f"Rows: {len(kpi_out):,}")

kpi_out.head()

# %% [markdown]
# ## 9. Country-level rollup

# %%
country_summary = (
    kpi_out.groupby("country", observed=True)
       .agg(
           skus              = ("sku_id", "nunique"),
           total_revenue     = ("total_revenue", "sum"),
           total_units       = ("total_units", "sum"),
           avg_stockout_rate = ("stockout_rate", "mean"),
           reorder_now       = ("status", lambda s: (s == "REORDER NOW").sum()),
           stockout_skus     = ("status", lambda s: (s == "STOCKOUT").sum()),
           overstock_skus    = ("status", lambda s: (s == "OVERSTOCK").sum()),
       )
       .round(3)
       .sort_values("total_revenue", ascending=False)
)
country_summary.to_csv(OUT_COUNTRY)
country_summary

# %% [markdown]
# ## 10. Action list — SKUs that need reordering now

# %%
needs_reorder = (
    kpi_out[kpi_out["status"].isin(["STOCKOUT", "REORDER NOW"])]
    .sort_values(["abc", "total_revenue"], ascending=[True, False])
)
needs_reorder.to_csv(OUT_REORDERS, index=False)
print(f"{len(needs_reorder):,} SKU × Country pairs need reordering → {OUT_REORDERS}")
needs_reorder.head(30)

# %% [markdown]
# ## 11. ABC × XYZ matrix (count of SKU × Country pairs)

# %%
matrix = (
    kpi_out.pivot_table(index="abc", columns="xyz", values="sku_id", aggfunc="count", fill_value=0)
       .reindex(index=["A","B","C"], columns=["X","Y","Z"], fill_value=0)
)
matrix.loc["Total"] = matrix.sum()
matrix["Total"]     = matrix.sum(axis=1)
matrix
