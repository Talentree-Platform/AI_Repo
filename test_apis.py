import requests
import sys
sys.path.append(".")
from db.connection import get_conn

conn = get_conn()
cursor = conn.cursor()

cursor.execute("SELECT TOP 1 Id FROM BoProductionRequests WHERE FraudScore IS NOT NULL")
req_row = cursor.fetchone()
req_id = req_row[0] if req_row else 1

cursor.execute("SELECT TOP 1 Id FROM Transactions")
tx_row = cursor.fetchone()
tx_id = tx_row[0] if tx_row else 1

cursor.execute("SELECT TOP 1 UserId FROM BusinessOwnerProfile WHERE IsDeleted=0")
bo_row = cursor.fetchone()
bo_id = bo_row[0] if bo_row else "11111111-1111-1111-1111-111111111101"

cursor.execute("SELECT TOP 1 Id FROM Products")
p_row = cursor.fetchone()
p_id = p_row[0] if p_row else 1

cursor.execute("SELECT TOP 1 Id FROM SupportTickets")
tk_row = cursor.fetchone()
tk_id = tk_row[0] if tk_row else 1

cursor.execute("SELECT TOP 1 Id FROM ProductReviews")
rv_row = cursor.fetchone()
rv_id = rv_row[0] if rv_row else 1

cursor.close()
conn.close()

print("Real IDs from DB:")
print(f"  req_id={req_id}, tx_id={tx_id}, bo_id={bo_id}, p_id={p_id}, tk_id={tk_id}, rv_id={rv_id}")
print()

BASE = "https://memo620-talentree-ai.hf.space"

# (method, path, use_post)
tests = [
    ("GET",  "/",                                     False),
    ("GET",  "/ai/status",                            False),
    ("GET",  "/ai/models/status",                     False),
    ("GET",  "/ai/dashboard/" + bo_id,                False),
    ("GET",  "/ai/analytics/revenue-trend/" + bo_id,  False),
    ("GET",  "/ai/reviews/trends/" + bo_id,           False),
    ("GET",  "/ai/benchmark/" + bo_id,                False),
    ("POST", "/ai/predict/churn/" + bo_id,            True),
    ("POST", "/ai/predict/fraud/" + str(req_id),      True),
    ("POST", "/ai/predict/anomaly/" + str(tx_id),     True),
    ("POST", "/ai/predict/sentiment/" + str(rv_id),   True),
    ("POST", "/ai/predict/triage/" + str(tk_id),      True),
    ("POST", "/ai/predict/demand/" + str(p_id),       True),
    ("POST", "/ai/compute/product/" + str(p_id),      True),
    ("POST", "/ai/compute/profile/" + bo_id,          True),
    ("GET",  "/ai/export/financial/" + bo_id,         False),
]

print("=" * 75)
print(f"{'Method':<6} {'Endpoint':<45} {'Status':>6}  Result")
print("=" * 75)

ok = fail = 0
for method, ep, is_post in tests:
    try:
        fn = requests.post if is_post else requests.get
        r = fn(BASE + ep, timeout=60)
        icon = "✓ OK" if r.status_code == 200 else "✗ FAIL"
        if r.status_code == 200:
            ok += 1
        else:
            fail += 1
        ct = r.headers.get("content-type", "")
        if "json" in ct:
            snippet = str(r.json())[:35]
        elif "csv" in ct or "pdf" in ct or "octet" in ct:
            snippet = f"[binary {len(r.content)} bytes]"
        else:
            snippet = r.text[:35] if r.text else "N/A"
        print(f"{method:<6} {ep:<45} {r.status_code:>6}  {snippet}")
    except Exception as e:
        fail += 1
        print(f"{method:<6} {ep:<45}    ERR  {str(e)[:35]}")

print("=" * 75)
print(f"PASSED: {ok}  |  FAILED: {fail}  |  TOTAL: {ok+fail}")
