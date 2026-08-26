from typing import List, Dict, Any

ROLE_ACCESS = {
    "regional_manager_apac": {"regions": ["APAC"], "detail_level": "full"},
    "global_cfo": {"regions": ["ALL"], "detail_level": "summary"},
}

# DETERMINISTIC
def filter_records_by_role(records: List[Any], role: str) -> List[Any]:
    """
    Filters KPI records based on the user's role access regions.
    """
    access = ROLE_ACCESS.get(role)
    if not access:
        # Default to no access if role is invalid
        return []
        
    allowed_regions = access.get("regions", [])
    
    if "ALL" in allowed_regions:
        return records
        
    filtered = []
    for record in records:
        # Assuming record is a SQLAlchemy model or Pydantic model with 'dimensions' dict
        dims = record.dimensions if hasattr(record, "dimensions") else {}
        region = dims.get("region")
        
        # If the KPI doesn't have a region dimension, it's global, we can allow or deny.
        # Let's say if region is specified, check it. If not specified, allow.
        if region:
            if region in allowed_regions:
                filtered.append(record)
        else:
            # Global metric (like marketing conversion by channel, no region)
            filtered.append(record)
            
    return filtered

# DETERMINISTIC
def filter_evidence_by_role(evidence_items: List[Any], role: str) -> List[Any]:
    """
    Filters evidence items based on role access.
    """
    access = ROLE_ACCESS.get(role)
    if not access:
        return []
        
    allowed_regions = access.get("regions", [])
    if "ALL" in allowed_regions:
        return evidence_items
        
    filtered = []
    for item in evidence_items:
        # Simple heuristic: if the evidence text or lineage mentions a region not allowed, filter it out.
        # A more robust system would tag evidence with regions.
        lineage = getattr(item, "lineage_path", "").upper()
        
        # Check if the lineage contains any region constraint
        # E.g. "synthetic_erp.csv -> revenue -> APAC -> price"
        # Only allow if it mentions an allowed region or doesn't mention any restricted region.
        # For simplicity, if it explicitly mentions a region NOT in allowed_regions, filter it.
        all_possible_regions = ["NA", "EMEA", "APAC", "LATAM"] # example set
        
        explicitly_mentions_other_region = False
        for r in all_possible_regions:
            if r in lineage and r not in allowed_regions:
                explicitly_mentions_other_region = True
                break
                
        if not explicitly_mentions_other_region:
            filtered.append(item)
            
    return filtered
