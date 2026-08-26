import pandas as pd
import numpy as np
from datetime import timedelta, date
from sqlalchemy.orm import Session
from models.schema import KPIRecordDB

# DETERMINISTIC
def generate_synthetic_revenue(start_date: date, db: Session):
    """Generates 90 days of daily revenue with a multi-factor anomaly at the end."""
    records = []
    regions = ["NA", "EMEA", "APAC"]
    products = ["WidgetA", "WidgetB"]
    
    # Base parameters
    base_price = {"WidgetA": 100.0, "WidgetB": 200.0}
    base_vol = {"NA": 500, "EMEA": 300, "APAC": 200}
    
    np.random.seed(42)
    
    for day in range(90):
        current_date = start_date + timedelta(days=day)
        is_anomaly = day >= 87 # Last 3 days have anomaly
        
        for region in regions:
            for product in products:
                # Add some noise
                price_noise = np.random.normal(0, 2)
                vol_noise = int(np.random.normal(0, 15))
                
                price = base_price[product] + price_noise
                vol = base_vol[region] + vol_noise
                
                if is_anomaly and region == "APAC" and product == "WidgetB":
                    # Multi-factor anomaly: price drops AND volume drops
                    price *= 0.8
                    vol = int(vol * 0.7)
                
                value = price * vol
                
                records.append(
                    KPIRecordDB(
                        kpi_name="revenue",
                        date=current_date,
                        grain="daily",
                        dimensions={"region": region, "product": product, "price": price, "volume": vol},
                        value=value,
                        source_file="synthetic_erp_export.csv"
                    )
                )
    
    db.add_all(records)
    db.commit()

# DETERMINISTIC
def generate_synthetic_marketing(start_date: date, db: Session):
    """Generates 12 weeks of weekly marketing conversion."""
    records = []
    channels = ["Social", "Search", "Email"]
    
    np.random.seed(42)
    
    for week in range(12):
        current_date = start_date + timedelta(weeks=week)
        
        for channel in channels:
            # Baseline conversion rate around 2.0 - 5.0%
            conv_rate = np.random.uniform(2.0, 5.0)
            
            records.append(
                KPIRecordDB(
                    kpi_name="marketing_conversion",
                    date=current_date,
                    grain="weekly",
                    dimensions={"channel": channel},
                    value=conv_rate,
                    source_file="synthetic_marketing.csv"
                )
            )
            
    db.add_all(records)
    db.commit()

# DETERMINISTIC
def generate_synthetic_churn(start_date: date, db: Session):
    """Generates 6 months of monthly churn signal (one product with only 3 weeks of history)."""
    # Wait, the spec says "6 months monthly churn signal including one product line with only 3 weeks of history."
    # If it's monthly, 6 months is 6 points. "3 weeks of history" for a monthly KPI means it's less than a month, or maybe the grain is weekly for that product?
    # Actually, it might be monthly but the new product has only 1 point, or it's weekly for that product.
    # Let's make it monthly for existing products, and the new product has only 3 weekly points or just 1 monthly point.
    # The requirement specifically says: "one product line with only 3 weeks of history." Let's record it as weekly for the new product, or just say grain="weekly" for churn overall and 24 weeks?
    # Let's stick to weekly grain for churn, 24 weeks = ~6 months.
    
    records = []
    products = ["LegacyApp", "NewApp"]
    
    np.random.seed(42)
    
    for week in range(24):
        current_date = start_date + timedelta(weeks=week)
        
        # LegacyApp has full 24 weeks
        churn_legacy = np.random.uniform(1.0, 2.5)
        records.append(
            KPIRecordDB(
                kpi_name="churn_signal",
                date=current_date,
                grain="weekly",
                dimensions={"product": "LegacyApp"},
                value=churn_legacy,
                source_file="synthetic_churn.csv"
            )
        )
        
        # NewApp has only 3 weeks of history
        if week >= 21: # last 3 weeks
            churn_new = np.random.uniform(1.5, 3.0)
            records.append(
                KPIRecordDB(
                    kpi_name="churn_signal",
                    date=current_date,
                    grain="weekly",
                    dimensions={"product": "NewApp"},
                    value=churn_new,
                    source_file="synthetic_churn.csv"
                )
            )
            
    db.add_all(records)
    db.commit()

# DETERMINISTIC
def seed_synthetic_data(db: Session):
    # Clear existing synthetic data if any
    db.query(KPIRecordDB).filter(KPIRecordDB.source_file.like("synthetic_%")).delete()
    
    end_date = date.today()
    generate_synthetic_revenue(end_date - timedelta(days=90), db)
    generate_synthetic_marketing(end_date - timedelta(weeks=12), db)
    generate_synthetic_churn(end_date - timedelta(weeks=24), db)
