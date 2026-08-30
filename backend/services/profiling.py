"""Deterministic CSV profiling: formulas, correlations, target selection."""
from __future__ import annotations

import re
from itertools import combinations
from typing import Any, Optional

import numpy as np
import pandas as pd


METRIC_HINTS = (
    "sales", "revenue", "profit", "amount", "total", "gmv", "arr", "mrr",
    "conversion", "churn", "orders", "quantity", "volume", "price", "cost",
    "margin", "users", "traffic", "clicks", "leads", "pipeline", "nps",
)

RATE_HINTS = (
    "rate", "pct", "percent", "ratio", "margin", "conversion", "churn", "nps", "avg", "average",
)


def load_dataframe(file_path: str) -> pd.DataFrame:
    last_err = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(file_path, encoding=encoding, low_memory=False)
            break
        except Exception as e:
            last_err = e
            df = None
    if df is None:
        raise ValueError(f"Could not read CSV: {last_err}")

    df.columns = [str(c).strip() for c in df.columns]
    drop_cols = []
    for col in df.columns:
        lowered = col.lower().replace(" ", "")
        if lowered.startswith("unnamed") or lowered in {"column1", "index"}:
            drop_cols.append(col)
            continue
        if df[col].dtype in (np.int64, np.int32, np.float64) and df[col].reset_index(drop=True).equals(
            pd.Series(range(len(df)), dtype=df[col].dtype)
        ):
            drop_cols.append(col)
    if drop_cols:
        df = df.drop(columns=drop_cols)
    return df


