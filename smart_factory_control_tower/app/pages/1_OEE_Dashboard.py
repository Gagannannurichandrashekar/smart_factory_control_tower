import streamlit as st
import pandas as pd
import sys
from pathlib import Path as PathLib

project_root = PathLib(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.db import connect, read_df, has_tables
from src.filters import render_global_filters, init_filters, apply_filters
from src.kpis import compute_oee, downtime_pareto
from src.kpi_cards import render_kpi_row, get_period_comparison

st.set_page_config(page_title="OEE Dashboard", layout="wide")
st.title("🏆 OEE Dashboard")
st.caption("Overall Equipment Effectiveness: Availability × Performance × Quality — industry-standard manufacturing KPI")

init_filters()

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
    production = read_df(con, "SELECT * FROM production")
    events = read_df(con, "SELECT * FROM events")
    con.close()
except Exception as e:
    st.error(f"Database error: {e}")
    st.info("💡 Click 'Generate Initial Data' button on Home page")
    st.stop()

if machines.empty:
    st.error("No data. Run: python scripts/generate_data.py")
    st.stop()

# Render global filters
filters = render_global_filters(machines)

# Apply filters to data (including shift filtering)
filtered_prod = apply_filters(
    production, 
    filters, 
    date_col='ts',  # Use ts for shift filtering
    machine_col='machine_id',
    ts_col='ts',
    machines_df=machines
)
filtered_events = apply_filters(
    events, 
    filters, 
    date_col='ts',  # Use ts for shift filtering
    machine_col='machine_id',
    ts_col='ts',
    machines_df=machines
)

# Convert to date for OEE calculation
filtered_prod['date'] = pd.to_datetime(filtered_prod['ts']).dt.date
filtered_events['date'] = pd.to_datetime(filtered_events['ts']).dt.date

oee = compute_oee(filtered_prod, filtered_events)

if oee.empty:
    st.warning("No OEE data computed. Check that production and events data exist.")
    st.stop()

oee["date"] = pd.to_datetime(oee["date"])

# KPI Cards with deltas
st.markdown("### 📊 OEE Metrics")
latest = oee.sort_values("date").groupby("machine_id").tail(1)

if not latest.empty:
    # Get period comparisons for deltas
    current_today, previous_yesterday = get_period_comparison(oee, 'date', 'oee', 'yesterday')
    
    avg_oee = latest['oee'].mean()
    avg_avail = latest['availability'].mean()
    avg_perf = latest['performance'].mean()
    avg_qual = latest['quality'].mean()
    
    # Calculate previous values for comparison
    prev_oee = previous_yesterday['oee'].mean() if not previous_yesterday.empty else None
    prev_avail = previous_yesterday['availability'].mean() if not previous_yesterday.empty else None
    prev_perf = previous_yesterday['performance'].mean() if not previous_yesterday.empty else None
    prev_qual = previous_yesterday['quality'].mean() if not previous_yesterday.empty else None
    
    kpis = [
        {'label': 'Overall OEE', 'current': avg_oee, 'previous': prev_oee, 'format': '.1%', 'delta_label': 'vs yesterday'},
        {'label': 'Availability', 'current': avg_avail, 'previous': prev_avail, 'format': '.1%', 'delta_label': 'vs yesterday'},
        {'label': 'Performance', 'current': avg_perf, 'previous': prev_perf, 'format': '.1%', 'delta_label': 'vs yesterday'},
        {'label': 'Quality', 'current': avg_qual, 'previous': prev_qual, 'format': '.1%', 'delta_label': 'vs yesterday'}
    ]
    
    render_kpi_row(kpis, num_columns=4)
else:
    st.warning("No data available for metrics.")

st.subheader("OEE trend (average across selected scope)")
trend = oee.groupby("date", as_index=False).agg(
    availability=("availability","mean"),
    performance=("performance","mean"),
    quality=("quality","mean"),
    oee=("oee","mean"),
)
metric = st.selectbox("Metric", ["oee","availability","performance","quality"], index=0)
trend_display = trend[["date", metric]].copy()
trend_display["date"] = pd.to_datetime(trend_display["date"])
chart_data = trend_display.set_index("date")
st.line_chart(chart_data)
st.dataframe(trend[["date", metric]].style.format({metric: '{:.2%}'}), use_container_width=True)

st.subheader("OEE by machine (latest day)")
latest_day = oee["date"].max()
oee_latest_day = oee[oee["date"]==latest_day].sort_values("oee", ascending=False)
st.dataframe(oee_latest_day[["machine_id","availability","performance","quality","oee","good_count","scrap_count","total_count"]], use_container_width=True)

st.subheader("Downtime Pareto Analysis")
pareto = downtime_pareto(filtered_events)
if pareto.empty:
    st.info("No downtime found in selection.")
else:
    pareto_top = pareto.head(10)
    bar_data = pareto_top.set_index("reason_code")[["downtime_s"]]
    st.bar_chart(bar_data)

    # Display table with cumulative percentage
    display_pareto = pareto.head(15).copy()
    st.dataframe(
        display_pareto[["reason_code", "downtime_s", "pct", "cum_pct"]].style.format({
            'downtime_s': '{:,.0f}',
            'pct': '{:.1%}',
            'cum_pct': '{:.1%}'
        }),
        use_container_width=True
    )
    
    # Highlight 80/20 rule
    if len(display_pareto) > 0:
        top_80 = display_pareto[display_pareto['cum_pct'] <= 0.80]
        if len(top_80) > 0:
            st.info(f"💡 **80/20 Rule**: Top {len(top_80)} reasons account for {top_80['cum_pct'].max():.1%} of downtime. Focus improvement efforts here.")
