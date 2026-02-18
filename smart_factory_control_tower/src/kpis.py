from __future__ import annotations
import pandas as pd
import numpy as np


def compute_oee(production: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    if production.empty or events.empty:
        return pd.DataFrame(columns=[
            "date","machine_id","availability","performance","quality","oee",
            "planned_time_s","run_time_s","total_count","good_count","scrap_count"
        ])

    prod = production.copy()
    prod["date"] = pd.to_datetime(prod["ts"]).dt.date
    prod["total_count"] = prod["good_count"] + prod["scrap_count"]

    prod_agg = prod.groupby(["date", "machine_id"], as_index=False).agg(
        good_count=("good_count", "sum"),
        scrap_count=("scrap_count", "sum"),
        total_count=("total_count", "sum"),
        ideal_cycle_time_s=("ideal_cycle_time_s", "mean"),
        avg_cycle_time_s=("cycle_time_s", "mean"),
    )

    ev = events.copy()
    ev["date"] = pd.to_datetime(ev["ts"]).dt.date

    planned = ev.groupby(["date","machine_id"], as_index=False)["duration_s"].sum().rename(columns={"duration_s":"planned_time_s"})
    run = ev[ev["state"]=="RUN"].groupby(["date","machine_id"], as_index=False)["duration_s"].sum().rename(columns={"duration_s":"run_time_s"})

    out = prod_agg.merge(planned, on=["date","machine_id"], how="left").merge(run, on=["date","machine_id"], how="left")
    out["planned_time_s"] = out["planned_time_s"].fillna(0.0)
    out["run_time_s"] = out["run_time_s"].fillna(0.0)

    out["availability"] = np.where(out["planned_time_s"]>0, out["run_time_s"]/out["planned_time_s"], 0.0)
    out["performance"] = np.where(out["run_time_s"]>0, (out["ideal_cycle_time_s"]*out["total_count"]) / out["run_time_s"], 0.0)
    out["quality"] = np.where(out["total_count"]>0, out["good_count"]/out["total_count"], 0.0)
    out["oee"] = out["availability"] * out["performance"] * out["quality"]

    for c in ["availability","performance","quality","oee"]:
        out[c] = out[c].clip(lower=0.0, upper=1.2)

    return out


def downtime_pareto(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=["reason_code","downtime_s"])
    ev = events.copy()
    ev = ev[ev["state"]=="DOWN"]
    agg = ev.groupby("reason_code", as_index=False)["duration_s"].sum().rename(columns={"duration_s":"downtime_s"})
    agg = agg.sort_values("downtime_s", ascending=False)
    total = agg["downtime_s"].sum()
    agg["pct"] = (agg["downtime_s"] / total) if total>0 else 0.0
    agg["cum_pct"] = agg["pct"].cumsum()
    return agg
