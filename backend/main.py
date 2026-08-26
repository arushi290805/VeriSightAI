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
