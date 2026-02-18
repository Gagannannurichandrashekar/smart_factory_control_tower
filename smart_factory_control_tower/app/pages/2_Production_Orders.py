import streamlit as st
import pandas as pd
import sys
from pathlib import Path as PathLib

project_root = PathLib(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.db import connect, read_df, has_tables

st.set_page_config(page_title="Production Orders", layout="wide")
st.title("📦 Production Order Tracking")
st.caption("Track orders by status, due date, and step progress — planned vs actual for on-time delivery")

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
    orders = read_df(con, "SELECT * FROM orders ORDER BY due_ts ASC")
    steps = read_df(con, "SELECT * FROM order_steps ORDER BY order_id, step_no")
    con.close()
except Exception as e:
    st.error(f"Database error: {e}")
    st.info("💡 Click 'Generate Initial Data' button on Home page")
    st.stop()

if orders.empty:
    st.error("No data. Run: python scripts/generate_data.py")
    st.stop()

orders["start_ts"] = pd.to_datetime(orders["start_ts"])
orders["due_ts"] = pd.to_datetime(orders["due_ts"])

now = pd.Timestamp.now()

# Basic WIP / risk flags
step_status = steps.groupby("order_id")["status"].apply(list).reset_index()
orders = orders.merge(step_status, on="order_id", how="left")
orders["status"] = orders["status"].apply(lambda s: "UNKNOWN" if not isinstance(s, list) else ("COMPLETED" if all(x=="COMPLETED" for x in s) else ("IN_PROGRESS" if any(x=="IN_PROGRESS" for x in s) else "NOT_STARTED")))
orders["due_risk"] = (orders["due_ts"] < now) & (orders["status"] != "COMPLETED")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Orders", f"{len(orders)}")
col2.metric("Completed", f"{(orders['status']=='COMPLETED').sum()}")
col3.metric("In Progress", f"{(orders['status']=='IN_PROGRESS').sum()}")
col4.metric("Past Due (not completed)", f"{orders['due_risk'].sum()}")

st.subheader("Orders list")
flt = st.multiselect("Filter status", options=["COMPLETED","IN_PROGRESS","NOT_STARTED","UNKNOWN"], default=["IN_PROGRESS","NOT_STARTED","UNKNOWN"])
view = orders[orders["status"].isin(flt)].copy()
st.dataframe(view[["order_id","sku","planned_qty","priority","start_ts","due_ts","status","due_risk"]], use_container_width=True)

st.subheader("Order details")
selected = st.selectbox("Select an order", options=orders["order_id"].tolist())
ssteps = steps[steps["order_id"]==selected].copy()
for c in ["planned_start_ts","planned_end_ts","actual_start_ts","actual_end_ts"]:
    ssteps[c] = pd.to_datetime(ssteps[c], errors="coerce")

st.dataframe(ssteps[["step_no","machine_id","status","planned_start_ts","planned_end_ts","actual_start_ts","actual_end_ts","qty_completed"]], use_container_width=True)

# Simple timeline chart (planned vs actual)
st.caption("Planned vs Actual step windows")
chart_df = ssteps.copy()
chart_df["planned_hours"] = (chart_df["planned_end_ts"] - chart_df["planned_start_ts"]).dt.total_seconds()/3600
chart_df["actual_hours"] = (chart_df["actual_end_ts"] - chart_df["actual_start_ts"]).dt.total_seconds()/3600
chart_df["actual_hours"] = chart_df["actual_hours"].fillna(0.0)

st.bar_chart(chart_df.set_index("step_no")[["planned_hours","actual_hours"]])
