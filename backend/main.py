from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil

from data.db import Base, engine, get_db
from services.synthetic import seed_synthetic_data
from services.ingestion import ingest_csv, ingest_screenshot

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BusinessIntelligence.ai Phase 1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/data/synthetic")
def create_synthetic_data(db: Session = Depends(get_db)):
    """Seed the database with synthetic data."""
    seed_synthetic_data(db)
    return {"message": "Synthetic data generated successfully."}

@app.post("/upload/csv")
def upload_csv(
    kpi_name: str = Form(...),
    grain: str = Form(...),
    date_col: str = Form(...),
    value_col: str = Form(...),
    dimension_cols: str = Form(...), # Comma separated
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and ingest a CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    file_location = f"./temp_{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    dim_cols = [c.strip() for c in dimension_cols.split(",") if c.strip()]
    
    try:
        count = ingest_csv(file_location, kpi_name, grain, date_col, value_col, dim_cols, db)
    except Exception as e:
        os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))
        
    os.remove(file_location)
    return {"message": f"Successfully ingested {count} records."}

@app.post("/upload/screenshot")
def upload_screenshot(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and ingest a dashboard screenshot."""
    if not (file.filename.endswith('.png') or file.filename.endswith('.jpg') or file.filename.endswith('.jpeg')):
        raise HTTPException(status_code=400, detail="Only PNG/JPG files are allowed.")
        
    file_location = f"./temp_{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    try:
        count = ingest_screenshot(file_location, db)
    except Exception as e:
        os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))
        
    os.remove(file_location)
    return {"message": f"Successfully ingested {count} records from screenshot."}

@app.get("/health")
def health_check():
    return {"status": "ok"}

from fastapi import Header
from services.access import filter_records_by_role
from models.schema import KPIRecordDB

@app.get("/data/revenue")
def get_revenue_data(role: str = Header(default="global_cfo", alias="X-Role"), db: Session = Depends(get_db)):
    """Fetch revenue data filtered by role."""
    records = db.query(KPIRecordDB).filter(KPIRecordDB.kpi_name == "revenue").all()
    filtered_records = filter_records_by_role(records, role)
    
    return {
        "count": len(filtered_records),
        "role_applied": role,
        "data": [
            {
                "date": r.date,
                "value": r.value,
                "dimensions": r.dimensions
        ]
    }

from models.schema import TelemetryLogDB
from sqlalchemy.sql import func

@app.get("/telemetry/summary")
def get_telemetry_summary(db: Session = Depends(get_db)):
    """Return total tokens, cost, and average latency."""
    result = db.query(
        func.sum(TelemetryLogDB.tokens_in).label("total_tokens_in"),
        func.sum(TelemetryLogDB.tokens_out).label("total_tokens_out"),
        func.sum(TelemetryLogDB.estimated_cost_usd).label("total_cost"),
        func.avg(TelemetryLogDB.latency_ms).label("avg_latency"),
        func.count(TelemetryLogDB.id).label("total_calls")
    ).first()
    
    return {
        "total_tokens_in": result.total_tokens_in or 0,
        "total_tokens_out": result.total_tokens_out or 0,
        "total_cost_usd": round(result.total_cost or 0.0, 6),
        "average_latency_ms": round(result.avg_latency or 0.0, 2),
        "total_llm_calls": result.total_calls or 0
    }

from services.metadata import get_function_tags

@app.get("/metadata/tags")
def get_tags():
    return {"tags": get_function_tags()}

from datetime import datetime
from services.evidence import EvidenceItem, Hypothesis, assign_evidence_label, assign_confidence_tiers
from services.narrative import generate_cfo_narrative, generate_regional_manager_narrative

@app.get("/scenarios/{scenario_name}")
def get_scenario(scenario_name: str, role: str = "regional_manager_apac", persona: str = "regional_manager"):
    # Mock data directly derived from Phase 3/4 tests
    if scenario_name == "multi_factor":
        ev1 = EvidenceItem(
            source="synthetic_erp.csv", method="z-score", contribution_pct=60.0,
            confidence="high", freshness_timestamp=datetime.now(),
            lineage_path="synthetic_erp.csv -> revenue -> APAC -> price",
            supports_hypothesis="Price drop drove revenue down",
            evidence_for=["Price dropped by 20% in APAC WidgetB"],
            evidence_against=[], is_temporal_precedent=True
        )
        ev2 = EvidenceItem(
            source="marketing_db", method="SQL aggregation", contribution_pct=40.0,
            confidence="high", freshness_timestamp=datetime.now(), lineage_path="marketing_db -> volume",
            supports_hypothesis="Price drop drove revenue down",
            evidence_for=["Volume dropped concurrently"], evidence_against=[], is_temporal_precedent=False
        )
        hypo = Hypothesis(
            description="Price and volume drop in APAC WidgetB caused the revenue drop.",
            evidence_items=[ev1, ev2], data_missing=[], next_investigation_step="Check competitor pricing.",
            z_score_associated=5.6
        )
        hypos = [hypo]
        
    elif scenario_name == "ambiguous":
        ev_a = EvidenceItem(
            source="system_a", method="rule-based threshold", contribution_pct=50.0,
            confidence="medium", freshness_timestamp=datetime.now(), lineage_path="sys_a",
            supports_hypothesis="A caused it", evidence_for=[], evidence_against=[], is_temporal_precedent=False
        )
        hypo_a = Hypothesis(
            description="Hypothesis A: Supply chain delay", evidence_items=[ev_a],
            data_missing=[], next_investigation_step="Investigate Supplier X", z_score_associated=2.1
        )
        ev_b = EvidenceItem(
            source="system_b", method="rule-based threshold", contribution_pct=48.0,
            confidence="medium", freshness_timestamp=datetime.now(), lineage_path="sys_b",
            supports_hypothesis="B caused it", evidence_for=[], evidence_against=[], is_temporal_precedent=False
        )
        hypo_b = Hypothesis(
            description="Hypothesis B: Marketing failure", evidence_items=[ev_b],
            data_missing=[], next_investigation_step="Investigate Campaign Y", z_score_associated=2.0
        )
        hypos = [hypo_a, hypo_b]
        
    else: # sparse_history
        ev1 = EvidenceItem(
            source="synthetic_churn.csv", method="peer_group_comparison", contribution_pct=100.0,
            confidence="medium", freshness_timestamp=datetime.now(), lineage_path="churn -> NewApp",
            supports_hypothesis="New product adoption lagging", evidence_for=["Churn is 10% higher than LegacyApp"],
            evidence_against=[], is_temporal_precedent=False
        )
        hypo = Hypothesis(
            description="NewApp churn is elevated compared to LegacyApp baseline.",
            evidence_items=[ev1], data_missing=["Insufficient historical data (3 weeks)"],
            next_investigation_step="Conduct user interviews.", z_score_associated=None
        )
        hypos = [hypo]
        
    for h in hypos: h.label = assign_evidence_label(h)
    assign_confidence_tiers(hypos)
    
    narrative = None
    if persona == "cfo":
        narrative = generate_cfo_narrative(hypos, business_impact_value=25000.0)
    else:
        narrative = generate_regional_manager_narrative(hypos)
        
    return {
        "hypotheses": [h.model_dump() for h in hypos],
        "narrative": narrative
    }
