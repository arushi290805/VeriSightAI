from sqlalchemy import Column, Integer, String, Float, Date, JSON
from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import Dict, Any, Optional

from data.db import Base

class KPIRecordDB(Base):
    __tablename__ = "kpi_records"

    id = Column(Integer, primary_key=True, index=True)
    kpi_name = Column(String, index=True)
    date = Column(Date, index=True)
    grain = Column(String)  # daily, weekly, monthly
    dimensions = Column(JSON)  # e.g., {"region": "APAC", "product": "Widget"}
    value = Column(Float)
    source_file = Column(String)

from sqlalchemy import DateTime

class TelemetryLogDB(Base):
    __tablename__ = "telemetry_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    step = Column(String)
    model = Column(String)
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)
    latency_ms = Column(Float)
    estimated_cost_usd = Column(Float)

class KPIRecord(BaseModel):
    kpi_name: str
    date: date
    grain: str
    dimensions: Dict[str, Any]
    value: float
    source_file: str

    model_config = ConfigDict(from_attributes=True)
