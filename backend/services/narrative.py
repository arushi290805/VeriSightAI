import json
from google import genai
from core.gemini_rotator import rotator
from core.config import settings
from services.evidence import Hypothesis
from typing import Dict, Any, List

CFO_PROMPT = """
You are a CFO assistant analyzing business anomalies.
Narrate only the facts present in this JSON evidence. Do not add any number, cause, or recommendation not explicitly present in the evidence. If evidence is ambiguous, state that plainly.

Requirements:
- 3-4 sentences max.
- Dollar-impact-led.
- No operational jargon.
- Format as a simple JSON object: { "narrative": "..." }

Evidence Ledger:
{evidence_json}
"""

REGIONAL_MANAGER_PROMPT = """
You are a Regional Manager assistant analyzing business anomalies.
Narrate only the facts present in this JSON evidence. Do not add any number, cause, or recommendation not explicitly present in the evidence. If evidence is ambiguous, state that plainly.

Format your response STRICTLY as a JSON object matching this schema:
{
  "kpi_summary": "KPI: <name> <direction> <magnitude>% <period>",
  "executive_summary": "<1-2 sentences>",
  "magnitude": "<dollar or unit impact>",
  "primary_drivers": ["<bulleted, with % contribution>"],
  "supporting_evidence": ["<bulleted, each citing its source and method>"],
  "confidence": "<tier> (<numeric score>) — <one sentence why>",
  "recommended_actions": [
    {
      "driver": "string",
      "controllable_lever": "string",
      "action": "string",
      "expected_impact": "string",
      "owner": "string",
      "confidence": "string",
      "monitoring_plan": "string"
    }
  ],
  "expected_impact_range": "<range, explicitly labeled as an estimate>"
}

Evidence Ledger:
{evidence_json}
"""

# LLM-ASSISTED
def generate_cfo_narrative(hypotheses: List[Hypothesis], business_impact_value: float, materiality_threshold: float = 10000.0) -> Dict[str, Any]:
    """Generates the CFO narrative, only if materiality threshold is met."""
    if abs(business_impact_value) < materiality_threshold:
        return {"narrative": f"Anomaly detected but financial impact (${abs(business_impact_value):,.2f}) is below the CFO materiality threshold (${materiality_threshold:,.2f}). No action required at executive level."}

    evidence_json = json.dumps([h.model_dump(mode='json') for h in hypotheses])
    prompt = CFO_PROMPT.replace("{evidence_json}", evidence_json)

    def _call(client):
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(response_mime_type="application/json")
        )
        return response.text

    try:
        res = rotator.execute_with_retry(_call)
        return json.loads(res)
    except Exception as e:
        return {"error": str(e), "narrative": "Failed to generate CFO narrative."}

# LLM-ASSISTED
def generate_regional_manager_narrative(hypotheses: List[Hypothesis]) -> Dict[str, Any]:
    """Generates the full structured KPI story for a Regional Manager."""
    evidence_json = json.dumps([h.model_dump(mode='json') for h in hypotheses])
    prompt = REGIONAL_MANAGER_PROMPT.replace("{evidence_json}", evidence_json)

    def _call(client):
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(response_mime_type="application/json")
        )
        return response.text

    try:
        res = rotator.execute_with_retry(_call)
        return json.loads(res)
    except Exception as e:
        return {"error": str(e), "kpi_summary": "Failed to generate narrative."}
