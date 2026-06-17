"""
Talentree AI - Static JSON Seed Data Generator
Generates JSON files for each table WITHOUT needing a DB connection.
Backend team can use these to restore data after a database crash.
"""
import json, os, random, uuid
from datetime import datetime, timedelta

random.seed(42)  # Fixed seed = same data every time

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "for_backend_team")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── IDs matching db52715 ──────────────────────────────────────────────────────
BO_USER_IDS = [
    "11111111-1111-1111-1111-111111111101",
    "22222222-2222-2222-2222-222222222202",
    "33333333-3333-3333-3333-333333333303",
]

ALL_USER_IDS = [
    "05515c97-a07e-4e62-901d-7cbe371de8d7",
    "11111111-1111-1111-1111-111111111101",
    "22222222-2222-2222-2222-222222222202",
    "33333333-3333-3333-3333-333333333303",
    "3a9d3797-1d5c-4dc0-b4cb-bb33125c80a7",
    "791f91bd-8afb-4399-9cf5-26ce52b801d7",
    "b1402433-d75c-4a91-b4d1-d1f92abee781",
    "b65f6a9d-b5c0-41d8-93de-59b43a0e7b42",
    "c34f2835-56c0-4eef-8291-93f70b385ae1",
]

PRODUCT_IDS = list(range(1, 17))

def rand_dt(days_back_max=180, days_back_min=1):
    delta = random.randint(days_back_min, days_back_max)
    dt = datetime.now() - timedelta(days=delta)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")

def stripe_id():
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "pi_" + "".join(random.choices(chars, k=24))

