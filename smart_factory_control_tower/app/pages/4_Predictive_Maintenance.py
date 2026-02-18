import streamlit as st
import pandas as pd
from pathlib import Path
import sys
from pathlib import Path as PathLib

project_root = PathLib(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.db import connect, read_df, has_tables
from src.features import build_maintenance_features, build_failure_labels

try:
    from src.models import train_model, save_model, load_model, FEATURE_COLS, SKLEARN_AVAILABLE, JOBLIB_AVAILABLE
    MODELS_AVAILABLE = True
    if not SKLEARN_AVAILABLE:
        try:
            from sklearn.model_selection import train_test_split
            SKLEARN_AVAILABLE = True
        except:
            pass
    if not JOBLIB_AVAILABLE:
        try:
            import joblib
            JOBLIB_AVAILABLE = True
        except:
            pass
except Exception:
    MODELS_AVAILABLE = False
    FEATURE_COLS = []
    SKLEARN_AVAILABLE = False
    JOBLIB_AVAILABLE = False
    try:
        from sklearn.model_selection import train_test_split
        import joblib
        SKLEARN_AVAILABLE = True
        JOBLIB_AVAILABLE = True
        MODELS_AVAILABLE = True
        from src.models import train_model, save_model, load_model, FEATURE_COLS
    except:
        pass

st.set_page_config(page_title="Predictive Maintenance", layout="wide")
st.title("🛠️ Predictive Maintenance")
st.caption("Machine failure risk from operational data — train a model and set alert thresholds for proactive maintenance")

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
    production = read_df(con, "SELECT * FROM production")
    events = read_df(con, "SELECT * FROM events")
    energy = read_df(con, "SELECT * FROM energy")
    con.close()
except Exception as e:
    st.error(f"Database error: {e}")
    st.info("💡 Click 'Generate Initial Data' button on Home page")
    st.stop()

if not MODELS_AVAILABLE:
    st.warning("⚠️ Machine learning module not available.")
    st.info("💡 This page requires scikit-learn and joblib.")
    st.info("💡 These packages should be installed automatically from requirements.txt.")
    st.info("💡 If you see this message, please check Streamlit Cloud deployment logs.")
    st.stop()

if not SKLEARN_AVAILABLE or not JOBLIB_AVAILABLE:
    st.warning("⚠️ Some machine learning dependencies are not available.")
    missing = []
    if not SKLEARN_AVAILABLE:
        missing.append("scikit-learn")
    if not JOBLIB_AVAILABLE:
        missing.append("joblib")
    st.info(f"💡 Missing: {', '.join(missing)}")
    st.info("💡 These should be in requirements.txt. Check deployment logs if issues persist.")
    st.stop()

feats = build_maintenance_features(production, events, energy)
labels = build_failure_labels(events, horizon_days=1)

if feats.empty:
    st.error("No features generated. Check that production, events, and energy data exist.")
    st.stop()

df = feats.merge(labels, on=["date","machine_id"], how="left").fillna({"label":0})

st.caption("Trains on historical operational data and generates daily risk scores for each machine.")

colA, colB = st.columns([1,2])
with colA:
    model_type = st.selectbox("Model", ["logreg","rf"], index=0)
    retrain = st.button("Train / Retrain model")
with colB:
    st.write("Model file: `data/maintenance_model.joblib`")
    st.write("Tip: retrain after regenerating data or changing simulator parameters.")

model_path = _project_root / "data" / "maintenance_model.joblib"

model = None
metrics = None
if retrain or not model_path.exists():
    if df.empty:
        st.error("No data available for training. Please generate data first.")
        st.stop()
    model, metrics = train_model(df, model_type=model_type)
    save_model(model, model_path)
    st.success(f"Model trained & saved. Metrics: {metrics}")
else:
    try:
        model = load_model(model_path)
    except Exception as e:
        st.error(f"Error loading model: {e}. Please retrain the model.")
        st.stop()

# Latest day risk table
if df.empty:
    st.warning("No data available for risk prediction.")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
latest = df["date"].max()
today = df[df["date"]==latest].copy()

if today.empty:
    st.warning("No data for the latest date.")
    st.stop()

# Check if all required features are present
missing_cols = [col for col in FEATURE_COLS if col not in today.columns]
if missing_cols:
    st.error(f"Missing required columns: {missing_cols}. Please regenerate data.")
    st.stop()

if model is None:
    st.error("Model not loaded. Please train or load a model first.")
    st.stop()

try:
    proba = model.predict_proba(today[FEATURE_COLS])[:,1]
    today["risk"] = proba
    today = today.sort_values("risk", ascending=False)
except Exception as e:
    st.error(f"Error generating predictions: {e}")
    st.stop()

st.subheader("Latest day: machine risk ranking")
st.dataframe(today[["machine_id","risk","downtime_ratio","down_events","avg_cycle_time_s","scrap_rate","kwh_per_good"]], use_container_width=True)

threshold = st.slider("Alert threshold", min_value=0.1, max_value=0.9, value=0.6, step=0.05)
alerts = today[today["risk"]>=threshold].copy()
st.subheader("Alerts")
if alerts.empty:
    st.info("No machines above threshold.")
else:
    st.warning(f"{len(alerts)} machine(s) above risk threshold.")
    st.dataframe(alerts[["machine_id","risk","downtime_ratio","down_events","avg_cycle_time_s","scrap_rate","kwh_per_good"]], use_container_width=True)

st.subheader("Training dataset preview")
st.dataframe(df.sort_values("date", ascending=False).head(20), use_container_width=True)
