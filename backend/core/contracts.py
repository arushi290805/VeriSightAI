import os
import yaml
from pydantic import BaseModel
from typing import List, Dict, Any

class Thresholds(BaseModel):
    z_score_alert: float
    z_score_high_confidence: float

class SemanticContract(BaseModel):
    name: str
    definition: str
    calculation: str
    grain: str
    refresh_cadence: str
    drivers: List[str]
    thresholds: Thresholds
    lineage_source: str
    access_roles: List[str]

def load_contracts(contracts_dir: str = "./contracts") -> Dict[str, SemanticContract]:
    contracts = {}
    if not os.path.exists(contracts_dir):
        return contracts
        
    for filename in os.listdir(contracts_dir):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            filepath = os.path.join(contracts_dir, filename)
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
                contract = SemanticContract(**data)
                contracts[contract.name] = contract
                
    return contracts

# Global store for contracts
CONTRACTS = load_contracts(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contracts"))
