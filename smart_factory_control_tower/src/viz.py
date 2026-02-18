from __future__ import annotations
import pandas as pd

MATPLOTLIB_AVAILABLE = False
plt = None

try:
    import matplotlib
    matplotlib.use('Agg', force=True)
    import matplotlib.pyplot as plt
    plt.ioff()
    MATPLOTLIB_AVAILABLE = True
except Exception:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.ioff()
        MATPLOTLIB_AVAILABLE = True
    except Exception:
        MATPLOTLIB_AVAILABLE = False
        plt = None


def line_chart(df: pd.DataFrame, x: str, y: str, title: str) -> plt.Figure:
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib is not installed. Install with: pip install matplotlib")
    
    from matplotlib.dates import DateFormatter, DayLocator
    
    plt.clf()
    fig, ax = plt.subplots(figsize=(12, 6))
    
    if df.empty:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
        plt.tight_layout()
        return fig
    
    if x in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df[x]):
            df = df.copy()
            df[x] = pd.to_datetime(df[x])
    
    ax.plot(df[x], df[y], linewidth=2, marker='o', markersize=3)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel(x, fontsize=12)
    ax.set_ylabel(y, fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    if pd.api.types.is_datetime64_any_dtype(df[x]):
        date_range = (df[x].max() - df[x].min()).days
        if date_range <= 7:
            ax.xaxis.set_major_locator(DayLocator(interval=1))
            ax.xaxis.set_major_formatter(DateFormatter('%m/%d'))
        elif date_range <= 30:
            ax.xaxis.set_major_locator(DayLocator(interval=2))
            ax.xaxis.set_major_formatter(DateFormatter('%m/%d'))
        else:
            ax.xaxis.set_major_locator(DayLocator(interval=max(1, date_range // 10)))
            ax.xaxis.set_major_formatter(DateFormatter('%m/%d'))
        
        fig.autofmt_xdate(rotation=45, ha='right')
    
    plt.tight_layout()
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str, rotate_xticks: bool = True) -> plt.Figure:
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib is not installed. Install with: pip install matplotlib")
    
    plt.clf()
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if df.empty:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
        ax.set_title(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        return fig
    
    ax.bar(df[x].astype(str), df[y], color='steelblue', alpha=0.7)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel(x, fontsize=12)
    ax.set_ylabel(y, fontsize=12)
    ax.grid(True, alpha=0.3, axis='y')
    if rotate_xticks:
        for tick in ax.get_xticklabels():
            tick.set_rotation(45)
            tick.set_ha("right")
    plt.tight_layout()
    return fig
