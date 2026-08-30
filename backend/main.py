from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil

from data.db import Base, engine, get_db, ensure_schema
from services.synthetic import seed_synthetic_data
from services.ingestion import ingest_csv, ingest_screenshot
from models.schema import ProjectDB, ProjectOut
from services.analytics import build_project_dashboard

Base.metadata.create_all(bind=engine)
ensure_schema()

# Ensure static/charts directory exists
os.makedirs(os.path.join("static", "charts"), exist_ok=True)

app = FastAPI(title="BusinessIntelligence.ai Phase 1")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"], # In production, restrict this
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
    file: UploadFile = File(...),
    project_id: Optional[int] = Form(None),
    advice_focus: str = Form(""),
    kpi_name: Optional[str] = Form(None),
    grain: Optional[str] = Form(None),
    date_col: Optional[str] = Form(None),
    value_col: Optional[str] = Form(None),
    dimension_cols: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload a CSV. Column mapping is optional; analysis is driven by advice_focus."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    file_location = f"./temp_{os.path.basename(file.filename)}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    dim_cols = [c.strip() for c in (dimension_cols or "").split(",") if c.strip()]

    try:
        result = ingest_csv(
            file_location,
            db,
            project_id=project_id,
            advice_focus=advice_focus,
            kpi_name=kpi_name,
            grain=grain,
            date_col=date_col,
            value_col=value_col,
            dimension_cols=dim_cols,
        )
    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))

    os.remove(file_location)
    return {
        "message": f"Ingested {result['count']} aggregated records. Analyzing {result['analysis'].get('target')} against related fields.",
        "analysis": result["analysis"],
    }


@app.post("/upload/screenshot")
def upload_screenshot(
    file: UploadFile = File(...),
    project_id: Optional[int] = Form(None),
    advice_focus: str = Form(""),
    db: Session = Depends(get_db)
):
    """Upload and ingest a dashboard screenshot of any layout."""
    name = (file.filename or "").lower()
    if not name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        raise HTTPException(status_code=400, detail="Only PNG/JPG/WebP files are allowed.")

    file_location = f"./temp_{os.path.basename(file.filename)}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    try:
        result = ingest_screenshot(file_location, db, project_id=project_id, advice_focus=advice_focus)
    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))

    os.remove(file_location)
    return {
        "message": f"Read {result['count']} metrics from the screenshot.",
        "analysis": result["analysis"],
    }


@app.post("/projects", response_model=ProjectOut)
def create_project(name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    proj = ProjectDB(name=name.strip(), description=description or "")
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@app.get("/projects", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(ProjectDB).all()


@app.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    proj = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj

@app.get("/projects/{project_id}/dashboard")
def get_project_dashboard(
    project_id: int, 
    role: str = "regional_manager_apac", 
    persona: str = "regional_manager", 
    db: Session = Depends(get_db)
):
    return build_project_dashboard(project_id, role, persona, db)

@app.get("/projects/{project_id}/narrative")
def get_project_narrative(
    project_id: int, 
    role: str = "regional_manager_apac", 
    persona: str = "regional_manager", 
    db: Session = Depends(get_db)
):
    from services.analytics import get_project_hypotheses
    import time
    
    t_start = time.perf_counter()
    hypos = get_project_hypotheses(project_id, db)
    
    t_gemini_start = time.perf_counter()
    narrative = None
    if hypos:
        if persona == "cfo":
            narrative = generate_cfo_narrative(hypos, business_impact_value=25000.0)
        else:
            narrative = generate_regional_manager_narrative(hypos)
    else:
        narrative = {
            "kpi_summary": "All KPIs are operating within standard historical baselines.",
            "executive_summary": "No statistical anomalies detected. Operating parameters are normal.",
            "magnitude": "Normal",
            "confidence": "High",
            "recommended_actions": [
                {
                    "driver": "Baseline operations",
                    "action": "Maintain current operational monitoring schedule.",
                    "expected_impact": "Operational stability"
                }
            ]
        }
    t_gemini_ms = (time.perf_counter() - t_gemini_start) * 1000
    t_total_ms = (time.perf_counter() - t_start) * 1000
    
    print(f"[PERF] Gemini request: {t_gemini_ms:.1f} ms")
    print(f"[PERF] Total narrative endpoint: {t_total_ms:.1f} ms")
    
    return narrative


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
            }
            for r in filtered_records
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
