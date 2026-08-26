import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.schema import Base, TelemetryLogDB
from services.telemetry import with_telemetry

def test_telemetry():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Create a dummy function to wrap
    @with_telemetry("dummy_step")
    def dummy_gemini_call(prompt: str, db=None):
        # Simulate processing time
        time.sleep(0.1)
        return f"Response to: {prompt}"
        
    # Call 1
    res1 = dummy_gemini_call("Hello", db=db)
    
    # Call 2 (identical prompt, should hit cache and NOT log to DB again)
    res2 = dummy_gemini_call("Hello", db=db)
    
    # Call 3 (different prompt)
    res3 = dummy_gemini_call("World", db=db)
    
    assert res1 == "Response to: Hello"
    assert res1 == res2
    assert res3 == "Response to: World"
    
    # Check DB logs
    logs = db.query(TelemetryLogDB).all()
    
    # Should only be 2 logs because the 2nd call hit the cache!
    print(f"Telemetry logs count: {len(logs)} (Expected: 2)")
    assert len(logs) == 2
    
    for log in logs:
        print(f"Logged Step: {log.step}, Latency: {log.latency_ms:.2f}ms, Cost: ${log.estimated_cost_usd:.6f}")
        assert log.step == "dummy_step"
        assert log.latency_ms >= 100.0 # because of time.sleep(0.1)
        assert log.estimated_cost_usd > 0
        
    print("Telemetry logging and caching verified.")

if __name__ == "__main__":
    test_telemetry()
