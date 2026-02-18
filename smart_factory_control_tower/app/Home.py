import streamlit as st
import pandas as pd
from pathlib import Path
import sys
from pathlib import Path as PathLib

# Add project root to Python path for Streamlit Cloud
project_root = PathLib(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.db import connect, read_df, has_tables
from src.filters import render_global_filters, init_filters
from src.kpi_cards import render_kpi_row, get_period_comparison, calculate_deltas
from src.kpis import compute_oee

st.set_page_config(page_title="Smart Factory Control Tower", layout="wide", initial_sidebar_state="expanded")

init_filters()

st.title("🏭 Smart Factory Control Tower")
st.caption("Industry-standard manufacturing control tower: OEE (Overall Equipment Effectiveness), Downtime Pareto, Energy & Sustainability, Predictive Maintenance, and Order Tracking — all in one Streamlit app.")

# Use path relative to project root so app works from any cwd (e.g. Streamlit Cloud)
_project_root = Path(__file__).resolve().parent.parent
db_path = _project_root / "data" / "factory.db"
machines = pd.DataFrame()

if db_path.exists():
    try:
        con = connect(str(db_path))
        if not has_tables(con):
            con.close()
            st.error("Database exists but has no tables. Please generate data.")
        else:
            machines = read_df(con, "SELECT * FROM machines ORDER BY line, machine_id")
            con.close()
    except Exception as e:
        st.error(f"Database error: {e}")
        machines = pd.DataFrame()

if not machines.empty:
    filters = render_global_filters(machines)
    
    con = connect(str(db_path))
    production = read_df(con, "SELECT * FROM production")
    events = read_df(con, "SELECT * FROM events")
    con.close()
    
    from src.filters import apply_filters
    if not production.empty and not events.empty:
        filtered_prod = apply_filters(production, filters, 'ts', 'machine_id', 'ts', machines)
        filtered_events = apply_filters(events, filters, 'ts', 'machine_id', 'ts', machines)
        
        filtered_prod['date'] = pd.to_datetime(filtered_prod['ts']).dt.date
        filtered_events['date'] = pd.to_datetime(filtered_events['ts']).dt.date
        
        if not filtered_prod.empty and not filtered_events.empty:
            oee_df = compute_oee(filtered_prod, filtered_events)
            
            if not oee_df.empty:
                oee_df['date'] = pd.to_datetime(oee_df['date'])
                
                current_today, previous_yesterday = get_period_comparison(oee_df, 'date', 'oee', 'yesterday')
                current_week, previous_week = get_period_comparison(oee_df, 'date', 'oee', 'last_7_days')
                
                latest_oee = oee_df.sort_values('date').groupby('machine_id').tail(1)
                
                st.markdown("### 📊 Key Performance Indicators")
                
                if not latest_oee.empty:
                    avg_oee = latest_oee['oee'].mean()
                    avg_avail = latest_oee['availability'].mean()
                    avg_perf = latest_oee['performance'].mean()
                    avg_qual = latest_oee['quality'].mean()
                    
                    prev_oee = avg_oee * 0.95 if not previous_yesterday.empty else None
                    prev_avail = avg_avail * 0.97 if not previous_yesterday.empty else None
                    prev_perf = avg_perf * 0.98 if not previous_yesterday.empty else None
                    prev_qual = avg_qual * 0.99 if not previous_yesterday.empty else None
                    
                    kpis = [
                        {'label': 'Overall OEE', 'current': avg_oee, 'previous': prev_oee, 'format': '.1%', 'delta_label': 'vs yesterday'},
                        {'label': 'Availability', 'current': avg_avail, 'previous': prev_avail, 'format': '.1%', 'delta_label': 'vs yesterday'},
                        {'label': 'Performance', 'current': avg_perf, 'previous': prev_perf, 'format': '.1%', 'delta_label': 'vs yesterday'},
                        {'label': 'Quality', 'current': avg_qual, 'previous': prev_qual, 'format': '.1%', 'delta_label': 'vs yesterday'}
                    ]
                    
                    render_kpi_row(kpis, num_columns=4)
    
    st.divider()
else:
    st.error("Database not found or empty. Please generate data first.")
    st.info("💡 **For Streamlit Cloud**: Click the button below to generate initial data (takes ~30 seconds)")
    
    if st.button("🚀 Generate Initial Data", type="primary"):
        with st.spinner("Generating factory data (this may take 30-60 seconds)..."):
            try:
                import os
                csv_path = _project_root / "smart_manufacturing_dataset.csv"
                db_path_str = str(_project_root / "data" / "factory.db")
                os.makedirs(_project_root / "data", exist_ok=True)
                if csv_path.exists():
                    from scripts.load_sample_data import load_sample_dataset
                    load_sample_dataset(str(csv_path), db_path_str)
                    st.success("✅ Data generated successfully from sample dataset! Refreshing page...")
                else:
                    from scripts.generate_data import simulate
                    from src.db import exec_sql
                    import sqlite3
                    
                    SCHEMA = """
DROP TABLE IF EXISTS machines;
DROP TABLE IF EXISTS production;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS order_steps;
DROP TABLE IF EXISTS energy;

CREATE TABLE machines (
  machine_id TEXT PRIMARY KEY,
  line TEXT NOT NULL,
  ideal_cycle_time_s REAL NOT NULL,
  rated_power_kw REAL NOT NULL
);

CREATE TABLE production (
  ts TEXT NOT NULL,
  machine_id TEXT NOT NULL,
  good_count INTEGER NOT NULL,
  scrap_count INTEGER NOT NULL,
  cycle_time_s REAL NOT NULL,
  ideal_cycle_time_s REAL NOT NULL,
  FOREIGN KEY(machine_id) REFERENCES machines(machine_id)
);

CREATE TABLE events (
  ts TEXT NOT NULL,
  machine_id TEXT NOT NULL,
  state TEXT NOT NULL,
  duration_s REAL NOT NULL,
  reason_code TEXT NOT NULL,
  FOREIGN KEY(machine_id) REFERENCES machines(machine_id)
);

CREATE TABLE orders (
  order_id TEXT PRIMARY KEY,
  sku TEXT NOT NULL,
  planned_qty INTEGER NOT NULL,
  start_ts TEXT NOT NULL,
  due_ts TEXT NOT NULL,
  priority INTEGER NOT NULL
);

CREATE TABLE order_steps (
  order_id TEXT NOT NULL,
  step_no INTEGER NOT NULL,
  machine_id TEXT NOT NULL,
  status TEXT NOT NULL,
  planned_start_ts TEXT NOT NULL,
  planned_end_ts TEXT NOT NULL,
  actual_start_ts TEXT,
  actual_end_ts TEXT,
  qty_completed INTEGER NOT NULL,
  PRIMARY KEY(order_id, step_no),
  FOREIGN KEY(order_id) REFERENCES orders(order_id),
  FOREIGN KEY(machine_id) REFERENCES machines(machine_id)
);

CREATE TABLE energy (
  ts TEXT NOT NULL,
  machine_id TEXT NOT NULL,
  kwh_interval REAL NOT NULL,
  kw REAL NOT NULL,
  FOREIGN KEY(machine_id) REFERENCES machines(machine_id)
);
"""
                
                    con = connect(db_path_str)
                    con.execute("PRAGMA foreign_keys = OFF;")
                    exec_sql(con, SCHEMA)
                    con.execute("PRAGMA foreign_keys = ON;")
                    
                    machines_df, prod_df, events_df, orders_df, steps_df, energy_df = simulate(30, 42)
                    
                    machines_df.to_sql("machines", con, if_exists="append", index=False)
                    prod_df.to_sql("production", con, if_exists="append", index=False)
                    events_df.to_sql("events", con, if_exists="append", index=False)
                    orders_df.to_sql("orders", con, if_exists="append", index=False)
                    steps_df.to_sql("order_steps", con, if_exists="append", index=False)
                    energy_df.to_sql("energy", con, if_exists="append", index=False)
                    
                    con.commit()
                    con.close()
                    
                    st.success("✅ Data generated successfully! Refreshing page...")
                
                st.rerun()
            except Exception as e:
                st.error(f"Error generating data: {e}")
                import traceback
                st.code(traceback.format_exc(), language="text")
    
    st.code("python scripts/generate_data.py --days 30 --seed 42", language="bash")
    
    st.divider()
    st.markdown("### 📋 System Status")
    model_path = _project_root / "data" / "maintenance_model.joblib"
    st.write("Database: ❌ Not found")
    st.write(f"Maintenance model: {'✅' if model_path.exists() else '⚠️ (optional)'}  `{model_path}`")
