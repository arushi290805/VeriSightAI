import json
import os
import re
from datetime import date, datetime
from typing import Any, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from core.config import settings
from core.gemini_rotator import rotator
from models.schema import KPIRecordDB, ProjectDB
from services.profiling import build_time_series, profile_csv


class ExtractedKPI(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kpi_name: str = "metric"
    value: Any = None
    date: Optional[str] = None
    grain: Optional[str] = None
    unit: Optional[str] = None
    dimensions: dict = Field(default_factory=dict)
    change: Optional[str] = None


class ExtractedSeriesPoint(BaseModel):
    model_config = ConfigDict(extra="ignore")
    label: Optional[str] = None
    date: Optional[str] = None
    value: Any = None


class ExtractedSeries(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = "series"
    points: list[ExtractedSeriesPoint] = Field(default_factory=list)


class FlexibleDashboard(BaseModel):
    model_config = ConfigDict(extra="ignore")
    dashboard_type: Optional[str] = "custom"
    title: Optional[str] = None
    period: Optional[str] = None
    records: list[ExtractedKPI] = Field(default_factory=list)
    kpis: list[ExtractedKPI] = Field(default_factory=list)
    series: list[ExtractedSeries] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _source_name(path: str) -> str:
    return os.path.basename(path)


def _update_project_analysis(db: Session, project_id: Optional[int], advice_focus: str, analysis: dict[str, Any]) -> None:
    if not project_id:
        return
    proj = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not proj:
        return
    proj.advice_focus = advice_focus or proj.advice_focus
    proj.analysis = analysis
    db.add(proj)


def ingest_csv(
    file_path: str,
    db: Session,
    project_id: int = None,
    advice_focus: str = "",
    kpi_name: str = None,
    grain: str = None,
    date_col: str = None,
    value_col: str = None,
    dimension_cols: list[str] = None,
) -> dict[str, Any]:
    """Profile a CSV, compute formulas/correlations, and store compact KPI series."""
    packed = profile_csv(file_path, advice_focus or kpi_name or "")
    df = packed["df"]
    numeric_df = packed["numeric_df"]
    profile = packed["profile"]

    if value_col and value_col in numeric_df.columns:
        profile["target"] = value_col
    if date_col and date_col in df.columns:
        profile["date_column"] = date_col
    if kpi_name:
        profile["advice_focus"] = kpi_name

    extra = [c["field"] for c in profile["correlations"][:3]]
    series_map = build_time_series(df, numeric_df, profile, extra)

    source = _source_name(file_path)
    records: list[KPIRecordDB] = []
    for metric, series in series_map.items():
        for _, row in series.iterrows():
            raw_date = row["date"]
            if hasattr(raw_date, "to_pydatetime"):
                parsed = raw_date.to_pydatetime().date()
            elif hasattr(raw_date, "date") and not isinstance(raw_date, date):
                parsed = raw_date.date()
            else:
                parsed = raw_date
            records.append(
                KPIRecordDB(
                    project_id=project_id,
                    kpi_name=str(metric),
                    date=parsed,
                    grain=str(row["grain"]),
                    dimensions={"advice_focus": profile["advice_focus"]},
                    value=float(row["value"]),
                    source_file=source,
                )
            )

    if not records:
        raise ValueError("Could not derive a time series from this file. Check that it contains numeric values.")

    analysis = {
        "source_type": "csv",
        "advice_focus": profile["advice_focus"],
        "target": profile["target"],
        "row_count": profile["row_count"],
        "columns": profile["columns"],
        "formulas": profile["formulas"],
        "correlations": profile["correlations"],
        "categorical_drivers": profile["categorical_drivers"],
        "date_column": profile["date_column"],
        "aggregation": profile["aggregation"],
        "series_points": {name: int(len(s)) for name, s in series_map.items()},
    }

    db.add_all(records)
    _update_project_analysis(db, project_id, profile["advice_focus"], analysis)
    db.commit()
    return {"count": len(records), "analysis": analysis}


def _parse_number(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    text = str(raw).strip()
    if not text:
        return None
    multiplier = 1.0
    lower = text.lower().replace(" ", "")
    if lower.endswith("bn") or lower.endswith("b"):
        multiplier = 1_000_000_000
        lower = re.sub(r"[bn]$", "", lower)
    elif lower.endswith("m"):
        multiplier = 1_000_000
        lower = lower[:-1]
    elif lower.endswith("k"):
        multiplier = 1_000
        lower = lower[:-1]
    cleaned = re.sub(r"[^0-9.\-]", "", lower)
    if cleaned in {"", "-", ".", "-."}:
        return None
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def _parse_date(value: Optional[str], fallback: date) -> date:
    if not value:
        return fallback
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    parsed = None
    try:
        import pandas as pd
        parsed = pd.to_datetime(value, errors="coerce")
        if parsed is not None and not (hasattr(parsed, "isna") and parsed.isna()):
            return parsed.date()
    except Exception:
        pass
    return fallback


def ingest_screenshot(
    image_path: str,
    db: Session,
    project_id: int = None,
    advice_focus: str = "",
) -> dict[str, Any]:
    """Extract KPIs from arbitrary dashboard screenshots using Gemini Vision."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    suffix = os.path.splitext(image_path)[1].lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(suffix, "image/png")

    prompt = (
        "You are reading a business dashboard screenshot. Dashboards vary widely: "
        "sales, finance, marketing, operations, HR, product analytics, healthcare, logistics, or mixed tiles. "
        "Do not assume a fixed layout or required fields.\n"
        "Extract whatever metrics, charts, and breakdowns are actually visible.\n"
        "Return ONLY JSON with this flexible shape:\n"
        "{\n"
        '  "dashboard_type": "sales|finance|marketing|operations|hr|product|custom",\n'
        '  "title": string or null,\n'
        '  "period": string or null,\n'
        '  "kpis": [ { "kpi_name": string, "value": number, "unit": string or null, '
        '"date": "YYYY-MM-DD" or null, "grain": "snapshot|daily|weekly|monthly" or null, '
        '"dimensions": {optional string pairs}, "change": string or null } ],\n'
        '  "series": [ { "name": string, "points": [ { "label": string, "date": "YYYY-MM-DD" or null, "value": number } ] } ],\n'
        '  "notes": [short strings for non-numeric insights]\n'
        "}\n"
        "Parse currency, percentages, and compact numbers such as 1.2M or 3.4k into plain numbers. "
        "Skip decorative chrome. If a field is missing on the screenshot, omit it rather than inventing it. "
        f"User advice focus (use only if relevant): {advice_focus or 'not specified'}."
    )

    def _call_gemini(client):
        return client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=mime),
            ],
            config=genai.types.GenerateContentConfig(response_mime_type="application/json"),
        ).text

    response_text = rotator.execute_with_retry(_call_gemini)

    try:
        data = json.loads(response_text)
        validated = FlexibleDashboard.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError) as e:
        raise ValueError(f"Failed to parse dashboard screenshot: {e}")

    today = date.today()
    source_name = _source_name(image_path)
    kpi_items = validated.kpis or validated.records
    records: list[KPIRecordDB] = []

    for item in kpi_items:
        value = _parse_number(item.value)
        if value is None:
            continue
        dims = dict(item.dimensions or {})
        if item.unit:
            dims["unit"] = item.unit
        if item.change:
            dims["change"] = item.change
        if validated.dashboard_type:
            dims["dashboard_type"] = validated.dashboard_type
        records.append(
            KPIRecordDB(
                project_id=project_id,
                kpi_name=item.kpi_name or "metric",
                date=_parse_date(item.date, today),
                grain=item.grain or "snapshot",
                dimensions=dims,
                value=float(value),
                source_file=source_name,
            )
        )

    for series in validated.series:
        for idx, point in enumerate(series.points):
            value = _parse_number(point.value)
            if value is None:
                continue
            point_date = _parse_date(point.date, today)
            records.append(
                KPIRecordDB(
                    project_id=project_id,
                    kpi_name=series.name or "series",
                    date=point_date,
                    grain="daily" if point.date else "snapshot",
                    dimensions={"label": point.label or str(idx), "dashboard_type": validated.dashboard_type},
                    value=float(value),
                    source_file=source_name,
                )
            )

    if not records:
        raise ValueError("No numeric KPIs could be read from this screenshot. Try a clearer image or a different view.")

    analysis = {
        "source_type": "screenshot",
        "advice_focus": advice_focus,
        "dashboard_type": validated.dashboard_type,
        "title": validated.title,
        "period": validated.period,
        "notes": validated.notes,
        "extracted_kpis": [r.kpi_name for r in records],
    }
    db.add_all(records)
    _update_project_analysis(db, project_id, advice_focus, analysis)
    db.commit()
    return {"count": len(records), "analysis": analysis}
