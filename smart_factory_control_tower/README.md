# Smart Factory Control Tower

Comprehensive manufacturing operations dashboard providing real-time visibility into equipment performance, production planning, energy consumption, and predictive maintenance insights.

## Features

- **OEE Dashboard**: Overall Equipment Effectiveness tracking with availability, performance, and quality metrics. Includes downtime Pareto analysis for root cause identification.
- **Predictive Maintenance**: Machine learning-based failure prediction with risk scoring and alerting. Supports logistic regression and random forest models.
- **Production Order Tracking**: Work-in-progress monitoring with order status, due date risk assessment, and step-by-step execution timelines.
- **Energy Monitoring**: Energy consumption analysis with peak demand tracking and efficiency metrics per production unit.

Built with **Streamlit** for rapid deployment and **SQLite** for lightweight data storage. Includes data generation utilities for testing and demonstration.

---

## 1) Setup

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

pip install -r requirements.txt
```

---

## 2) Generate synthetic factory data (SQLite)

```bash
python scripts/generate_data.py --days 30 --seed 42
```

This creates: `data/factory.db`

---

## 3) Run the Streamlit app

```bash
streamlit run app/Home.py
```

---

## Deploy to Streamlit Cloud

1. **Push to GitHub**: Initialize git and push to a GitHub repository
2. **Connect to Streamlit Cloud**: Go to https://share.streamlit.io
3. **Deploy**: Select your repo and set main file to `app/Home.py`
4. **First Run**: The app will automatically generate data on first deployment

See `DEPLOYMENT.md` for detailed deployment instructions.

---

## Project structure

```
smart_factory_control_tower/
  app/
    Home.py
    pages/
      0_Alert_Center.py
      1_OEE_Dashboard.py
      2_Production_Orders.py
      3_Energy_Monitoring.py
      4_Predictive_Maintenance.py
      5_Industry_4.0_Insights.py
  data/
    factory.db (generated)
    maintenance_model.joblib (generated)
  scripts/
    generate_data.py
    train_maintenance_model.py
  src/
    db.py
    kpis.py
    features.py
    models.py
    viz.py
    filters.py
    kpi_cards.py
    config.py
    logger.py
    industry4_features.py
  requirements.txt
```

---

## Architecture

- **Frontend**: Streamlit web application with multi-page dashboard
- **Backend**: Python with pandas for data processing
- **Database**: SQLite for operational data storage
- **Machine Learning**: scikit-learn for predictive maintenance models
- **Visualization**: Matplotlib for charts and graphs

## Extending the System

The codebase is designed for easy extension:

- **Data Integration**: Replace data simulator with real-time sources (MQTT, Kafka, OPC-UA, SCADA systems)
- **Database**: Migrate to PostgreSQL or TimescaleDB for production scale
- **MLOps**: Integrate MLflow for model versioning and experiment tracking
- **Authentication**: Add user management and role-based access control
- **Alerts**: Implement notification system (email, SMS, Slack) for threshold breaches
- **API**: Expose REST endpoints for external system integration

## Requirements

- Python 3.9+
- See `requirements.txt` for package dependencies
