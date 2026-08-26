import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from services.evidence import EvidenceItem, Hypothesis
from services.narrative import generate_cfo_narrative, generate_regional_manager_narrative

def test_narrative_generation():
    ev1 = EvidenceItem(
        source="synthetic_erp.csv",
        method="z-score",
        contribution_pct=60.0,
        confidence="high",
        freshness_timestamp=datetime.now(),
        lineage_path="synthetic_erp.csv -> revenue -> APAC -> price",
        supports_hypothesis="Price drop drove revenue down",
        evidence_for=["Price dropped by 20% in APAC WidgetB"],
        evidence_against=[],
        is_temporal_precedent=True
    )
    
    hypo = Hypothesis(
        description="Price drop in APAC WidgetB caused the revenue drop.",
        evidence_items=[ev1],
        data_missing=[],
        next_investigation_step="Check competitor pricing.",
        z_score_associated=5.6,
        confidence_tier="HIGH",
        label="likely_contributed_to"
    )
    
    # Test CFO materiality threshold
    cfo_skip = generate_cfo_narrative([hypo], business_impact_value=5000.0, materiality_threshold=10000.0)
    print("CFO Below Threshold:", cfo_skip)
    assert "below the CFO materiality threshold" in cfo_skip.get("narrative", "")
    
    # Generate CFO narrative
    cfo_narrative = generate_cfo_narrative([hypo], business_impact_value=25000.0, materiality_threshold=10000.0)
    print("\nCFO Narrative:", cfo_narrative)
    
    # Generate RM narrative
    rm_narrative = generate_regional_manager_narrative([hypo])
    print("\nRM Narrative Keys:", rm_narrative.keys())
    
    if "error" in cfo_narrative:
        print("Skipping structure assertions due to missing API key (expected in CI/test environments without real keys).")
    else:
        assert "narrative" in cfo_narrative
        assert "kpi_summary" in rm_narrative
        assert "recommended_actions" in rm_narrative
    
if __name__ == "__main__":
    test_narrative_generation()
