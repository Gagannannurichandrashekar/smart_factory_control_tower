from __future__ import annotations
import pandas as pd
import numpy as np

SKLEARN_AVAILABLE = False
train_test_split = None
roc_auc_score = None
average_precision_score = None
f1_score = None
Pipeline = None
SimpleImputer = None
StandardScaler = None
LogisticRegression = None
RandomForestClassifier = None

try:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, average_precision_score, f1_score
    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

JOBLIB_AVAILABLE = False
joblib = None

try:
    import joblib
    JOBLIB_AVAILABLE = True
except Exception:
    JOBLIB_AVAILABLE = False

from pathlib import Path

MODEL_PATH_DEFAULT = Path("data/maintenance_model.joblib")

FEATURE_COLS = [
    "total_count","good_count","scrap_count","avg_cycle_time_s","std_cycle_time_s","scrap_rate",
    "kwh","avg_kw","max_kw","kwh_per_good",
    "downtime_ratio","down_events","RUN","DOWN","IDLE",
    "avg_cycle_time_s_r3","avg_cycle_time_s_r7",
    "downtime_ratio_r3","downtime_ratio_r7",
    "down_events_r3","down_events_r7",
    "kwh_per_good_r3","kwh_per_good_r7",
    "max_kw_r3","max_kw_r7",
]

def train_model(df: pd.DataFrame, label_col: str = "label", model_type: str = "logreg"):
    if not SKLEARN_AVAILABLE:
        raise ImportError("scikit-learn is not installed. Install with: pip install scikit-learn")
    X = df[FEATURE_COLS].copy()
    y = df[label_col].astype(int).values

    stratify_param = y if len(set(y)) > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=stratify_param
    )

    if model_type == "rf":
        clf = RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight="balanced_subsample",
            max_depth=8,
            min_samples_leaf=3,
        )
        pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("clf", clf)
        ])
    else:
        clf = LogisticRegression(max_iter=2000, class_weight="balanced")
        pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", clf)
        ])

    pipe.fit(X_train, y_train)

    has_multiple_classes = len(set(y_test)) > 1
    if has_multiple_classes:
        proba = pipe.predict_proba(X_test)[:, 1]
        preds = (proba >= 0.5).astype(int)
    else:
        proba = np.zeros_like(y_test, dtype=float)
        preds = np.zeros_like(y_test, dtype=int)

    metrics = {}
    if has_multiple_classes:
        metrics["roc_auc"] = float(roc_auc_score(y_test, proba))
        metrics["pr_auc"] = float(average_precision_score(y_test, proba))
        metrics["f1"] = float(f1_score(y_test, preds))
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None
        metrics["f1"] = None

    return pipe, metrics


def save_model(model, path: str | Path = MODEL_PATH_DEFAULT) -> None:
    if not JOBLIB_AVAILABLE:
        raise ImportError("joblib is not installed. Install with: pip install joblib")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: str | Path = MODEL_PATH_DEFAULT):
    if not JOBLIB_AVAILABLE:
        raise ImportError("joblib is not installed. Install with: pip install joblib")
    path = Path(path)
    return joblib.load(path)