def save(name, data):
    path = os.path.join(OUTPUT_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {name}.json  ->  {len(data)} rows  ({os.path.getsize(path)/1024:.1f} KB)")
    return data

# ── Generate each table ───────────────────────────────────────────────────────

def gen_transactions(count=1000):
    types   = ["Sale","Refund","Payout","Fee"]
    weights = [70, 10, 15, 5]
    rows = []
    for i in range(1, count + 1):
        bo = random.choice(BO_USER_IDS)
        t  = random.choices(types, weights=weights)[0]
        amount = round(random.uniform(50.0, 5000.0), 2)
        dt = rand_dt(180)
        is_anomaly = random.random() < 0.05
        score = round(random.uniform(0.7, 0.99), 2) if is_anomaly else round(random.uniform(0.01, 0.3), 2)
        rows.append({
            "BusinessOwnerId": bo,
            "Type": t,
            "Description": f"{t} transaction",
            "Amount": amount,
            "BalanceAfter": round(amount * random.randint(1, 10), 2),
            "ReferenceId": random.randint(1000, 999999),
            "ReferenceType": "Order" if t == "Sale" else "PayoutRequest" if t == "Payout" else "Other",
            "StripePaymentIntentId": stripe_id(),
            "AnomalyFlag": 1 if is_anomaly else 0,
            "AnomalyScore": score,
            "CreatedAt": dt,
            "UpdatedAt": dt,
            "CreatedBy": bo,
            "UpdatedBy": bo,
        })
    return save("Transactions", rows)


def gen_login_histories(count=3000):
    devices   = ["iPhone 14","Samsung Galaxy S23","MacBook Pro","Windows PC","iPad Pro","Huawei P50","OnePlus 11","Dell XPS"]
    locations = ["Cairo, Egypt","Alexandria, Egypt","Giza, Egypt","Riyadh, Saudi Arabia","Dubai, UAE","Mansoura, Egypt"]
    rows = []
    for _ in range(count):
        user = random.choice(ALL_USER_IDS)
        dt   = rand_dt(365)
        ip   = f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"
        rows.append({
            "UserId": user,
            "IpAddress": ip,
            "DeviceInfo": random.choice(devices),
            "Location": random.choice(locations),
            "LoginAt": dt,
            "IsSuccessful": 1 if random.random() > 0.1 else 0,
        })
    return save("LoginHistories", rows)


def gen_product_reviews(count=200):
    positive = ["Excellent product!", "Highly recommended!", "Amazing craftsmanship.", "Perfect item."]
    neutral  = ["Product is okay.", "Decent quality.", "Average product."]
    negative = ["Not as described.", "Very disappointed.", "Slow shipping."]
    rows = []
    for _ in range(count):
        prod   = random.choice(PRODUCT_IDS)
        customer = random.choice(ALL_USER_IDS)
        rating = random.choices([5,4,3,2,1], weights=[40,30,15,10,5])[0]
        text   = random.choice(positive if rating >= 4 else neutral if rating == 3 else negative)
        dt     = rand_dt(180)
        rows.append({
            "ProductId": prod,
            "CustomerUserId": customer,
            "CustomerName": f"User {customer[:4]}",
            "Rating": rating,
            "ReviewText": text,
            "IsAnonymous": 0,
            "SentimentScore": round(rating / 5.0, 4),
            "SentimentLabel": "Positive" if rating >= 4 else "Neutral" if rating == 3 else "Negative",
            "FlaggedToxic": 0,
            "CreatedAt": dt,
            "CreatedBy": customer,
            "UpdatedAt": dt,
            "UpdatedBy": customer,
        })
    return save("ProductReviews", rows)


def gen_support_tickets(count=100):
    # Category: 0=Payment,1=ProductQuality,2=Delivery,3=Account,4=Technical
    # Priority: 0=Low,1=Medium,2=High,3=Critical
    # Status:   0=Open,1=InProgress,2=Resolved,3=Closed
    rows = []
    for i in range(count):
        bo = random.choice(BO_USER_IDS)
        dt = rand_dt(180)
        rows.append({
            "BusinessOwnerUserId": bo,
            "Category": random.choice([0,1,2,3,4]),
            "Subject": f"Support Issue #{i+1}",
            "Description": "Customer needs help with this issue.",
            "Status": random.choice([0,1,2,3]),
            "Priority": random.choice([0,1,2,3]),
            "TicketNumber": f"TKT-{random.randint(10000,99999)}",
            "AutoCategory": None,
            "PriorityScore": None,
            "CreatedAt": dt,
            "CreatedBy": bo,
            "UpdatedAt": dt,
            "UpdatedBy": bo,
            "IsDeleted": 0,
        })
    return save("SupportTickets", rows)


def gen_ticket_messages(tickets):
    rows = []
    for i, ticket in enumerate(tickets):
        ticket_idx = i + 1  # placeholder ID (1-based)
        num_msgs = random.randint(1, 4)
        bo_id = ticket["BusinessOwnerUserId"]
        for j in range(num_msgs):
            dt = rand_dt(180)
            is_admin = j % 2 == 0
            sender = random.choice(ALL_USER_IDS) if is_admin else bo_id
            rows.append({
                "TicketId": f"<<SupportTickets[{ticket_idx}].Id>>",
                "Content": "Please see details.",
                "IsAdminMessage": 1 if is_admin else 0,
                "SenderId": sender,
                "EmailSent": 1,
                "CreatedAt": dt,
                "CreatedBy": sender,
                "UpdatedAt": dt,
                "UpdatedBy": sender,
            })
    return save("TicketMessages", rows)


def gen_onboarding_progress():
    rows = []
    for bo in BO_USER_IDS:
        rows.append({
            "BusinessOwnerId": bo,
            "TourCompleted": 1 if random.random() > 0.2 else 0,
            "ChecklistProductAdded": 1 if random.random() > 0.4 else 0,
            "ChecklistPaymentSet": 1 if random.random() > 0.5 else 0,
            "ChecklistProfileDone": 1 if random.random() > 0.1 else 0,
        })
    return save("OnboardingProgress", rows)


def gen_payout_requests():
    statuses = ["Pending","Approved","Processing","Completed","Rejected"]
    banks    = ["CIB Bank","NBE","Banque Misr","QNB Egypt","HSBC Egypt"]
    names    = ["Ahmed Hassan","Sara Mohamed","Omar Khalil","Nadia Ali"]
    rows = []
    for bo in BO_USER_IDS:
        for status in random.sample(statuses, random.randint(1, 3)):
            amount = round(random.uniform(500, 20000), 2)
            dt = rand_dt(120)
            rows.append({
                "BusinessOwnerId": bo,
                "Amount": amount,
                "Currency": "EGP",
                "Status": status,
                "BankName": random.choice(banks),
                "AccountHolderName": random.choice(names),
                "AccountIdentifierEnc": f"ENC_{random.randint(100000000,999999999)}",
                "RoutingSwiftCode": "XXXXXXXX",
                "CreatedAt": dt,
                "UpdatedAt": dt,
                "CreatedBy": bo,
                "UpdatedBy": bo,
            })
    return save("PayoutRequests", rows)


def gen_production_requests(count=200):
    statuses = ["Submitted","UnderReview","Quoted","Confirmed","InProduction","Completed","Rejected"]
    rows = []
    for i in range(count):
        bo = random.choice(BO_USER_IDS)
        status = random.choice(statuses)
        is_fraud = random.random() < 0.08
        f_score  = round(random.uniform(0.55, 0.95), 2) if is_fraud else round(random.uniform(0.0, 0.25), 2)
        dt = rand_dt(180)
        rows.append({
            "BusinessOwnerId": bo,
            "Title": f"Request {i}",
            "Notes": "Notes...",
            "Status": status,
            "QuotedPrice": random.randint(100, 5000),
            "EstimatedCompletionDate": dt,
            "CompletedAt": dt if status == "Completed" else None,
            "FraudScore": f_score,
            "IsFraudFlag": 1 if is_fraud else 0,
            "PaymentStatus": "Paid",
            "CreatedAt": dt,
            "UpdatedAt": dt,
            "CreatedBy": bo,
            "UpdatedBy": bo,
        })
    return save("BoProductionRequests", rows)


def gen_product_stats():
    rows = []
    for pid in PRODUCT_IDS:
        rows.append({
            "Id": pid,
            "_note": "UPDATE only — do not INSERT. These are stats to apply to existing Products rows.",
            "ViewCount": random.randint(150, 3000),
            "CartAddCount": random.randint(20, 400),
            "PurchaseCount": random.randint(10, 150),
            "RevenueTotal": round(random.uniform(500, 5000), 2),
            "AvgRating": round(random.uniform(3.5, 5.0), 1),
        })
    return save("Products_stats_update", rows)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Talentree AI - JSON Seed Data Generator")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)

    gen_transactions(1000)
    gen_login_histories(3000)
    gen_product_reviews(200)
    tickets = gen_support_tickets(100)
    gen_ticket_messages(tickets)
    gen_onboarding_progress()
    gen_payout_requests()
    gen_production_requests(200)
    gen_product_stats()

    print("\n  [NOTE] for Backend Team:")
    print("  - TicketMessages.TicketId uses <<SupportTickets[N].Id>> placeholders")
    print("    - Insert SupportTickets first, then map real IDs to TicketMessages")
    print("  - Products_stats_update.json -> run UPDATE not INSERT")
    print("=" * 60)
    print("  [DONE] All JSON files saved to: for_backend_team/")
    print("=" * 60)

if __name__ == "__main__":
    main()
