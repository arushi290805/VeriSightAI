import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.schema import Base, KPIRecordDB
from services.synthetic import generate_synthetic_revenue
from services.access import filter_records_by_role
from datetime import date, timedelta

def test_access_filtering():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    start = date.today() - timedelta(days=10)
    generate_synthetic_revenue(start, db)
    
    records = db.query(KPIRecordDB).all()
    
    # Total records: 90 days * 3 regions (NA, EMEA, APAC) * 2 products = 540
    assert len(records) == 540
    
    # Global CFO should see all 540
    cfo_records = filter_records_by_role(records, "global_cfo")
    print(f"CFO Records: {len(cfo_records)} (Expected: 540)")
    assert len(cfo_records) == 540
    
    # Regional Manager APAC should see only APAC (90 days * 1 region * 2 products = 180)
    apac_records = filter_records_by_role(records, "regional_manager_apac")
    print(f"APAC Manager Records: {len(apac_records)} (Expected: 180)")
    assert len(apac_records) == 180
    
    # Verify all apac records actually have region APAC
    for r in apac_records:
        assert r.dimensions.get("region") == "APAC"
        
if __name__ == "__main__":
    test_access_filtering()
