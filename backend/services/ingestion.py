import pandas as pd
import json
from datetime import datetime
from sqlalchemy.orm import Session
from models.schema import KPIRecordDB, KPIRecord
from core.config import settings
from core.gemini_rotator import rotator
import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError

class ExtractedKPI(BaseModel):
    kpi_name: str
    date: str # ISO format YYYY-MM-DD
    grain: str
    dimensions: dict
    value: float

class ExtractionResponse(BaseModel):
    records: list[ExtractedKPI]

# DETERMINISTIC
def ingest_csv(file_path: str, kpi_name: str, grain: str, date_col: str, value_col: str, dimension_cols: list[str], db: Session) -> int:
    """Generic CSV loader."""
    df = pd.read_csv(file_path)
    
    records = []
    for _, row in df.iterrows():
        try:
            # Parse date safely
            raw_date = row[date_col]
            parsed_date = pd.to_datetime(raw_date).date()
        except:
            continue
            
        dimensions = {col: row[col] for col in dimension_cols if col in row}
        
        try:
            value = float(row[value_col])
        except:
            continue
            
        records.append(
            KPIRecordDB(
                kpi_name=kpi_name,
                date=parsed_date,
                grain=grain,
                dimensions=dimensions,
                value=value,
                source_file=file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1]
            )
        )
        
    db.add_all(records)
    db.commit()
    return len(records)

# LLM-ASSISTED
def ingest_screenshot(image_path: str, db: Session) -> int:
    """Extracts KPI values from dashboard screenshots using Gemini Vision."""
    # Use the File API for uploading the image if needed, or send bytes.
    # Since we use google-generativeai, we can pass a PIL Image or upload it.
    import PIL.Image
    
    try:
        img = PIL.Image.open(image_path)
    except Exception as e:
        raise ValueError(f"Could not read image: {e}")

    prompt = (
        "Extract structured KPI values from this dashboard screenshot. "
        "Return ONLY structured JSON matching this schema: "
        "{ \"records\": [ { \"kpi_name\": string, \"date\": \"YYYY-MM-DD\", \"grain\": \"daily\"|\"weekly\"|\"monthly\", "
        "\"dimensions\": { string: string }, \"value\": number } ] }. "
        "Do not include any markdown formatting, narrative, or commentary. "
        "Just the raw JSON."
    )

    def _call_gemini():
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        # We can enforce JSON schema if we use generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
        response = model.generate_content(
            [prompt, img],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        return response.text

    response_text = rotator.execute_with_retry(_call_gemini)
    
    try:
        data = json.loads(response_text)
        validated = ExtractionResponse(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"Failed to parse Gemini output into structured schema: {e}\nRaw output: {response_text}")

    records = []
    source_name = image_path.split("/")[-1] if "/" in image_path else image_path.split("\\")[-1]
    for item in validated.records:
        parsed_date = datetime.strptime(item.date, "%Y-%m-%d").date()
        records.append(
            KPIRecordDB(
                kpi_name=item.kpi_name,
                date=parsed_date,
                grain=item.grain,
                dimensions=item.dimensions,
                value=item.value,
                source_file=source_name
            )
        )

    db.add_all(records)
    db.commit()
    return len(records)
