import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from services.evidence import EvidenceItem, Hypothesis, assign_evidence_label, assign_confidence_tiers

def test_multifactor_high_confidence():
    # Multi-factor scenario (z > 3, >=2 independent sources, temporal precedence)
    ev1 = EvidenceItem(
        source="synthetic_erp.csv",
        method="z-score",
        contribution_pct=60.0,
        confidence="high",
        freshness_timestamp=datetime.now(),
        lineage_path="synthetic_erp.csv -> revenue -> APAC -> price",
        supports_hypothesis="Price drop drove revenue down",
        evidence_for=["Price dropped by 20%"],
        evidence_against=[],
        is_temporal_precedent=True
    )
    
    ev2 = EvidenceItem(
        source="marketing_db",
        method="SQL aggregation",
        contribution_pct=40.0,
        confidence="high",
        freshness_timestamp=datetime.now(),
        lineage_path="marketing_db -> volume",
        supports_hypothesis="Price drop drove revenue down",
        evidence_for=["Volume dropped concurrently"],
        evidence_against=[],
        is_temporal_precedent=False
    )
    
    hypo = Hypothesis(
        description="Price and volume drop in APAC WidgetB caused the revenue drop.",
        evidence_items=[ev1, ev2],
        data_missing=[],
        next_investigation_step="Check competitor pricing.",
        z_score_associated=5.6 # From Phase 2 test
    )
    
    label = assign_evidence_label(hypo)
    hypo.label = label
    
    assign_confidence_tiers([hypo])
    
    print(f"Multi-factor Label: {hypo.label} (Expected: likely_contributed_to)")
    print(f"Multi-factor Tier: {hypo.confidence_tier} (Expected: HIGH)")
    
    assert hypo.label == "likely_contributed_to"
    assert hypo.confidence_tier == "HIGH"


def test_ambiguous_scenario():
    # Two roughly equal hypotheses
    ev_a = EvidenceItem(
        source="system_a",
        method="rule-based threshold",
        contribution_pct=50.0,
        confidence="medium",
        freshness_timestamp=datetime.now(),
        lineage_path="sys_a",
        supports_hypothesis="A caused it",
        evidence_for=[],
        evidence_against=[],
        is_temporal_precedent=False
    )
    hypo_a = Hypothesis(
        description="Hypothesis A",
        evidence_items=[ev_a],
        data_missing=[],
        next_investigation_step="Investigate A",
        z_score_associated=2.1
    )
    
    ev_b = EvidenceItem(
        source="system_b",
        method="rule-based threshold",
        contribution_pct=48.0,
        confidence="medium",
        freshness_timestamp=datetime.now(),
        lineage_path="sys_b",
        supports_hypothesis="B caused it",
        evidence_for=[],
        evidence_against=[],
        is_temporal_precedent=False
    )
    hypo_b = Hypothesis(
        description="Hypothesis B",
        evidence_items=[ev_b],
        data_missing=[],
        next_investigation_step="Investigate B",
        z_score_associated=2.0
    )
    
    hypos = [hypo_a, hypo_b]
    
    # Assign labels
    for h in hypos:
        h.label = assign_evidence_label(h)
        
    # Assign tiers
    assign_confidence_tiers(hypos)
    
    print(f"Hypo A Tier: {hypo_a.confidence_tier} (Expected: AMBIGUOUS)")
    print(f"Hypo B Tier: {hypo_b.confidence_tier} (Expected: AMBIGUOUS)")
    
    assert hypo_a.confidence_tier == "AMBIGUOUS"
    assert hypo_b.confidence_tier == "AMBIGUOUS"

if __name__ == "__main__":
    test_multifactor_high_confidence()
    test_ambiguous_scenario()
