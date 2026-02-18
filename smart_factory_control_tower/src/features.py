from __future__ import annotations
import pandas as pd
import numpy as np


def build_maintenance_features(
    production: pd.DataFrame, 
    events: pd.DataFrame, 
    energy: pd.DataFrame
) -> pd.DataFrame:
    if production.empty or events.empty or energy.empty:
        return pd.DataFrame()

    prod = production.copy()
    prod["date"] = pd.to_datetime(prod["ts"]).dt.date
    prod["total_count"] = prod["good_count"] + prod["scrap_count"]

    prod_d = prod.groupby(["date","machine_id"], as_index=False).agg(
        total_count=("total_count","sum"),
        good_count=("good_count","sum"),
        scrap_count=("scrap_count","sum"),
        avg_cycle_time_s=("cycle_time_s","mean"),
        std_cycle_time_s=("cycle_time_s","std"),
    )
    prod_d["std_cycle_time_s"] = prod_d["std_cycle_time_s"].fillna(0.0)
    prod_d["scrap_rate"] = np.where(prod_d["total_count"]>0, prod_d["scrap_count"]/prod_d["total_count"], 0.0)

    ev = events.copy()
    ev["date"] = pd.to_datetime(ev["ts"]).dt.date
    ev_d = ev.groupby(["date","machine_id","state"], as_index=False)["duration_s"].sum()
    pivot = ev_d.pivot_table(index=["date","machine_id"], columns="state", values="duration_s", aggfunc="sum").reset_index().fillna(0.0)
    pivot.columns.name = None
    for c in ["RUN","DOWN","IDLE"]:
        if c not in pivot.columns:
            pivot[c] = 0.0
    pivot["planned_time_s"] = pivot[["RUN","DOWN","IDLE"]].sum(axis=1)
    pivot["downtime_ratio"] = np.where(pivot["planned_time_s"]>0, pivot["DOWN"]/pivot["planned_time_s"], 0.0)

    down_cnt = ev[ev["state"]=="DOWN"].groupby(["date","machine_id"], as_index=False).size().rename(columns={"size":"down_events"})
    pivot = pivot.merge(down_cnt, on=["date","machine_id"], how="left").fillna({"down_events":0})

    en = energy.copy()
    en["date"] = pd.to_datetime(en["ts"]).dt.date
    en_d = en.groupby(["date","machine_id"], as_index=False).agg(
        kwh=("kwh_interval","sum"),
        avg_kw=("kw","mean"),
        max_kw=("kw","max"),
    )
    tmp = prod_d.merge(en_d, on=["date","machine_id"], how="left")
    tmp["kwh_per_good"] = np.where(tmp["good_count"]>0, tmp["kwh"]/tmp["good_count"], np.nan)
    tmp["kwh_per_good"] = tmp.groupby("machine_id")["kwh_per_good"].transform(lambda s: s.fillna(s.median()))
    tmp = tmp.merge(pivot[["date","machine_id","downtime_ratio","down_events","RUN","DOWN","IDLE"]], on=["date","machine_id"], how="left")

    tmp = tmp.sort_values(["machine_id","date"]).reset_index(drop=True)
    for col in ["avg_cycle_time_s","std_cycle_time_s","scrap_rate","downtime_ratio","down_events","kwh_per_good","max_kw"]:
        tmp[f"{col}_r3"] = tmp.groupby("machine_id")[col].transform(lambda s: s.rolling(3, min_periods=1).mean())
        tmp[f"{col}_r7"] = tmp.groupby("machine_id")[col].transform(lambda s: s.rolling(7, min_periods=1).mean())

    tmp = tmp.fillna(0.0)
    return tmp


def build_failure_labels(events: pd.DataFrame, horizon_days: int = 1) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=["date","machine_id","label"])

    ev = events.copy()
    ev["date"] = pd.to_datetime(ev["ts"]).dt.date
    breakdown = ev[(ev["state"]=="DOWN") & (ev["reason_code"]=="BREAKDOWN")][["date","machine_id"]].drop_duplicates()
    breakdown["breakdown"] = 1

    all_dm = ev[["date","machine_id"]].drop_duplicates()
    all_dm = all_dm.sort_values(["machine_id","date"]).reset_index(drop=True)

    bset = set((r.date, r.machine_id) for r in breakdown.itertuples(index=False))
    labels = []
    for r in all_dm.itertuples(index=False):
        d = r.date
        mid = r.machine_id
        y = 0
        for k in range(0, horizon_days+1):
            dd = d + pd.Timedelta(days=k)
            dd = dd.date() if isinstance(dd, pd.Timestamp) else dd
            if (dd, mid) in bset:
                y = 1
                break
        labels.append((d, mid, y))
    return pd.DataFrame(labels, columns=["date","machine_id","label"])
