from __future__ import annotations
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


def init_filters():
    if 'filters' not in st.session_state:
        st.session_state.filters = {
            'line': 'All',
            'machine_id': 'All',
            'date_from': (datetime.now() - timedelta(days=30)).date(),
            'date_to': datetime.now().date(),
            'shift': 'All'
        }


def render_global_filters(machines_df: pd.DataFrame) -> dict:
    init_filters()
    
    with st.container():
        st.markdown("---")
        st.markdown("### 🎛️ Global Filters")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            lines = ['All'] + sorted(machines_df['line'].unique().tolist())
            selected_line = st.selectbox(
                "Production Line",
                options=lines,
                index=lines.index(st.session_state.filters['line']) if st.session_state.filters['line'] in lines else 0,
                key='filter_line'
            )
            st.session_state.filters['line'] = selected_line
        
        with col2:
            if selected_line == 'All':
                machine_options = ['All'] + sorted(machines_df['machine_id'].unique().tolist())
            else:
                line_machines = machines_df[machines_df['line'] == selected_line]['machine_id'].unique().tolist()
                machine_options = ['All'] + sorted(line_machines)
            
            selected_machine = st.selectbox(
                "Machine",
                options=machine_options,
                index=machine_options.index(st.session_state.filters['machine_id']) if st.session_state.filters['machine_id'] in machine_options else 0,
                key='filter_machine'
            )
            st.session_state.filters['machine_id'] = selected_machine
        
        with col3:
            date_from = st.date_input(
                "From Date",
                value=st.session_state.filters['date_from'],
                max_value=datetime.now().date(),
                key='filter_date_from'
            )
            st.session_state.filters['date_from'] = date_from
            
            date_to = st.date_input(
                "To Date",
                value=st.session_state.filters['date_to'],
                max_value=datetime.now().date(),
                min_value=date_from,
                key='filter_date_to'
            )
            st.session_state.filters['date_to'] = date_to
        
        with col4:
            shift_options = ['All', 'Day Shift (7-15)', 'Night Shift (15-23)', 'Graveyard (23-7)']
            selected_shift = st.selectbox(
                "Shift",
                options=shift_options,
                index=shift_options.index(st.session_state.filters['shift']) if st.session_state.filters['shift'] in shift_options else 0,
                key='filter_shift'
            )
            st.session_state.filters['shift'] = selected_shift
        
        st.markdown("---")
    
    return st.session_state.filters.copy()


def apply_filters(
    df: pd.DataFrame, 
    filters: dict, 
    date_col: str = 'date', 
    machine_col: str = 'machine_id',
    ts_col: Optional[str] = 'ts',
    machines_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    result = df.copy()
    
    if filters['line'] != 'All' and machines_df is not None and machine_col in result.columns:
        line_machines = machines_df[machines_df['line'] == filters['line']]['machine_id'].unique().tolist()
        result = result[result[machine_col].isin(line_machines)]
    
    if filters['machine_id'] != 'All' and machine_col in result.columns:
        result = result[result[machine_col] == filters['machine_id']]
    
    if date_col in result.columns:
        if pd.api.types.is_datetime64_any_dtype(result[date_col]):
            date_from = pd.Timestamp(filters['date_from'])
            date_to = pd.Timestamp(filters['date_to']) + pd.Timedelta(days=1)
            result = result[
                (result[date_col] >= date_from) &
                (result[date_col] < date_to)
            ]
        else:
            if not isinstance(result[date_col].iloc[0] if len(result) > 0 else None, type(filters['date_from'])):
                result[date_col] = pd.to_datetime(result[date_col]).dt.date
            result = result[
                (result[date_col] >= filters['date_from']) &
                (result[date_col] <= filters['date_to'])
            ]
    
    if filters['shift'] != 'All' and ts_col in result.columns:
        start_hour, end_hour = get_shift_hours(filters['shift'])
        
        if not pd.api.types.is_datetime64_any_dtype(result[ts_col]):
            result[ts_col] = pd.to_datetime(result[ts_col])
        
        result['_filter_hour'] = result[ts_col].dt.hour
        
        if start_hour < end_hour:
            result = result[(result['_filter_hour'] >= start_hour) & (result['_filter_hour'] < end_hour)]
        else:
            result = result[(result['_filter_hour'] >= start_hour) | (result['_filter_hour'] < end_hour)]
        
        result = result.drop(columns=['_filter_hour'], errors='ignore')
    
    return result


def get_shift_hours(shift: str) -> tuple[int, int]:
    shift_map = {
        'Day Shift (7-15)': (7, 15),
        'Night Shift (15-23)': (15, 23),
        'Graveyard (23-7)': (23, 7),
        'All': (0, 24)
    }
    return shift_map.get(shift, (0, 24))

