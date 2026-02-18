"""
Industry 4.0 Modern Manufacturing Features

Implements cutting-edge manufacturing trends including:
- Digital Twin concepts
- Real-time analytics
- Predictive insights
- Sustainability metrics
- Supply chain visibility
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, List


def calculate_carbon_footprint(energy_kwh: float, carbon_factor: float = 0.5) -> float:
    """
    Calculate CO2 emissions from energy consumption.
    
    Args:
        energy_kwh: Energy consumption in kWh
        carbon_factor: kg CO2 per kWh (default: 0.5 for grid average)
        
    Returns:
        CO2 emissions in kg
    """
    return energy_kwh * carbon_factor


def calculate_sustainability_score(
    oee: float,
    energy_efficiency: float,
    scrap_rate: float,
    max_score: float = 100.0
) -> float:
    """
    Calculate sustainability score combining multiple factors.
    
    Args:
        oee: Overall Equipment Effectiveness (0-1)
        energy_efficiency: Energy efficiency metric (normalized 0-1)
        scrap_rate: Scrap rate (0-1, lower is better)
        max_score: Maximum score
        
    Returns:
        Sustainability score (0-100)
    """
    # Weighted combination
    oee_weight = 0.4
    energy_weight = 0.3
    quality_weight = 0.3
    
    quality_factor = 1.0 - scrap_rate  # Convert scrap rate to quality factor
    
    score = (
        oee * oee_weight +
        energy_efficiency * energy_weight +
        quality_factor * quality_weight
    ) * max_score
    
    return min(max_score, max(0.0, score))


def calculate_digital_twin_health(
    oee: float,
    downtime_ratio: float,
    scrap_rate: float,
    energy_variance: float
) -> Dict[str, float]:
    """
    Calculate digital twin health indicators.
    
    Args:
        oee: Overall Equipment Effectiveness
        downtime_ratio: Ratio of downtime to total time
        scrap_rate: Scrap rate
        energy_variance: Coefficient of variation in energy consumption
        
    Returns:
        Dictionary with health indicators
    """
    # Overall health score (0-100)
    health_score = (
        oee * 40 +
        (1 - downtime_ratio) * 30 +
        (1 - scrap_rate) * 20 +
        max(0, 1 - energy_variance) * 10
    )
    
    # Risk level
    if health_score >= 80:
        risk_level = "Low"
    elif health_score >= 60:
        risk_level = "Medium"
    else:
        risk_level = "High"
    
    return {
        'health_score': health_score,
        'risk_level': risk_level,
        'oee_contribution': oee * 40,
        'availability_contribution': (1 - downtime_ratio) * 30,
        'quality_contribution': (1 - scrap_rate) * 20,
        'stability_contribution': max(0, 1 - energy_variance) * 10
    }


def calculate_lean_metrics(
    production_df: pd.DataFrame,
    events_df: pd.DataFrame
) -> Dict[str, float]:
    """
    Calculate Lean Manufacturing metrics.
    
    Args:
        production_df: Production data
        events_df: Events data
        
    Returns:
        Dictionary with Lean metrics
    """
    # Calculate takt time (customer demand rate)
    total_time = events_df['duration_s'].sum() if 'duration_s' in events_df.columns else 0
    total_units = production_df['good_count'].sum() if 'good_count' in production_df.columns else 1
    
    takt_time = total_time / total_units if total_units > 0 else 0
    
    # Calculate cycle time efficiency
    avg_cycle_time = production_df['cycle_time_s'].mean() if 'cycle_time_s' in production_df.columns else 0
    cycle_efficiency = (takt_time / avg_cycle_time) if avg_cycle_time > 0 else 0
    
    # Calculate value-added time ratio
    run_time = events_df[events_df['state'] == 'RUN']['duration_s'].sum() if 'state' in events_df.columns else 0
    total_time = events_df['duration_s'].sum() if 'duration_s' in events_df.columns else 1
    value_added_ratio = run_time / total_time if total_time > 0 else 0
    
    return {
        'takt_time': takt_time,
        'cycle_efficiency': cycle_efficiency,
        'value_added_ratio': value_added_ratio,
        'waste_ratio': 1 - value_added_ratio
    }


def calculate_smart_factory_index(
    oee: float,
    predictive_maintenance_score: float,
    energy_efficiency: float,
    quality_rate: float,
    digitalization_level: float = 0.8
) -> float:
    """
    Calculate Smart Factory Index (0-100).
    
    Combines multiple Industry 4.0 indicators into a single score.
    
    Args:
        oee: Overall Equipment Effectiveness
        predictive_maintenance_score: PM model accuracy/effectiveness (0-1)
        energy_efficiency: Energy efficiency metric (0-1)
        quality_rate: Quality rate (0-1)
        digitalization_level: Level of digitalization (0-1)
        
    Returns:
        Smart Factory Index (0-100)
    """
    weights = {
        'oee': 0.30,
        'predictive': 0.25,
        'energy': 0.20,
        'quality': 0.15,
        'digitalization': 0.10
    }
    
    index = (
        oee * weights['oee'] +
        predictive_maintenance_score * weights['predictive'] +
        energy_efficiency * weights['energy'] +
        quality_rate * weights['quality'] +
        digitalization_level * weights['digitalization']
    ) * 100
    
    return min(100.0, max(0.0, index))


def detect_anomalies(
    df: pd.DataFrame,
    metric_col: str,
    threshold_std: float = 2.0
) -> pd.DataFrame:
    """
    Detect anomalies using statistical methods (Z-score).
    
    Args:
        df: DataFrame with metric data
        metric_col: Column name to analyze
        threshold_std: Number of standard deviations for threshold
        
    Returns:
        DataFrame with anomaly flags
    """
    result = df.copy()
    
    if metric_col not in result.columns:
        return result
    
    mean = result[metric_col].mean()
    std = result[metric_col].std()
    
    if std > 0:
        result['z_score'] = (result[metric_col] - mean) / std
        result['is_anomaly'] = abs(result['z_score']) > threshold_std
    else:
        result['z_score'] = 0
        result['is_anomaly'] = False
    
    return result

