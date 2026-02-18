from __future__ import annotations
import argparse
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from pathlib import Path
from src.db import connect, exec_sql

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

def simulate(days: int, seed: int):
    rng = np.random.default_rng(seed)
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days)

    # Machines
    machines = []
    for line in ["LineA","LineB"]:
        for i in range(1,4):
            mid = f"{line}-M{i}"
            ideal = float(rng.uniform(18, 45))  # seconds
            rated = float(rng.uniform(4.0, 12.0))  # kW
            machines.append((mid, line, ideal, rated))
    machines_df = pd.DataFrame(machines, columns=["machine_id","line","ideal_cycle_time_s","rated_power_kw"])

    # Simulate hourly blocks of state durations summing to 3600s
    events = []
    production = []
    energy = []

    reason_down = ["SETUP","JAM","MATERIAL","QUALITY_CHECK","BREAKDOWN"]
    # baseline breakdown probability per hour per machine
    base_break_p = 0.015

    ts = start
    while ts < now:
        for m in machines_df.itertuples(index=False):
            # Utilization patterns
            hour = ts.hour
            shift_factor = 1.0 if 7 <= hour <= 18 else 0.55  # day vs night
            # State durations
            run_ratio = float(np.clip(rng.normal(0.78*shift_factor, 0.08), 0.15, 0.92))
            down_ratio = float(np.clip(rng.normal(0.10, 0.05), 0.00, 0.40))
            idle_ratio = float(max(0.0, 1.0 - run_ratio - down_ratio))
            # Normalize to 3600
            total = run_ratio + down_ratio + idle_ratio
            run_s = 3600.0 * run_ratio/total
            down_s = 3600.0 * down_ratio/total
            idle_s = 3600.0 * idle_ratio/total

            # Down reason (BREAKDOWN occasionally, more likely if cycle time is trending up—simulated later)
            # Inject breakdowns with a small chance; if down_s is tiny, still allow breakdown reason sometimes.
            if rng.random() < base_break_p:
                down_reason = "BREAKDOWN"
                # Longer breakdowns
                down_s = float(np.clip(rng.normal(1800, 600), 600, 3600))
                run_s = max(0.0, 3600 - down_s - idle_s)
            else:
                down_reason = rng.choice(reason_down[:-1]) if down_s > 60 else "NONE"

            # Add event rows
            if run_s > 1:
                events.append((ts.isoformat(), m.machine_id, "RUN", run_s, "RUNNING"))
            if down_s > 1:
                events.append((ts.isoformat(), m.machine_id, "DOWN", down_s, down_reason))
            if idle_s > 1:
                events.append((ts.isoformat(), m.machine_id, "IDLE", idle_s, "IDLE"))

            # Production based on run time and cycle time
            # Cycle time degrades slightly when many breakdowns recently (simulate via noise only here)
            cycle_time = float(np.clip(rng.normal(m.ideal_cycle_time_s * rng.uniform(0.95, 1.25), 2.5), m.ideal_cycle_time_s*0.85, m.ideal_cycle_time_s*1.7))
            qty = int(max(0, (run_s / cycle_time) * rng.uniform(0.92, 1.05)))
            scrap = int(max(0, rng.binomial(qty, p=float(np.clip(rng.normal(0.02, 0.015), 0.0, 0.12)))))
            good = max(0, qty - scrap)

            production.append((ts.isoformat(), m.machine_id, good, scrap, cycle_time, m.ideal_cycle_time_s))

            # Energy: kw fluctuates with run/idle; kWh interval ~ avg_kw * 1h
            load = 0.35 + 0.65*(run_s/3600.0)
            kw = float(np.clip(rng.normal(m.rated_power_kw*load, 0.35), 0.2, m.rated_power_kw*1.25))
            kwh = float(max(0.0, kw * 1.0))
            energy.append((ts.isoformat(), m.machine_id, kwh, kw))

        ts += timedelta(hours=1)

    prod_df = pd.DataFrame(production, columns=["ts","machine_id","good_count","scrap_count","cycle_time_s","ideal_cycle_time_s"])
    events_df = pd.DataFrame(events, columns=["ts","machine_id","state","duration_s","reason_code"])
    energy_df = pd.DataFrame(energy, columns=["ts","machine_id","kwh_interval","kw"])

    # Orders + steps (simple: each order routes through 2-3 machines on a line)
    orders = []
    steps = []
    order_count = max(12, days//2)
    skus = ["SKU-IPA-12OZ", "SKU-LAGER-16OZ", "SKU-NA-12OZ", "SKU-SELTZER-12OZ"]
    for j in range(order_count):
        oid = f"ORD-{1000+j}"
        sku = rng.choice(skus)
        qty = int(rng.integers(500, 2500))
        priority = int(rng.integers(1, 4))
        # schedule window
        st = start + timedelta(hours=int(rng.integers(0, days*24-24)))
        due = st + timedelta(hours=int(rng.integers(12, 72)))
        orders.append((oid, sku, qty, st.isoformat(), due.isoformat(), priority))

        line = rng.choice(["LineA","LineB"])
        line_machines = machines_df[machines_df["line"]==line]["machine_id"].tolist()
        route_len = int(rng.integers(2, 4))
        route = rng.choice(line_machines, size=route_len, replace=False).tolist()
        planned = st
        completed_total = 0
        for step_no, mid in enumerate(route, start=1):
            dur_h = int(rng.integers(4, 16))
            planned_start = planned
            planned_end = planned_start + timedelta(hours=dur_h)
            planned = planned_end

            # Actuals: sometimes late
            delay_h = int(max(0, rng.normal(1.5, 3.0))) if rng.random() < 0.35 else 0
            actual_start = planned_start + timedelta(hours=delay_h)
            actual_end = planned_end + timedelta(hours=delay_h)

            # Status: last step maybe in progress
            status = "COMPLETED"
            if actual_end > now - timedelta(hours=4) and rng.random() < 0.35:
                status = "IN_PROGRESS"
                actual_end = None

            step_qty = int(min(qty, qty * rng.uniform(0.45, 1.0)))
            completed_total = step_qty if status=="COMPLETED" else max(completed_total, int(step_qty * rng.uniform(0.2, 0.8)))

            steps.append((
                oid, step_no, mid, status,
                planned_start.isoformat(), planned_end.isoformat(),
                actual_start.isoformat(), actual_end.isoformat() if actual_end else None,
                completed_total
            ))

    orders_df = pd.DataFrame(orders, columns=["order_id","sku","planned_qty","start_ts","due_ts","priority"])
    steps_df = pd.DataFrame(steps, columns=[
        "order_id","step_no","machine_id","status",
        "planned_start_ts","planned_end_ts","actual_start_ts","actual_end_ts","qty_completed"
    ])

    return machines_df, prod_df, events_df, orders_df, steps_df, energy_df

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--db", type=str, default="data/factory.db")
    args = p.parse_args()

    con = connect(args.db)
    exec_sql(con, SCHEMA)

    machines_df, prod_df, events_df, orders_df, steps_df, energy_df = simulate(args.days, args.seed)

    machines_df.to_sql("machines", con, if_exists="append", index=False)
    prod_df.to_sql("production", con, if_exists="append", index=False)
    events_df.to_sql("events", con, if_exists="append", index=False)
    orders_df.to_sql("orders", con, if_exists="append", index=False)
    steps_df.to_sql("order_steps", con, if_exists="append", index=False)
    energy_df.to_sql("energy", con, if_exists="append", index=False)

    con.commit()
    con.close()

    print(f"✅ Generated {args.days} days of data into {args.db}")

if __name__ == "__main__":
    main()
