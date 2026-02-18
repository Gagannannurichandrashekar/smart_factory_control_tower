from __future__ import annotations
import argparse
import pandas as pd
from src.db import connect, read_df
from src.features import build_maintenance_features, build_failure_labels
from src.models import train_model, save_model

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=str, default="data/factory.db")
    p.add_argument("--model_type", type=str, choices=["logreg","rf"], default="logreg")
    p.add_argument("--horizon_days", type=int, default=1)
    args = p.parse_args()

    con = connect(args.db)
    production = read_df(con, "SELECT * FROM production")
    events = read_df(con, "SELECT * FROM events")
    energy = read_df(con, "SELECT * FROM energy")
    con.close()

    feats = build_maintenance_features(production, events, energy)
    labels = build_failure_labels(events, horizon_days=args.horizon_days)

    df = feats.merge(labels, on=["date","machine_id"], how="left").fillna({"label":0})
    model, metrics = train_model(df, model_type=args.model_type)
    save_model(model)

    print("✅ Saved model to data/maintenance_model.joblib")
    print("Metrics:", metrics)

if __name__ == "__main__":
    main()
