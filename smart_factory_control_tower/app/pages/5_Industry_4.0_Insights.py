import streamlit as st
import pandas as pd
import sys
from pathlib import Path as PathLib

project_root = PathLib(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.db import connect, read_df, has_tables
from src.filters import render_global_filters, init_filters, apply_filters
from src.kpis import compute_oee
from src.industry4_features import (
    calculate_carbon_footprint,
    calculate_sustainability_score,
    calculate_digital_twin_health,
    calculate_lean_metrics,
    calculate_smart_factory_index,
    detect_anomalies
)

st.set_page_config(page_title="Industry 4.0 Insights", layout="wide")
st.title("🌐 Industry 4.0 Insights")
st.caption("Smart Factory Index, Digital Twin health, sustainability, lean metrics, and anomaly detection")

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
    energy = read_df(con, "SELECT * FROM energy")
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

# Apply filters
filtered_prod = apply_filters(production, filters, 'ts', 'machine_id', 'ts', machines)
filtered_events = apply_filters(events, filters, 'ts', 'machine_id', 'ts', machines)
filtered_energy = apply_filters(energy, filters, 'ts', 'machine_id', 'ts', machines)

if filtered_prod.empty or filtered_events.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# Calculate OEE
oee_df = compute_oee(filtered_prod, filtered_events)

if oee_df.empty:
    st.warning("No OEE data computed.")
    st.stop()

# Latest metrics
latest_oee = oee_df.sort_values('date').groupby('machine_id').tail(1)
avg_oee = latest_oee['oee'].mean()
avg_scrap_rate = latest_oee['scrap_count'].sum() / latest_oee['total_count'].sum() if latest_oee['total_count'].sum() > 0 else 0

# Energy metrics
filtered_energy['ts'] = pd.to_datetime(filtered_energy['ts'])
daily_energy = filtered_energy.groupby('machine_id')['kwh_interval'].sum().mean()
energy_efficiency = 1.0 - (filtered_energy['kw'].std() / filtered_energy['kw'].mean()) if filtered_energy['kw'].mean() > 0 else 0.5

# Industry 4.0 Metrics
st.markdown("### 📊 Smart Factory Index")

col1, col2, col3, col4 = st.columns(4)

# Digital Twin Health
dt_health = calculate_digital_twin_health(
    avg_oee,
    latest_oee['downtime_ratio'].mean() if 'downtime_ratio' in latest_oee.columns else 0.1,
    avg_scrap_rate,
    filtered_energy['kw'].std() / filtered_energy['kw'].mean() if filtered_energy['kw'].mean() > 0 else 0.1
)

with col1:
    st.metric("Digital Twin Health", f"{dt_health['health_score']:.1f}", delta=dt_health['risk_level'])

# Sustainability Score
sustainability = calculate_sustainability_score(avg_oee, energy_efficiency, avg_scrap_rate)
with col2:
    st.metric("Sustainability Score", f"{sustainability:.1f}/100")

# Carbon Footprint
total_kwh = filtered_energy['kwh_interval'].sum()
carbon_kg = calculate_carbon_footprint(total_kwh)
with col3:
    st.metric("CO2 Emissions", f"{carbon_kg:,.0f} kg", help="Based on energy consumption")

# Smart Factory Index
pm_score = 0.7  # Placeholder - would come from actual PM model performance
sf_index = calculate_smart_factory_index(avg_oee, pm_score, energy_efficiency, 1 - avg_scrap_rate)
with col4:
    st.metric("Smart Factory Index", f"{sf_index:.1f}/100")

st.divider()

# Lean Manufacturing Metrics
st.markdown("### 🎯 Lean Manufacturing Metrics")
lean_metrics = calculate_lean_metrics(filtered_prod, filtered_events)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Takt Time", f"{lean_metrics['takt_time']:.2f}s", help="Customer demand rate")
col2.metric("Cycle Efficiency", f"{lean_metrics['cycle_efficiency']:.1%}")
col3.metric("Value-Added Ratio", f"{lean_metrics['value_added_ratio']:.1%}")
col4.metric("Waste Ratio", f"{lean_metrics['waste_ratio']:.1%}", delta=f"-{lean_metrics['waste_ratio']:.1%}", delta_color="inverse")

st.divider()

# Anomaly Detection
st.markdown("### 🔍 Anomaly Detection")
if 'kwh_interval' in filtered_energy.columns:
    energy_anomalies = detect_anomalies(
        filtered_energy.groupby('machine_id')['kwh_interval'].sum().reset_index(),
        'kwh_interval'
    )
    
    anomaly_machines = energy_anomalies[energy_anomalies['is_anomaly']]
    if not anomaly_machines.empty:
        st.warning(f"⚠️ {len(anomaly_machines)} machine(s) detected with energy consumption anomalies")
        st.dataframe(anomaly_machines[['machine_id', 'kwh_interval', 'z_score']], use_container_width=True)
    else:
        st.success("✅ No energy consumption anomalies detected")

st.divider()

# Digital Twin Health Breakdown
st.markdown("### 🏥 Digital Twin Health Breakdown")
health_df = pd.DataFrame([dt_health])
st.dataframe(health_df[['health_score', 'risk_level', 'oee_contribution', 'availability_contribution', 'quality_contribution', 'stability_contribution']], use_container_width=True)

