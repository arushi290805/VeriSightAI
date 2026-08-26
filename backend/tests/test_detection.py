import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.detection import decompose_revenue, detect_anomaly, get_window_size
from models.schema import KPIRecordDB
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data.db import Base
from services.synthetic import generate_synthetic_revenue, generate_synthetic_churn
from datetime import date, timedelta
import math
import numpy as np

def test_decomposition_identity():
    # Test identity: price_effect + volume_effect + mix_effect == total_delta
    price_0, price_1 = 100.0, 80.0
    volume_0, volume_1 = 500.0, 350.0
    
    result = decompose_revenue(price_0, price_1, volume_0, volume_1)
    
    calculated_total = result["price_effect"] + result["volume_effect"] + result["mix_effect"]
    actual_total = (price_1 * volume_1) - (price_0 * volume_0)
    
    # Must hold exactly (or within floating point tolerance)
    assert math.isclose(calculated_total, actual_total, rel_tol=1e-9)
    assert math.isclose(result["total_delta"], actual_total, rel_tol=1e-9)
    print("Decomposition identity verified.")

def test_multi_factor_anomaly():
    # Use synthetic data to find the anomaly injected in the last 3 days for APAC WidgetB
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    end_date = date.today()
    start_date = end_date - timedelta(days=90)
    generate_synthetic_revenue(start_date, db)
    
    # Get history for APAC WidgetB excluding the anomaly point
    # Day 89 is an anomaly
    records = db.query(KPIRecordDB).filter(
        KPIRecordDB.kpi_name == "revenue",
        KPIRecordDB.dimensions['region'].as_string() == "APAC",
        KPIRecordDB.dimensions['product'].as_string() == "WidgetB"
    ).order_by(KPIRecordDB.date).all()
    
    history_values = [r.value for r in records[:-3]] # First 87 points (normal)
    anomaly_record = records[-1] # The 90th point (anomaly)
    
    # Previous point to decompose
    prev_record = records[-4] # Last normal point
    price_0 = prev_record.dimensions["price"]
    vol_0 = prev_record.dimensions["volume"]
    
    price_1 = anomaly_record.dimensions["price"]
    vol_1 = anomaly_record.dimensions["volume"]
    
    decomposition = decompose_revenue(price_0, price_1, vol_0, vol_1)
    
    baseline_value = np.mean(history_values[-28:])
    deviation_value = anomaly_record.value - baseline_value
    
    detection = detect_anomaly(
        kpi_name="revenue",
        grain="daily",
        history=history_values,
        current_value=anomaly_record.value,
        deviation_value=deviation_value,
        baseline_value=baseline_value
    )
    
    print("Decomposition:", decomposition)
    print("Detection:", detection)
    
    assert detection["method"] == "z-score"
    assert detection["is_anomaly"] is True
    assert detection["z_score"] < -2.5 # Should be a large negative z-score since price & vol dropped
    print("Multi-factor anomaly correctly detected and decomposed.")

def test_sparse_history_fallback():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    end_date = date.today()
    start_date = end_date - timedelta(weeks=24)
    generate_synthetic_churn(start_date, db)
    
    # Get NewApp history (should have only 3 points)
    records = db.query(KPIRecordDB).filter(
        KPIRecordDB.kpi_name == "churn_signal",
        KPIRecordDB.dimensions['product'].as_string() == "NewApp"
    ).order_by(KPIRecordDB.date).all()
    
    assert len(records) == 3
    
    history_values = [r.value for r in records[:-1]] # First 2 points
    current_value = records[-1].value
    
    # Peer group baseline (LegacyApp average)
    legacy_records = db.query(KPIRecordDB).filter(
        KPIRecordDB.kpi_name == "churn_signal",
        KPIRecordDB.dimensions['product'].as_string() == "LegacyApp"
    ).all()
    peer_average = np.mean([r.value for r in legacy_records])
    
    deviation_value = current_value - peer_average
    
    detection = detect_anomaly(
        kpi_name="churn_signal",
        grain="weekly",
        history=history_values,
        current_value=current_value,
        deviation_value=deviation_value,
        baseline_value=peer_average
    )
    
    print("Sparse History Detection:", detection)
    assert "peer_group_comparison" in detection["method"]
    assert detection["z_score"] is None
    print("Sparse-history product triggers peer-group fallback logic.")

if __name__ == "__main__":
    test_decomposition_identity()
    test_multi_factor_anomaly()
    test_sparse_history_fallback()
