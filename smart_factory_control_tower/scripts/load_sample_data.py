from __future__ import annotations
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
from src.db import connect, exec_sql

def load_sample_dataset(csv_path: str = "smart_manufacturing_dataset.csv", db_path: str = "data/factory.db"):
    print(f"Loading dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    print(f"Dataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    con = connect(db_path)
    
    con.execute("PRAGMA foreign_keys = OFF;")
    
    SCHEMA = """
DROP TABLE IF EXISTS order_steps;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS energy;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS production;
DROP TABLE IF EXISTS machines;
DROP TABLE IF EXISTS sample_manufacturing_data;

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

CREATE TABLE sample_manufacturing_data (
  agent_id TEXT NOT NULL,
  task_type TEXT NOT NULL,
  execution_time REAL NOT NULL,
  q_value REAL NOT NULL,
  machine_usage REAL NOT NULL,
  energy_consumption REAL NOT NULL,
  production_efficiency REAL NOT NULL,
  security_event TEXT,
  anomaly_detected TEXT NOT NULL,
  fuzzy_pid_adjustment REAL NOT NULL,
  system_efficiency REAL NOT NULL,
  ts TEXT NOT NULL
);
"""
    
    exec_sql(con, SCHEMA)
    con.execute("PRAGMA foreign_keys = ON;")
    
    now = datetime.now()
    start_time = now - timedelta(days=30)
    
    unique_agents = df['Agent_ID'].unique()
    
    machines_data = []
    for i, agent_id in enumerate(unique_agents[:12]):
        line = f"Line{'A' if i < 6 else 'B'}"
        machine_id = f"{line}-M{(i % 6) + 1}"
        agent_data = df[df['Agent_ID'] == agent_id]
        if len(agent_data) > 0:
            ideal_cycle_time = float(agent_data['Execution_Time'].mean())
            rated_power = float(agent_data['Energy_Consumption'].mean() * 0.1)
        else:
            ideal_cycle_time = 20.0
            rated_power = 5.0
        machines_data.append((machine_id, line, ideal_cycle_time, rated_power))
    
    machines_df = pd.DataFrame(machines_data, columns=["machine_id", "line", "ideal_cycle_time_s", "rated_power_kw"])
    machines_df.to_sql("machines", con, if_exists="append", index=False)
    con.commit()
    
    df['ts'] = pd.date_range(start=start_time, periods=len(df), freq='1h')[:len(df)]
    df['ts'] = df['ts'].astype(str)
    
    agent_to_machine = {}
    for i, agent_id in enumerate(unique_agents[:12]):
        line = f"Line{'A' if i < 6 else 'B'}"
        machine_id = f"{line}-M{(i % 6) + 1}"
        agent_to_machine[agent_id] = machine_id
    
    df['machine_id'] = df['Agent_ID'].map(agent_to_machine).fillna('LineA-M1')
    
    sample_df = df[[
        'Agent_ID', 'Task_Type', 'Execution_Time', 'Q_Value', 'Machine_Usage',
        'Energy_Consumption', 'Production_Efficiency', 'Security_Event',
        'Anomaly_Detected', 'Fuzzy_PID_Adjustment', 'System_Efficiency', 'ts'
    ]].copy()
    sample_df.columns = [
        'agent_id', 'task_type', 'execution_time', 'q_value', 'machine_usage',
        'energy_consumption', 'production_efficiency', 'security_event',
        'anomaly_detected', 'fuzzy_pid_adjustment', 'system_efficiency', 'ts'
    ]
    sample_df.to_sql("sample_manufacturing_data", con, if_exists="append", index=False)
    con.commit()
    
    production_data = []
    events_data = []
    energy_data = []
    
    print("Processing production, events, and energy data...")
    for idx, row in df.iterrows():
        machine_id = row['machine_id']
        ts = row['ts']
        execution_time = row['Execution_Time']
        energy_cons = row['Energy_Consumption']
        prod_efficiency = row['Production_Efficiency']
        machine_usage = row['Machine_Usage']
        anomaly = row['Anomaly_Detected']
        
        good_count = int(prod_efficiency * 10)
        scrap_count = max(0, int((100 - prod_efficiency) * 0.1))
        ideal_cycle = float(machines_df[machines_df['machine_id'] == machine_id]['ideal_cycle_time_s'].iloc[0])
        
        production_data.append((
            ts, machine_id, good_count, scrap_count, execution_time, ideal_cycle
        ))
        
        if anomaly == 'Yes':
            events_data.append((ts, machine_id, 'DOWN', execution_time * 2, 'BREAKDOWN'))
        else:
            events_data.append((ts, machine_id, 'RUN', execution_time, 'NORMAL'))
        
        kw = energy_cons * 0.1
        kwh_interval = kw * (execution_time / 3600)
        energy_data.append((ts, machine_id, kwh_interval, kw))
    
    prod_df = pd.DataFrame(production_data, columns=[
        "ts", "machine_id", "good_count", "scrap_count", "cycle_time_s", "ideal_cycle_time_s"
    ])
    print(f"Inserting {len(prod_df)} production records...")
    prod_df.to_sql("production", con, if_exists="append", index=False)
    con.commit()
    
    events_df = pd.DataFrame(events_data, columns=[
        "ts", "machine_id", "state", "duration_s", "reason_code"
    ])
    print(f"Inserting {len(events_df)} event records...")
    events_df.to_sql("events", con, if_exists="append", index=False)
    con.commit()
    
    energy_df = pd.DataFrame(energy_data, columns=[
        "ts", "machine_id", "kwh_interval", "kw"
    ])
    print(f"Inserting {len(energy_df)} energy records...")
    energy_df.to_sql("energy", con, if_exists="append", index=False)
    con.commit()
    
    orders_data = []
    steps_data = []
    
    for i in range(20):
        order_id = f"ORD-{1000 + i}"
        sku = f"SKU-{i % 5 + 1}"
        start_ts = (start_time + timedelta(days=i*1.5)).strftime("%Y-%m-%d %H:%M:%S")
        due_ts = (start_time + timedelta(days=i*1.5 + 3)).strftime("%Y-%m-%d %H:%M:%S")
        priority = i % 3 + 1
        orders_data.append((order_id, sku, 1000 + i*50, start_ts, due_ts, priority))
        
        for step_no in range(1, 4):
            machine_id = f"Line{'A' if step_no % 2 == 1 else 'B'}-M{step_no}"
            planned_start = (start_time + timedelta(days=i*1.5, hours=step_no*4)).strftime("%Y-%m-%d %H:%M:%S")
            planned_end = (start_time + timedelta(days=i*1.5, hours=step_no*4 + 8)).strftime("%Y-%m-%d %H:%M:%S")
            actual_start = planned_start
            actual_end = planned_end if i < 15 else None
            status = "COMPLETED" if i < 15 else "IN_PROGRESS"
            qty = 500 if status == "COMPLETED" else 0
            steps_data.append((
                order_id, step_no, machine_id, status, planned_start, planned_end,
                actual_start, actual_end, qty
            ))
    
    orders_df = pd.DataFrame(orders_data, columns=[
        "order_id", "sku", "planned_qty", "start_ts", "due_ts", "priority"
    ])
    orders_df.to_sql("orders", con, if_exists="append", index=False)
    con.commit()
    
    steps_df = pd.DataFrame(steps_data, columns=[
        "order_id", "step_no", "machine_id", "status",
        "planned_start_ts", "planned_end_ts", "actual_start_ts", "actual_end_ts", "qty_completed"
    ])
    steps_df.to_sql("order_steps", con, if_exists="append", index=False)
    con.commit()
    
    con.close()
    
    print(f"✅ Loaded {len(df)} records from sample dataset")
    print(f"✅ Created {len(machines_df)} machines")
    print(f"✅ Created {len(prod_df)} production records")
    print(f"✅ Created {len(events_df)} event records")
    print(f"✅ Created {len(energy_df)} energy records")
    print(f"✅ Created {len(orders_df)} orders")
    print(f"✅ Database ready!")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=str, default="smart_manufacturing_dataset.csv")
    p.add_argument("--db", type=str, default="data/factory.db")
    args = p.parse_args()
    load_sample_dataset(args.csv, args.db)

