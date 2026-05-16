# 📦 Inventory Health Dashboard — SKU × Country

> An interactive supply chain analytics tool built on real-world FMCG data spanning multiple countries, brands, and SKUs. It enables procurement and operations teams to monitor demand trends across daily, monthly, and yearly granularities while tracking critical inventory KPIs such as safety stock, reorder points, and stockout risk. SKUs are intelligently segmented using ABC (revenue importance) and XYZ (demand variability) classification to prioritize restocking decisions and minimize both stockouts and overstock situations.

---

## 📊 Dataset Link:
Source: https://www.kaggle.com/datasets/robertocarlost/fmcg-multi-country-sales-dataset?select=fmcg_sales_3years_1M_rows.csv


## 🧠 KPIs Computed per SKU × Country × Year

| KPI                  | Description                                        |
|----------------------|----------------------------------------------------|
| `avg_daily_demand`   | Average units sold per day                         |
| `std_daily_demand`   | Standard deviation of daily demand                 |
| `cv_demand`          | Coefficient of Variation (demand variability)      |
| `safety_stock`       | Buffer stock based on service level and lead time  |
| `reorder_point`      | Stock level at which to trigger a new order        |
| `days_of_supply`     | How many days current stock will last              |
| `stockout_rate`      | % of days with zero stock                          |
| `status`             | STOCKOUT / REORDER NOW / LOW / HEALTHY / OVERSTOCK |

---

## 🔤 Segmentation Logic

### ABC Segmentation (Revenue Importance)
| Segment | Criteria              | Service Level  |
|---------|-----------------------|----------------|
| A       | Top 70% of revenue    | 99% (Z = 2.33) |
| B       | Next 20% of revenue   | 95% (Z = 1.65) |
| C       | Bottom 10% of revenue | 90% (Z = 1.28) |

### XYZ Segmentation (Demand Variability)
| Segment | CV Threshold | Meaning |
|---------|-------------|---------|
| X | CV ≤ 0.50 | Steady, easy to forecast |
| Y | CV ≤ 1.00 | Moderate variability |
| Z | CV > 1.00 | Erratic / lumpy demand |

---

## ⚙️ Formulas

```
Safety Stock  = Z_score × σ_daily × √(lead_time_days)
Reorder Point = (μ_daily × lead_time_days) + Safety Stock
Days of Supply = current_stock / μ_daily
CV            = σ_daily / μ_daily
```

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python | Core language |
| Pandas | Data wrangling |
| NumPy | Numerical computation |
| Streamlit | Interactive dashboard |
| Plotly | Visualizations |
| Jupyter | Notebook environment |

---

## 📌 Key Design Decisions

- **Store → Country aggregation** — raw data is at store level; aggregated to SKU × Country × Day for analysis
- **Configurable thresholds** — ABC/XYZ cutoffs and service levels are defined in a single config block, not hardcoded
- **Year-aware snapshots** — stock and KPIs tracked per year, not collapsed into a single snapshot
- **Vectorized ABC classification** — uses `groupby().transform()` instead of `apply()` to avoid pandas index issues

---

## 👤 Author

Bommena Meghana
- GitHub: [meghana257](#)
- LinkedIn: [https://www.linkedin.com/in/meghana-bommena-696092183/](#)

---