def _clean_numeric_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = (
        series.astype(str)
        .str.replace(r"[\s$€£¥,%]", "", regex=True)
        .str.replace(",", "", regex=False)
        .replace({"": np.nan, "nan": np.nan, "none": np.nan, "-": np.nan})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def classify_columns(df: pd.DataFrame) -> dict[str, Any]:
    numeric_map: dict[str, pd.Series] = {}
    date_cols: list[str] = []
    categorical_cols: list[str] = []

    for col in df.columns:
        name = col.lower()
        parsed_dates = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
        date_ratio = parsed_dates.notna().mean()
        looks_like_date = any(k in name for k in ("date", "time", "timestamp", "datetime"))
        if date_ratio > (0.5 if looks_like_date else 0.85):
            date_cols.append(col)
            continue

        numeric = _clean_numeric_series(df[col])
        numeric_ratio = numeric.notna().mean()
        nunique = int(df[col].nunique(dropna=True))
        is_id_like = nunique >= max(50, int(len(df) * 0.9))
        name_is_metric = any(h in name for h in METRIC_HINTS)
        if numeric_ratio > 0.7 and (name_is_metric or not is_id_like):
            numeric_map[col] = numeric
        else:
            categorical_cols.append(col)

    return {
        "numeric_map": numeric_map,
        "date_cols": date_cols,
        "categorical_cols": categorical_cols,
    }


def discover_formulas(numeric_df: pd.DataFrame, max_cols: int = 12) -> list[dict[str, str]]:
    """Find simple identities like A ≈ B×C, A ≈ B+C using a sample of rows."""
    cols = list(numeric_df.columns)[:max_cols]
    if len(cols) < 2:
        return []

    sample = numeric_df[cols].dropna()
    if len(sample) > 2500:
        sample = sample.sample(2500, random_state=7)
    if len(sample) < 20:
        return []

    found: list[dict[str, str]] = []
    seen = set()

    def close(a: pd.Series, b: pd.Series) -> bool:
        denom = np.maximum(np.abs(a.to_numpy(dtype=float)), 1e-6)
        rel = np.abs(a.to_numpy(dtype=float) - b.to_numpy(dtype=float)) / denom
        return bool(np.nanmean(rel) < 0.03)

    for a, b in combinations(cols, 2):
        sa, sb = sample[a], sample[b]
        if close(sa, sb):
            key = tuple(sorted((a, b, "eq")))
            if key not in seen:
                seen.add(key)
                found.append({"result": a, "expression": b, "kind": "identity"})

    if len(cols) >= 3:
        for result, x, y in combinations(cols, 3):
            for r, p, q in ((result, x, y), (x, result, y), (y, result, x)):
                sr, sp, sq = sample[r], sample[p], sample[q]
                candidates = [
                    (sp * sq, f"{p} × {q}", "product"),
                    (sp + sq, f"{p} + {q}", "sum"),
                    (sp - sq, f"{p} - {q}", "difference"),
                ]
                if (np.abs(sq) > 1e-9).mean() > 0.9:
                    candidates.append((sp / sq.replace(0, np.nan), f"{p} / {q}", "ratio"))
                for computed, expr, kind in candidates:
                    if close(sr, computed):
                        key = (r, expr)
                        if key not in seen:
                            seen.add(key)
                            found.append({"result": r, "expression": expr, "kind": kind})
                if len(found) >= 8:
                    return found
    return found[:8]


def _score_column(name: str, advice: str) -> int:
    n = re.sub(r"[^a-z0-9]+", " ", name.lower())
    a = re.sub(r"[^a-z0-9]+", " ", (advice or "").lower())
    score = 0
    tokens = [t for t in a.split() if len(t) > 2]
    for t in tokens:
        if t in n:
            score += 4
    for hint in METRIC_HINTS:
        if hint in n:
            score += 2
        if hint in a and hint in n:
            score += 5
    return score


def choose_target(numeric_cols: list[str], advice_focus: str, formulas: list[dict]) -> str:
    if not numeric_cols:
        raise ValueError("This CSV has no numeric columns to analyze.")

    ranked = sorted(numeric_cols, key=lambda c: _score_column(c, advice_focus), reverse=True)
    if advice_focus and _score_column(ranked[0], advice_focus) > 0:
        return ranked[0]

    product_results = {f["result"] for f in formulas if f.get("kind") == "product"}
    for col in ranked:
        if col in product_results:
            return col

    for col in ranked:
        if any(h in col.lower() for h in METRIC_HINTS):
            return col
    return ranked[0]


def aggregation_fn(column_name: str) -> str:
    n = column_name.lower()
    if any(h in n for h in RATE_HINTS):
        return "mean"
    return "sum"


def pearson_correlations(numeric_df: pd.DataFrame, target: str, top_n: int = 10) -> list[dict[str, Any]]:
    if target not in numeric_df.columns:
        return []
    corr = numeric_df.corr(numeric_only=True)
    if target not in corr.columns:
        return []
    series = corr[target].drop(labels=[target], errors="ignore").dropna()
    series = series.reindex(series.abs().sort_values(ascending=False).index)
    out = []
    for col, val in series.head(top_n).items():
        out.append({
            "field": col,
            "correlation": round(float(val), 4),
            "direction": "positive" if val >= 0 else "negative",
            "strength": _strength(abs(float(val))),
        })
    return out


def categorical_associations(df: pd.DataFrame, target_series: pd.Series, categorical_cols: list[str], top_n: int = 6) -> list[dict[str, Any]]:
    results = []
    y = target_series.dropna()
    if y.empty:
        return []
    for col in categorical_cols:
        if df[col].nunique(dropna=True) < 2 or df[col].nunique(dropna=True) > 40:
            continue
        grouped = pd.DataFrame({"y": target_series, "g": df[col]}).dropna()
        if grouped.empty:
            continue
        overall = grouped["y"].mean()
        if overall == 0:
            continue
        means = grouped.groupby("g")["y"].mean()
        spread = (means.max() - means.min()) / (abs(overall) + 1e-9)
        top = means.sort_values(ascending=False).head(3)
        results.append({
            "field": col,
            "association_score": round(float(spread), 4),
            "top_segments": [{"label": str(i), "mean": round(float(v), 4)} for i, v in top.items()],
        })
    results.sort(key=lambda r: r["association_score"], reverse=True)
    return results[:top_n]


def _strength(abs_corr: float) -> str:
    if abs_corr >= 0.7:
        return "strong"
    if abs_corr >= 0.4:
        return "moderate"
    if abs_corr >= 0.2:
        return "weak"
    return "very weak"


def profile_csv(file_path: str, advice_focus: str) -> dict[str, Any]:
    df = load_dataframe(file_path)
    if df.empty:
        raise ValueError("CSV is empty.")

    classified = classify_columns(df)
    numeric_map: dict[str, pd.Series] = classified["numeric_map"]
    if not numeric_map:
        raise ValueError("Could not find numeric fields in this CSV to analyze.")

    numeric_df = pd.DataFrame(numeric_map)
    formulas = discover_formulas(numeric_df)
    target = choose_target(list(numeric_df.columns), advice_focus, formulas)
    correlations = pearson_correlations(numeric_df, target)
    cat_assoc = categorical_associations(df, numeric_df[target], classified["categorical_cols"])
    date_col: Optional[str] = classified["date_cols"][0] if classified["date_cols"] else None

    profile = {
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "target": target,
        "date_column": date_col,
        "numeric_columns": list(numeric_df.columns),
        "categorical_columns": classified["categorical_cols"],
        "formulas": formulas,
        "correlations": correlations,
        "categorical_drivers": cat_assoc,
        "aggregation": aggregation_fn(target),
        "advice_focus": advice_focus or target,
    }
    return {"df": df, "numeric_df": numeric_df, "profile": profile}


def build_time_series(df: pd.DataFrame, numeric_df: pd.DataFrame, profile: dict[str, Any], extra_metrics: list[str]) -> dict[str, pd.DataFrame]:
    """Aggregate potentially huge files into compact KPI series."""
    date_col = profile["date_column"]
    series: dict[str, pd.DataFrame] = {}
    metrics = [profile["target"]] + [m for m in extra_metrics if m != profile["target"]]

    work = df.copy()
    if date_col:
        work["_date"] = pd.to_datetime(work[date_col], errors="coerce", dayfirst=True)
        work = work.dropna(subset=["_date"])
        n_days = work["_date"].dt.date.nunique()
        grain = "daily"
        if n_days > 420:
            work["_bucket"] = work["_date"].dt.to_period("W").dt.start_time.dt.date
            grain = "weekly"
        elif n_days > 60:
            work["_bucket"] = work["_date"].dt.date
            grain = "daily"
        else:
            work["_bucket"] = work["_date"].dt.date
            grain = "daily" if n_days > 14 else "snapshot"
    else:
        work["_bucket"] = pd.Timestamp.today().date()
        grain = "snapshot"

    for metric in metrics:
        if metric not in numeric_df.columns:
            continue
        work[metric] = numeric_df[metric]
        how = aggregation_fn(metric)
        grouped = work.dropna(subset=[metric]).groupby("_bucket")[metric]
        agg = grouped.mean() if how == "mean" else grouped.sum()
        out = agg.reset_index()
        out.columns = ["date", "value"]
        out["grain"] = grain
        if len(out) > 400:
            out = out.iloc[:: max(1, len(out) // 400)]
        series[metric] = out
    return series
