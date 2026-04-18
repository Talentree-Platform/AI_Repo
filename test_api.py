import requests
import json

BASE = "http://localhost:8000"
BO = "a091d9c9-e581-4f6e-8cf6-d38fc68dffbf"

tests = [
    ("GET", "/ai/status", "Health Check"),
    ("GET", f"/ai/dashboard/{BO}", "Dashboard"),
    ("GET", f"/ai/analytics/revenue-trend/{BO}?period=monthly", "Revenue Trend"),
    ("GET", f"/ai/reviews/trends/{BO}?period=monthly", "Review Trends"),
    ("GET", f"/ai/benchmark/{BO}", "Benchmark"),
    ("GET", "/ai/models/status", "Models Status"),
    ("POST", f"/ai/predict/churn/{BO}", "Predict Churn"),
    ("POST", "/ai/predict/fraud/1", "Predict Fraud"),
    ("POST", "/ai/predict/anomaly/1001", "Predict Anomaly"),
    ("POST", "/ai/predict/sentiment/1", "Predict Sentiment"),
    ("POST", "/ai/predict/triage/1", "Predict Triage"),
    ("POST", "/ai/predict/demand/15", "Predict Demand"),
    ("POST", f"/ai/compute/product/15", "Compute Product"),
    ("POST", f"/ai/compute/profile/{BO}", "Compute Profile"),
    ("POST", "/ai/compute/request/1", "Compute Request"),
    ("POST", "/ai/compute/materials/all", "Compute Materials"),
    ("POST", f"/ai/notify/check/{BO}", "Notify Check"),
    ("POST", "/ai/train/all", "Train All (retrain)"),
    ("GET", f"/ai/export/financial/{BO}?format=csv", "Export CSV"),
    ("GET", f"/ai/export/financial/{BO}?format=pdf", "Export PDF"),
]

passed = 0
failed = 0
for method, path, name in tests:
    try:
        url = BASE + path
        if method == "POST":
            r = requests.post(url, timeout=60)
        else:
            r = requests.get(url, timeout=60)
        status = r.status_code
        ok = status == 200
        if ok:
            passed += 1
            print(f"  [OK]  {name:25s} -> {status}")
        else:
            failed += 1
            detail = r.json().get("detail", "")[:80] if r.headers.get("content-type","").startswith("application/json") else ""
            print(f"  [FAIL] {name:25s} -> {status} {detail}")
    except Exception as e:
        failed += 1
        print(f"  [ERR] {name:25s} -> {e}")

print(f"\n{'='*50}")
print(f"  PASSED: {passed}/{len(tests)}  |  FAILED: {failed}/{len(tests)}")
print(f"{'='*50}")
