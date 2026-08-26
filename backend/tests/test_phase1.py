import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.schema import Base, KPIRecordDB
from services.synthetic import seed_synthetic_data

# Use an in-memory SQLite database for testing
engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def test_synthetic_data():
    db = SessionLocal()
    seed_synthetic_data(db)
    
    # Check revenue records (90 days * 3 regions * 2 products = 540)
    revenue_count = db.query(KPIRecordDB).filter(KPIRecordDB.kpi_name == "revenue").count()
    print(f"Revenue records: {revenue_count} (Expected: 540)")
    assert revenue_count == 540
    
    # Check marketing conversion (12 weeks * 3 channels = 36)
    marketing_count = db.query(KPIRecordDB).filter(KPIRecordDB.kpi_name == "marketing_conversion").count()
    print(f"Marketing conversion records: {marketing_count} (Expected: 36)")
    assert marketing_count == 36
    
    # Check churn signal (LegacyApp 24 weeks + NewApp 3 weeks = 27)
    churn_count = db.query(KPIRecordDB).filter(KPIRecordDB.kpi_name == "churn_signal").count()
    print(f"Churn signal records: {churn_count} (Expected: 27)")
    assert churn_count == 27
    
    print("All synthetic data generated correctly and loaded into the internal schema.")
    
if __name__ == "__main__":
    test_synthetic_data()
