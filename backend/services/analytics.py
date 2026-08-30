import os
import time
import matplotlib
matplotlib.use('Agg') # non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, date
from sqlalchemy.orm import Session
from models.schema import KPIRecordDB, ProjectDB
from services.detection import detect_anomaly
from services.evidence import EvidenceItem, Hypothesis, assign_evidence_label, assign_confidence_tiers
from services.narrative import generate_cfo_narrative, generate_regional_manager_narrative

_chart_cache = {}

def _safe_filename(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(name))
    return cleaned[:80] or "kpi"


def _downsample(df: pd.DataFrame, max_points: int = 120) -> pd.DataFrame:
    if len(df) <= max_points:
        return df
    step = max(1, len(df) // max_points)
    return df.iloc[::step]


def _anomaly_dates_vectorized(dates: list, values: list, z_alert: float = 2.0) -> list:
    if len(values) < 8:
        return []
    s = pd.Series(values, dtype=float)
    mean = s.shift(1).expanding(min_periods=5).mean()
    std = s.shift(1).expanding(min_periods=5).std().replace(0, np.nan)
    z = (s - mean) / std
    hits = []
    for i, score in enumerate(z):
        if pd.notna(score) and abs(float(score)) > z_alert:
            hits.append(dates[i])
    return hits[:40]


def generate_seaborn_chart(project_id: int, kpi_name: str, df: pd.DataFrame, anomaly_dates: list) -> str:
    """Generates a Seaborn chart and saves it in static/charts/ directory."""
    sns.set_theme(style="whitegrid", rc={"axes.facecolor": "#fbfaf6", "figure.facecolor": "#fbfaf6"})
    plt.figure(figsize=(9, 4.2))

    df = _downsample(df.copy().sort_values(by="date"))
    df["date_str"] = df["date"].apply(lambda d: d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d))

    sns.lineplot(
        data=df,
        x="date_str",
        y="value",
        marker="o",
        linewidth=2,
        color="#2c5f4a",
        label=str(kpi_name),
    )

    anomaly_str_dates = [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d) for d in anomaly_dates]
    anomalies = df[df["date_str"].isin(anomaly_str_dates)]
    if not anomalies.empty:
        sns.scatterplot(
            data=anomalies,
            x="date_str",
            y="value",
            color="#b42318",
            s=90,
            zorder=5,
            label="Unusual point",
        )

    plt.title(f"{kpi_name}", fontsize=13, pad=12)
    plt.xlabel("")
    plt.ylabel("Value", fontsize=10)
    if len(df) > 10:
        step = max(1, len(df) // 8)
        plt.xticks(ticks=np.arange(0, len(df), step), labels=df["date_str"].iloc[::step], rotation=30, ha="right")
    else:
        plt.xticks(rotation=30, ha="right")

    plt.tight_layout()
    static_dir = os.path.join("static", "charts")
    os.makedirs(static_dir, exist_ok=True)
    filename = f"project_{project_id}_{_safe_filename(kpi_name)}.png"
    filepath = os.path.join(static_dir, filename)
    plt.savefig(filepath, dpi=110)
    plt.close()
    return f"/static/charts/{filename}"

def build_project_dashboard(project_id: int, role: str, persona: str, db: Session):
    """Dynamically builds metrics, anomalies, charts, and evidence ledger for a project (narrative is fetched separately)."""
    t_start = time.perf_counter()
    
    # 1. Fetch records
    t_db_start = time.perf_counter()
    records = db.query(KPIRecordDB).filter(KPIRecordDB.project_id == project_id).all()
    t_db_ms = (time.perf_counter() - t_db_start) * 1000
    
    if not records:
        print(f"[PERF] Database lookup: {t_db_ms:.1f} ms")
        print(f"[PERF] Total dashboard: {(time.perf_counter() - t_start) * 1000:.1f} ms")
        return {
            "empty": True,
            "message": "No data has been uploaded to this project yet. Please upload a CSV or screenshot to begin.",
            "metrics": {},
            "charts": {},
            "hypotheses": [],
            "narrative": "No data available.",
            "analysis": None,
        }
        
    # Group by KPI name
    t_proc_start = time.perf_counter()
    kpis = {}
    for r in records:
        kpis.setdefault(r.kpi_name, []).append(r)

    chart_names = {
        name for name, _ in sorted(kpis.items(), key=lambda kv: len(kv[1]), reverse=True)[:8]
    }
        
    metrics_summary = {}
    charts = {}
    hypotheses = []
    
    t_detect_ms = 0.0
    t_chart_ms = 0.0
    
    for kpi_name, kpi_records in kpis.items():
        # Sort by date
        kpi_records = sorted(kpi_records, key=lambda x: x.date)
        values = [r.value for r in kpi_records]
        dates = [r.date for r in kpi_records]
        
        # Latest record details
        latest_record = kpi_records[-1]
        current_value = latest_record.value
        
        # Calculate historical baseline
        history = values[:-1]
        baseline_value = np.mean(history) if history else current_value
        deviation_value = current_value - baseline_value
        
        # Detect anomaly
        t_det_start = time.perf_counter()
        detection = detect_anomaly(
            kpi_name=kpi_name,
            grain=latest_record.grain or "daily",
            history=history,
            current_value=current_value,
            deviation_value=deviation_value,
            baseline_value=baseline_value
        )
        
        anomaly_dates = _anomaly_dates_vectorized(dates, values)
        t_detect_ms += (time.perf_counter() - t_det_start) * 1000

        # Generate / Retrieve Seaborn chart
        t_chart_start = time.perf_counter()

        cache_key = (project_id, kpi_name, len(kpi_records), latest_record.date, latest_record.value)
        static_filename = f"project_{project_id}_{_safe_filename(kpi_name)}.png"
        static_filepath = os.path.join("static", "charts", static_filename)
        
        if len(kpi_records) >= 2 and kpi_name in chart_names:
            if cache_key in _chart_cache and os.path.exists(static_filepath):
                chart_url = _chart_cache[cache_key]
            else:
                df_kpi = pd.DataFrame({"date": dates, "value": values})
                chart_url = generate_seaborn_chart(project_id, kpi_name, df_kpi, anomaly_dates)
                _chart_cache[cache_key] = chart_url
            charts[kpi_name] = chart_url
        t_chart_ms += (time.perf_counter() - t_chart_start) * 1000
        
        metrics_summary[kpi_name] = {
            "current_value": float(current_value),
            "baseline_value": float(baseline_value),
            "deviation": float(deviation_value),
            "is_anomaly": bool(detection["is_anomaly"]),
            "method_used": detection["method"],
            "anomaly_score": float(detection["anomaly_score"]),
            "z_score": (
                float(detection["z_score"])
                if detection["z_score"] is not None
                else None
            ),
            "grain": latest_record.grain
        }
        
        # Construct Evidence ledger items if there is anomaly or significant deviation
        if detection["is_anomaly"] or abs(deviation_value) > (baseline_value * 0.05):
            evidence_items = [
                EvidenceItem(
                    source=latest_record.source_file or "unknown",
                    method=detection["method"],
                    contribution_pct=100.0,
                    confidence="high" if detection["anomaly_score"] > 0.7 else "medium",
                    freshness_timestamp=datetime.now(),
                    lineage_path=f"upload -> {kpi_name} -> {latest_record.dimensions}",
                    supports_hypothesis=f"Significant change in {kpi_name}",
                    evidence_for=[f"Latest value is {current_value} vs baseline {baseline_value:.2f}"],
                    evidence_against=[],
                    is_temporal_precedent=True
                )
            ]
            
            hypo = Hypothesis(
                description=f"Change in {kpi_name} driven by dimensions: {latest_record.dimensions}",
                evidence_items=evidence_items,
                data_missing=[],
                next_investigation_step="Investigate segment factors and verify driver attributes.",
                z_score_associated=(
                    float(detection["z_score"])
                    if detection["z_score"] is not None
                    else None
                )
            )
            hypotheses.append(hypo)
            
    t_proc_ms = (time.perf_counter() - t_proc_start) * 1000
    
    # Assign confidence tiers
    t_tier_start = time.perf_counter()
    assign_confidence_tiers(hypotheses)
    for h in hypotheses:
        h.label = assign_evidence_label(h)
    t_tier_ms = (time.perf_counter() - t_tier_start) * 1000
        
    t_total_ms = (time.perf_counter() - t_start) * 1000
    
    print(f"[PERF] Database lookup: {t_db_ms:.1f} ms")
    print(f"[PERF] Dataset processing: {t_proc_ms - t_detect_ms - t_chart_ms:.1f} ms")
    print(f"[PERF] Anomaly detection: {t_detect_ms:.1f} ms")
    print(f"[PERF] Chart generation: {t_chart_ms:.1f} ms")
    print(f"[PERF] Confidence tiering: {t_tier_ms:.1f} ms")
    print(f"[PERF] Total dashboard: {t_total_ms:.1f} ms")
    
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    analysis = project.analysis if project else None

    return {
        "empty": False,
        "metrics": metrics_summary,
        "charts": charts,
        "hypotheses": [h.model_dump() for h in hypotheses],
        "narrative": None,
        "analysis": analysis,
        "advice_focus": project.advice_focus if project else None,
    }

def get_project_hypotheses(project_id: int, db: Session) -> list[Hypothesis]:
    """Builds and returns the hypotheses list for narrative generation without side-effects like chart generation."""
    records = db.query(KPIRecordDB).filter(KPIRecordDB.project_id == project_id).all()
    if not records:
        return []
        
    kpis = {}
    for r in records:
        kpis.setdefault(r.kpi_name, []).append(r)
        
    hypotheses = []
    for kpi_name, kpi_records in kpis.items():
        kpi_records = sorted(kpi_records, key=lambda x: x.date)
        values = [r.value for r in kpi_records]
        latest_record = kpi_records[-1]
        current_value = latest_record.value
        history = values[:-1]
        baseline_value = np.mean(history) if history else current_value
        deviation_value = current_value - baseline_value
        
        detection = detect_anomaly(
            kpi_name=kpi_name,
            grain=latest_record.grain or "daily",
            history=history,
            current_value=current_value,
            deviation_value=deviation_value,
            baseline_value=baseline_value
        )
        
        if detection["is_anomaly"] or abs(deviation_value) > (baseline_value * 0.05):
            evidence_items = [
                EvidenceItem(
                    source=latest_record.source_file or "unknown",
                    method=detection["method"],
                    contribution_pct=100.0,
                    confidence="high" if detection["anomaly_score"] > 0.7 else "medium",
                    freshness_timestamp=datetime.now(),
                    lineage_path=f"upload -> {kpi_name} -> {latest_record.dimensions}",
                    supports_hypothesis=f"Significant change in {kpi_name}",
                    evidence_for=[f"Latest value is {current_value} vs baseline {baseline_value:.2f}"],
                    evidence_against=[],
                    is_temporal_precedent=True
                )
            ]
            
            hypo = Hypothesis(
                description=f"Change in {kpi_name} driven by dimensions: {latest_record.dimensions}",
                evidence_items=evidence_items,
                data_missing=[],
                next_investigation_step="Investigate segment factors and verify driver attributes.",
                z_score_associated=(
                    float(detection["z_score"])
                    if detection["z_score"] is not None
                    else None
                )
            )
            hypotheses.append(hypo)
            
    assign_confidence_tiers(hypotheses)
    for h in hypotheses:
        h.label = assign_evidence_label(h)
        
    return hypotheses

