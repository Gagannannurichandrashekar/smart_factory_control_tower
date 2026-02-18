import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import sys
from pathlib import Path as PathLib

project_root = PathLib(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.db import connect, read_df, has_tables
from src.filters import render_global_filters, init_filters, apply_filters
from src.features import build_maintenance_features, build_failure_labels

try:
    from src.models import load_model, FEATURE_COLS, SKLEARN_AVAILABLE, JOBLIB_AVAILABLE
    MODELS_AVAILABLE = True
    if SKLEARN_AVAILABLE is None:
        SKLEARN_AVAILABLE = False
    if JOBLIB_AVAILABLE is None:
        JOBLIB_AVAILABLE = False
except (ImportError, AttributeError, Exception) as e:
    MODELS_AVAILABLE = False
    FEATURE_COLS = []
    SKLEARN_AVAILABLE = False
    JOBLIB_AVAILABLE = False

st.set_page_config(page_title="Alert Center", layout="wide")
st.title("🚨 Alert Center")
st.caption("Unified view of maintenance risk, energy spikes, and schedule-at-risk orders — act on what matters first")

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
    orders = read_df(con, "SELECT * FROM orders")
    con.close()
except Exception as e:
    st.error(f"Database error: {e}")
    st.info("💡 Click 'Generate Initial Data' button on Home page")
    st.stop()

if machines.empty:
    st.error("No data available. Run: python scripts/generate_data.py")
    st.stop()

filters = render_global_filters(machines)

alerts = []

filtered_production = apply_filters(production, filters, 'ts', 'machine_id', 'ts', machines)
filtered_events_alert = apply_filters(events, filters, 'ts', 'machine_id', 'ts', machines)
filtered_energy = apply_filters(energy, filters, 'ts', 'machine_id', 'ts', machines)

# Maintenance Alerts
st.subheader("🔧 Maintenance Risk Alerts")
if not MODELS_AVAILABLE:
    st.info("ℹ️ Machine learning features are not available. Other alerts will still work.")
elif not SKLEARN_AVAILABLE or not JOBLIB_AVAILABLE:
    st.info("ℹ️ Maintenance predictions require scikit-learn and joblib. Other alerts will still work.")
else:
    model_path = _project_root / "data" / "maintenance_model.joblib"
    if model_path.exists():
        try:
            feats = build_maintenance_features(filtered_production, filtered_events_alert, filtered_energy)
            if not feats.empty:
                model = load_model(model_path)
                feats["date"] = pd.to_datetime(feats["date"])
                latest = feats["date"].max()
                today = feats[feats["date"] == latest].copy()
                
                if not today.empty and all(col in today.columns for col in FEATURE_COLS):
                    proba = model.predict_proba(today[FEATURE_COLS])[:, 1]
                    today["risk"] = proba
                    high_risk = today[today["risk"] >= 0.6].copy()
                    
                    if not high_risk.empty:
                        for _, row in high_risk.iterrows():
                            alerts.append({
                                'type': 'Maintenance',
                                'severity': 'High' if row['risk'] >= 0.8 else 'Medium',
                                'machine_id': row['machine_id'],
                                'message': f"High failure risk: {row['risk']:.1%}",
                                'risk_score': row['risk'],
                                'timestamp': latest
                            })
                        
                        st.dataframe(
                            high_risk[["machine_id", "risk", "downtime_ratio", "down_events"]].sort_values("risk", ascending=False),
                            use_container_width=True
                        )
                    else:
                        st.info("✅ No high-risk maintenance alerts")
            else:
                st.warning("Insufficient data for maintenance predictions")
        except Exception as e:
            st.error(f"Error loading maintenance model: {e}")
    else:
        st.info("Maintenance model not trained. Visit Predictive Maintenance page to train.")

st.divider()

# Energy Alerts
st.subheader("⚡ Energy Consumption Alerts")
filtered_energy["ts"] = pd.to_datetime(filtered_energy["ts"])
filtered_energy["date"] = filtered_energy["ts"].dt.date
latest_energy_date = filtered_energy["date"].max() if not filtered_energy.empty else None

if latest_energy_date:
    daily_energy = filtered_energy.groupby(["date", "machine_id"], as_index=False).agg(
        kwh=("kwh_interval", "sum"),
        peak_kw=("kw", "max")
    )
    
    latest_daily = daily_energy[daily_energy["date"] == latest_energy_date] if latest_energy_date else pd.DataFrame()
    if not latest_daily.empty:
        avg_peak = latest_daily["peak_kw"].mean()
        threshold = avg_peak * 1.3  # 30% above average
        
        high_energy = latest_daily[latest_daily["peak_kw"] > threshold]
        if not high_energy.empty:
            for _, row in high_energy.iterrows():
                alerts.append({
                    'type': 'Energy',
                    'severity': 'Medium',
                    'machine_id': row['machine_id'],
                    'message': f"Peak demand spike: {row['peak_kw']:.1f} kW",
                    'peak_kw': row['peak_kw'],
                    'timestamp': latest_energy_date
                })
            
            st.dataframe(high_energy[["machine_id", "peak_kw", "kwh"]], use_container_width=True)
        else:
            st.info("✅ No energy consumption alerts")
    else:
        st.warning("No energy data available for selected filters")
else:
    st.warning("No energy data available")

st.divider()

# Schedule Alerts
st.subheader("📦 Production Schedule Alerts")
orders["due_ts"] = pd.to_datetime(orders["due_ts"])
now = pd.Timestamp.now()

con = connect(str(db_path))
steps = read_df(con, "SELECT * FROM order_steps")
con.close()

step_status = steps.groupby("order_id")["status"].apply(list).reset_index()
orders = orders.merge(step_status, on="order_id", how="left")
orders["status"] = orders["status"].apply(
    lambda s: "COMPLETED" if isinstance(s, list) and all(x == "COMPLETED" for x in s)
    else ("IN_PROGRESS" if isinstance(s, list) and any(x == "IN_PROGRESS" for x in s) else "NOT_STARTED")
)
orders["due_risk"] = (orders["due_ts"] < now) & (orders["status"] != "COMPLETED")

at_risk_orders = orders[orders["due_risk"]].copy()
if not at_risk_orders.empty:
    for _, row in at_risk_orders.iterrows():
        days_overdue = (now - row["due_ts"]).days
        alerts.append({
            'type': 'Schedule',
            'severity': 'High' if days_overdue > 1 else 'Medium',
            'order_id': row['order_id'],
            'message': f"Order overdue: {days_overdue} day(s)",
            'days_overdue': days_overdue,
            'timestamp': row['due_ts']
        })
    
    st.dataframe(
        at_risk_orders[["order_id", "sku", "due_ts", "status"]],
        use_container_width=True
    )
else:
    st.info("✅ No schedule risk alerts")

st.divider()

# Alert Summary
st.subheader("📊 Alert Summary")
if alerts:
    alerts_df = pd.DataFrame(alerts)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Alerts", len(alerts))
    with col2:
        high_severity = len(alerts_df[alerts_df['severity'] == 'High'])
        st.metric("High Severity", high_severity, delta=f"{high_severity} critical")
    with col3:
        by_type = alerts_df['type'].value_counts()
        st.metric("Alert Types", len(by_type))
    
    # Alert breakdown by type
    st.bar_chart(by_type)
else:
    st.success("🎉 No active alerts! All systems operating normally.")

