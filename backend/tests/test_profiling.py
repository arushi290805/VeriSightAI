import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from services.profiling import discover_formulas, profile_csv, choose_target


def test_product_formula_and_sales_target():
    df = pd.DataFrame({
        "Order Date": ["01-12-2019", "02-12-2019", "03-12-2019"] * 20,
        "Quantity Ordered": [1, 2, 3] * 20,
        "Price Each": [10.0, 5.0, 8.0] * 20,
        "Sales": [10.0, 10.0, 24.0] * 20,
        "City": ["Austin", "Dallas", "Austin"] * 20,
    })
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp:
        df.to_csv(tmp.name, index=False)
        path = tmp.name
    try:
        packed = profile_csv(path, "which products drive sales")
        profile = packed["profile"]
        assert profile["target"] == "Sales"
        kinds = {f["kind"] for f in profile["formulas"]}
        assert "product" in kinds
        fields = {c["field"] for c in profile["correlations"]}
        assert "Quantity Ordered" in fields or "Price Each" in fields
    finally:
        os.remove(path)


def test_choose_target_uses_advice():
    cols = ["Clicks", "Revenue", "Impressions"]
    assert choose_target(cols, "help me improve conversion and revenue", []) == "Revenue"


if __name__ == "__main__":
    test_product_formula_and_sales_target()
    test_choose_target_uses_advice()
    print("profiling tests passed")
