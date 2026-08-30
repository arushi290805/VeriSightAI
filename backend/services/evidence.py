from pydantic import BaseModel
from typing import List, Literal, Dict, Any, Optional
from datetime import datetime
import json
import google.genai as genai
from google import genai
from core.gemini_rotator import rotator
from core.config import settings
import hashlib

class EvidenceItem(BaseModel):
    source: str
    method: str  # e.g. "z-score", "SQL aggregation", "Gemini retrieval match", "rule-based threshold", "controlled_comparison"
    contribution_pct: float
    confidence: str  # "high" | "medium" | "low"
    freshness_timestamp: datetime
    lineage_path: str
    supports_hypothesis: str
    evidence_for: List[str]
    evidence_against: List[str]
    is_temporal_precedent: bool = False # Added field to explicitly flag temporal precedence

class Hypothesis(BaseModel):
    description: str
    evidence_items: List[EvidenceItem]
    label: Literal["correlated_with", "likely_contributed_to", "causal_evidence_supports"] = "correlated_with"
    confidence_tier: Literal["HIGH", "MEDIUM", "LOW", "AMBIGUOUS"] = "LOW"
    data_missing: List[str]
    next_investigation_step: str
    z_score_associated: Optional[float] = None

# DETERMINISTIC
def assign_evidence_label(hypothesis: Hypothesis) -> str:
    """Assigns label based on deterministic rules."""
    has_controlled_comparison = any("controlled_comparison" in item.method for item in hypothesis.evidence_items)
    
    if has_controlled_comparison:
        return "causal_evidence_supports"
        
    independent_sources = set(item.source for item in hypothesis.evidence_items)
    has_temporal_precedence = any(item.is_temporal_precedent for item in hypothesis.evidence_items)
    
    if len(independent_sources) >= 2 and has_temporal_precedence:
        return "likely_contributed_to"
        
    return "correlated_with"

# DETERMINISTIC
def calculate_hypothesis_strength(hypothesis: Hypothesis) -> float:
    """Helper to calculate a numeric strength for ambiguity checks."""
    score = 0.0
    for item in hypothesis.evidence_items:
        weight = 1.0
        if item.confidence == "high": weight = 3.0
        elif item.confidence == "medium": weight = 2.0
        score += weight * (item.contribution_pct / 100.0 if item.contribution_pct > 0 else 1.0)
    
    # Boost if it has causal evidence
    label = assign_evidence_label(hypothesis)
    if label == "causal_evidence_supports": score *= 2.0
    elif label == "likely_contributed_to": score *= 1.5
    
    if hypothesis.z_score_associated:
        score *= min(abs(hypothesis.z_score_associated) / 2.0, 2.0)
        
    return score

# DETERMINISTIC
def assign_confidence_tiers(hypotheses: List[Hypothesis]) -> None:
    """Assigns confidence tier and detects ambiguous scenarios."""
    if not hypotheses:
        return
        
    # Calculate strengths
    strengths = [calculate_hypothesis_strength(h) for h in hypotheses]
    
    # Check for ambiguity if more than 1 hypothesis
    if len(hypotheses) >= 2:
        sorted_indices = sorted(range(len(strengths)), key=lambda k: strengths[k], reverse=True)
        top1 = strengths[sorted_indices[0]]
        top2 = strengths[sorted_indices[1]]
        
        # If top 2 are within 15% of each other, mark both as AMBIGUOUS
        if top1 > 0 and (top1 - top2) / top1 <= 0.15:
            for i in sorted_indices:
                if (top1 - strengths[i]) / top1 <= 0.15:
                    hypotheses[i].confidence_tier = "AMBIGUOUS"
                    hypotheses[i].next_investigation_step = "Run controlled A/B test to isolate variables and resolve ambiguity."
            return

    # Normal assignment
    for h in hypotheses:
        independent_sources = set(item.source for item in h.evidence_items)
        has_temporal_precedence = any(item.is_temporal_precedent for item in h.evidence_items)
        has_controlled = any("controlled_comparison" in item.method for item in h.evidence_items)
        z = abs(h.z_score_associated) if h.z_score_associated else 0.0
        
        if z > 3 and len(independent_sources) >= 2 and has_temporal_precedence:
            h.confidence_tier = "HIGH"
        elif z > 2 and len(independent_sources) >= 1 and not has_controlled:
            h.confidence_tier = "MEDIUM"
        else:
            h.confidence_tier = "LOW"

_retrieval_cache = {}

# LLM-ASSISTED
def retrieve_unstructured_evidence(text_snippets: List[Dict[str, str]], dimensions: Dict[str, str], time_window: str) -> List[Dict[str, Any]]:
    """
    Uses Gemini to do semantic matching over unstructured evidence text.
    text_snippets should be [{"id": "1", "text": "..."}, ...]
    """
    if not text_snippets:
        return []

    # Cache key
    input_hash = hashlib.md5(json.dumps({
        "snippets": text_snippets,
        "dim": dimensions,
        "window": time_window
    }, sort_keys=True).encode()).hexdigest()
    
    if input_hash in _retrieval_cache:
        return _retrieval_cache[input_hash]

    prompt = f"""
    Given the following anomaly dimensions: {json.dumps(dimensions)}
    Time window: {time_window}
    
    Evaluate the relevance of the following text snippets to the anomaly.
    Snippets: {json.dumps(text_snippets)}
    
    Return ONLY a JSON array of objects with the structure:
    [{{ "snippet_id": string, "relevance_score": number (0 to 1), "reasoning": string }}]
    Do not output markdown blocks or any other text.
    """

    def _call_gemini(client):
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return response.text

    response_text = rotator.execute_with_retry(_call_gemini)
    
    try:
        data = json.loads(response_text)
        _retrieval_cache[input_hash] = data
        return data
    except Exception as e:
        print(f"Failed to parse retrieval output: {e}\nRaw: {response_text}")
        return []
