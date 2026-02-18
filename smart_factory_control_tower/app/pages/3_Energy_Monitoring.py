import streamlit as st
import pandas as pd
import sys
from pathlib import Path as PathLib

project_root = PathLib(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.db import connect, read_df, has_tables

st.set_page_config(page_title="Energy Monitoring", layout="wide")
st.title("⚡ Energy Monitoring")
st.caption("Power consumption, peak demand, and energy-per-unit — essential for cost and sustainability reporting")

_project_root = PathLib(__file__).resolve().parent.parent.parent
db_path = _project_root / "data" / "factory.db"
if not db_path.exists():
    st.error("Database not found. Please generate data first.")
    st.info("💡 Click 'Generate Initial Data' button on Home page")
    st.stop()

try:
    con = connect(str(db_path))
    if not has_tables(con):
        con.close()
        st.error("Database exists but has no tables. Please generate data first.")
        st.info("💡 Click 'Generate Initial Data' button on Home page")
        st.stop()
    machines = read_df(con, "SELECT * FROM machines ORDER BY line, machine_id")
    energy = read_df(con, "SELECT * FROM energy")
    production = read_df(con, "SELECT * FROM production")
    con.close()
except Exception as e:
    st.error(f"Database error: {e}")
    st.info("💡 Click 'Generate Initial Data' button on Home page")
    st.stop()

if energy.empty:
    st.error("No data. Run: python scripts/generate_data.py")
    st.stop()

energy["ts"] = pd.to_datetime(energy["ts"])
production["ts"] = pd.to_datetime(production["ts"])

line = st.selectbox("Line", options=["All"] + sorted(machines["line"].unique().tolist()))
if line != "All":
    mids = machines[machines["line"]==line]["machine_id"].tolist()
    energy = energy[energy["machine_id"].isin(mids)]
    production = production[production["machine_id"].isin(mids)]

energy["date"] = energy["ts"].dt.date
production["date"] = production["ts"].dt.date
production["good"] = production["good_count"]

if energy.empty:
    st.warning("No energy data available after filtering.")
    st.stop()

daily_e = energy.groupby("date", as_index=False).agg(kwh=("kwh_interval","sum"), peak_kw=("kw","max"), avg_kw=("kw","mean"))
daily_p = production.groupby("date", as_index=False).agg(good=("good","sum")) if not production.empty else pd.DataFrame(columns=["date", "good"])
daily = daily_e.merge(daily_p, on="date", how="left").fillna({"good":0})
daily["kwh_per_good"] = daily.apply(lambda r: (r["kwh"]/r["good"]) if r["good"]>0 else 0.0, axis=1)

if daily.empty:
    st.warning("No daily aggregated data available.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Total kWh (selected)", f"{daily['kwh'].sum():,.0f}")

avg_peak_kw = daily['peak_kw'].mean() if not daily.empty else 0.0
col2.metric("Avg peak kW", f"{avg_peak_kw:.1f}")

avg_kwh_per_good = daily['kwh_per_good'].mean() if not daily.empty else 0.0
col3.metric("Avg kWh / good unit", f"{avg_kwh_per_good:.3f}")

daily["date"] = pd.to_datetime(daily["date"])
daily_indexed = daily.set_index("date")

st.subheader("Daily Energy (kWh)")
st.line_chart(daily_indexed[["kwh"]])

st.subheader("Daily Peak Demand (kW)")
st.line_chart(daily_indexed[["peak_kw"]])

st.subheader("Energy per Good Unit (kWh/unit)")
st.line_chart(daily_indexed[["kwh_per_good"]])

st.subheader("Raw daily table")
st.dataframe(daily.sort_values("date", ascending=False), use_container_width=True)
