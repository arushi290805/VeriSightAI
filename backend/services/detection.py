import numpy as np
from scipy import stats
from typing import List, Dict, Any, Tuple
from core.contracts import CONTRACTS

# DETERMINISTIC
def get_window_size(grain: str) -> int:
    if grain == "daily": return 28
    if grain == "weekly": return 8
    if grain == "monthly": return 6
    return 28

# DETERMINISTIC
def compute_z_score(history: List[float], current_value: float) -> Tuple[float, float, float]:
    """
    Computes Z-score using trailing window (excluding current point).
    Returns (z_score, mean, std)
    """
    if len(history) == 0:
        return 0.0, current_value, 0.0
    mean = np.mean(history)
    std = np.std(history)
    if std == 0:
        std = 1e-9 # avoid division by zero
    z = (current_value - mean) / std
    return float(z), float(mean), float(std)

# DETERMINISTIC
def decompose_revenue(price_0: float, price_1: float, volume_0: float, volume_1: float) -> Dict[str, float]:
    """
    Price/Volume/Mix decomposition for revenue.
    """
    price_effect = (price_1 - price_0) * volume_0
    volume_effect = (volume_1 - volume_0) * price_0
    mix_effect = (price_1 - price_0) * (volume_1 - volume_0)
    
    return {
        "price_effect": price_effect,
        "volume_effect": volume_effect,
        "mix_effect": mix_effect,
        "total_delta": price_effect + volume_effect + mix_effect
    }

# DETERMINISTIC
def calculate_anomaly_score(z: float, history: List[float], mean: float, std: float, deviation_value: float, baseline_value: float) -> float:
    """
    Computes Anomaly Confidence Score.
    """
    # Magnitude
    magnitude = min(abs(z) / 5.0, 1.0)
    
    # Significance (2-tailed p-value)
    # p_value is the probability of observing a value at least as extreme as z
    p_value = 2 * stats.norm.sf(abs(z))
    significance = 1.0 - p_value
    
    # Persistence
    if len(history) < 5:
        persistence = 0.0
    else:
        last_5 = history[-5:]
        exceeded_count = sum(1 for x in last_5 if abs(x - mean) > std)
        persistence = exceeded_count / 5.0
        
    # Business Impact
    if baseline_value == 0:
        business_impact = 1.0
    else:
        business_impact = min(abs(deviation_value) / abs(baseline_value), 1.0)
        
    return magnitude * significance * persistence * business_impact

# DETERMINISTIC
def detect_anomaly(kpi_name: str, grain: str, history: List[float], current_value: float, deviation_value: float, baseline_value: float) -> Dict[str, Any]:
    """
    Main detection logic combining z-score, sparse history rules, and thresholds.
    """
    contract = CONTRACTS.get(kpi_name)
    if not contract:
        raise ValueError(f"Contract not found for KPI {kpi_name}")
        
    window = get_window_size(grain)
    recent_history = history[-window:] if len(history) >= window else history
    
    # Sparse-history rule: < 21 data points of history in total (not just recent)
    if len(history) < 21:
        # Instead of z-score, we simulate a peer-group comparison for the prototype
        peer_average = baseline_value # Mocking the peer average as baseline
        deviation = current_value - peer_average
        return {
            "method": "peer_group_comparison (insufficient history: N days, using category average as baseline)",
            "is_anomaly": abs(deviation) > (peer_average * 0.1), # simple 10% threshold for peer comparison
            "z_score": None,
            "anomaly_score": 0.5, # Default medium score for peer comparison
            "mean": peer_average,
            "std": None
        }
        
    z, mean, std = compute_z_score(recent_history, current_value)
    
    is_anomaly = abs(z) > contract.thresholds.z_score_alert
    score = calculate_anomaly_score(z, recent_history, mean, std, deviation_value, baseline_value)
    
    return {
        "method": "z-score",
        "is_anomaly": is_anomaly,
        "z_score": z,
        "anomaly_score": score,
        "mean": mean,
        "std": std
    }
