from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import Optional


def render_kpi_card(
    label: str,
    current_value: float,
    previous_value: Optional[float] = None,
    format_str: str = ".1f",
    delta_label: str = "vs previous",
    help_text: Optional[str] = None
) -> None:
    if previous_value is not None and previous_value != 0:
        delta = ((current_value - previous_value) / previous_value) * 100
        delta_str = f"{delta:+.1f}%"
    else:
        delta = None
        delta_str = None
    
    st.metric(
        label=label,
        value=f"{current_value:{format_str}}",
        delta=delta_str if delta is not None else None,
        help=help_text
    )


def render_kpi_row(
    kpis: list[dict],
    num_columns: int = 4
) -> None:
    cols = st.columns(num_columns)
    
    for idx, kpi in enumerate(kpis):
        with cols[idx % num_columns]:
            render_kpi_card(
                label=kpi.get('label', ''),
                current_value=kpi.get('current', 0),
                previous_value=kpi.get('previous'),
                format_str=kpi.get('format', '.1f'),
                delta_label=kpi.get('delta_label', 'vs previous'),
                help_text=kpi.get('help')
            )


def calculate_deltas(
    current_df: pd.DataFrame,
    previous_df: pd.DataFrame,
    metric_col: str,
    group_by: Optional[list] = None
) -> tuple[float, float]:
    if group_by:
        current_val = current_df.groupby(group_by)[metric_col].mean().mean()
        previous_val = previous_df.groupby(group_by)[metric_col].mean().mean()
    else:
        current_val = current_df[metric_col].mean()
        previous_val = previous_df[metric_col].mean()
    
    return float(current_val), float(previous_val)


def get_period_comparison(
    df: pd.DataFrame,
    date_col: str,
    metric_col: str,
    comparison_type: str = "yesterday"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if date_col not in df.columns:
        return df, pd.DataFrame()
    
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])
    
    latest_date = df[date_col].max()
    
    if comparison_type == "yesterday":
        current_start = latest_date
        previous_end = latest_date - pd.Timedelta(days=1)
        previous_start = previous_end
        current_df = df[df[date_col] == current_start]
        previous_df = df[df[date_col] == previous_start]
    elif comparison_type == "last_7_days":
        current_start = latest_date - pd.Timedelta(days=6)
        previous_end = current_start - pd.Timedelta(days=1)
        previous_start = previous_end - pd.Timedelta(days=6)
        current_df = df[df[date_col] >= current_start]
        previous_df = df[(df[date_col] >= previous_start) & (df[date_col] <= previous_end)]
    else:
        return df, pd.DataFrame()
    
    return current_df, previous_df

