"""
Talentree AI - EXTRA Seed Data Generator (ML Model Improvement)
================================================================
Generates ADDITIONAL rows targeting ML model training quality.

What this adds:
  - AspNetUsers:          40 extra regular users (total -> ~50 users for churn)
  - LoginHistories:       2000 extra logins for new users
  - BoProductionRequests: 800 extra requests with 15% fraud rate (was 8%)
                          -> gives model ~120+ real fraud rows to train on
  - ProductReviews:       300 extra reviews for more sentiment data

Backend: INSERT these AFTER the existing rows (no conflict with existing IDs).
"""

import json, os, random, uuid
from datetime import datetime, timedelta

random.seed(99)  # Different seed from original (42)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "for_backend_team_extra")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Existing IDs already in DB (do NOT re-insert these) ──────────────────────
EXISTING_USER_IDS = [
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

BO_USER_IDS = [
    "11111111-1111-1111-1111-111111111101",
    "22222222-2222-2222-2222-222222222202",
    "33333333-3333-3333-3333-333333333303",
]

PRODUCT_IDS = list(range(1, 17))

# ── 40 new regular user IDs (stable, not Guid.NewGuid()) ─────────────────────
NEW_USER_IDS = [f"aaaaaaaa-{str(i).zfill(4)}-4000-8000-{str(i*7).zfill(12)}" for i in range(1, 41)]

# All users combined (existing + new) for references
ALL_USER_IDS = EXISTING_USER_IDS + NEW_USER_IDS


def rand_dt(days_back_max=365, days_back_min=1):
    delta = random.randint(days_back_min, days_back_max)
    dt = datetime.now() - timedelta(days=delta)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def save(name, data):
    path = os.path.join(OUTPUT_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {name}.json  ->  {len(data)} rows  ({os.path.getsize(path)/1024:.1f} KB)")
    return data


# ── 1. New AspNetUsers ────────────────────────────────────────────────────────
def gen_new_users():
    """40 new regular (non-BO) users with realistic login counts."""
    first_names = ["Ahmed","Sara","Omar","Nadia","Youssef","Hana","Karim","Lina",
                   "Hassan","Dina","Tarek","Rania","Mostafa","Amira","Khaled","Eman",
                   "Mohamed","Nour","Amir","Salma","Wael","Mona","Samy","Layla",
                   "Tamer","Heba","Ashraf","Yasmin","Sherif","Mariam","Fady","Rana",
                   "Adel","Sherine","Bassem","Nevine","Gamal","Doaa","Alaa","Ghada"]
    last_names  = ["Hassan","Mohamed","Ali","Ahmed","Ibrahim","Mahmoud","Khalil",
                   "Omar","Saad","Nasser","Farouk","Mansour","Abdel","Salem","Gaber"]
    rows = []
    for i, uid in enumerate(NEW_USER_IDS):
        fname = first_names[i % len(first_names)]
        lname = last_names[i % len(last_names)]
        email = f"{fname.lower()}.{lname.lower()}{i}@talentree.test"
        login_count = random.randint(5, 120)
        created = rand_dt(400, 30)
        # Simulate churn patterns: 30% of new users are "churned" (low activity)
        is_churned = random.random() < 0.30
        last_login = rand_dt(90, 61) if is_churned else rand_dt(30, 1)
        rows.append({
            "Id": uid,
            "UserName": email,
            "NormalizedUserName": email.upper(),
            "Email": email,
            "NormalizedEmail": email.upper(),
            "EmailConfirmed": 1,
            "PasswordHash": "AQAAAAEAACcQAAAAEPlaceholderHashForTestUser==",
            "SecurityStamp": str(uuid.uuid4()),
            "ConcurrencyStamp": str(uuid.uuid4()),
            "PhoneNumber": f"+20100{random.randint(1000000,9999999)}",
            "PhoneNumberConfirmed": 1,
            "TwoFactorEnabled": 0,
            "LockoutEnabled": 1,
            "LockoutEnd": None,
            "AccessFailedCount": 0,
            "FirstName": fname,
            "LastName": lname,
            "UserType": "Customer",
            "IsActive": 1,
            "IsDeleted": 0,
            "ChurnRiskScore": None,
            "ChurnRiskUpdatedAt": None,
            "LoginCount": login_count,
            "LastLoginAt": last_login,
            "ProfilePictureUrl": None,
            "CreatedAt": created,
            "UpdatedAt": created,
        })
    return save("AspNetUsers_extra", rows)


# ── 2. Login Histories for new users ─────────────────────────────────────────
def gen_extra_login_histories(new_users, count=2000):
    """2000 login history entries for the 40 new users."""
    devices   = ["iPhone 14","Samsung Galaxy S23","MacBook Pro","Windows PC",
                 "iPad Pro","Huawei P50","OnePlus 11","Dell XPS","Xiaomi 12"]
    locations = ["Cairo, Egypt","Alexandria, Egypt","Giza, Egypt",
                 "Riyadh, Saudi Arabia","Dubai, UAE","Mansoura, Egypt",
                 "Tanta, Egypt","Aswan, Egypt","Luxor, Egypt"]
    rows = []
    for _ in range(count):
        user = random.choice(NEW_USER_IDS)
        dt   = rand_dt(365, 1)
        ip   = f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        rows.append({
            "UserId": user,
            "IpAddress": ip,
            "DeviceInfo": random.choice(devices),
            "Location": random.choice(locations),
            "LoginAt": dt,
            "IsSuccessful": 1 if random.random() > 0.08 else 0,
        })
    return save("LoginHistories_extra", rows)


# ── 3. Extra Production Requests (HIGH fraud rate for model) ──────────────────
def gen_extra_production_requests(count=800):
    """800 extra requests with 15% fraud rate (was 8%) for better fraud F1."""
    statuses = ["Submitted","UnderReview","Quoted","Confirmed",
                "InProduction","Completed","Rejected","Cancelled"]
    weights  = [10, 15, 15, 20, 15, 15, 5, 5]
    payment_statuses = ["Paid","Unpaid","PartiallyPaid","Refunded"]
    pay_weights      = [60, 20, 10, 10]

    rows = []
    for i in range(count):
        bo       = random.choice(BO_USER_IDS)
        status   = random.choices(statuses, weights=weights)[0]
        pay_stat = random.choices(payment_statuses, weights=pay_weights)[0]

        # 15% fraud rate — gives 120 fraud rows for training
        is_fraud = random.random() < 0.15
        f_score  = round(random.uniform(0.60, 0.98), 2) if is_fraud else round(random.uniform(0.01, 0.30), 2)

        # Fraud pattern: high price + unpaid + unusual hour
        if is_fraud:
            price     = random.randint(3000, 9999)
            pay_stat  = random.choices(["Unpaid","PartiallyPaid"], weights=[70,30])[0]
            title_len = random.randint(5, 20)   # very short title is suspicious
        else:
            price     = random.randint(100, 3000)
            title_len = random.randint(20, 80)

        dt = rand_dt(365, 1)

        rows.append({
            "BusinessOwnerId": bo,
            "Title": f"{'X'*title_len if is_fraud else f'Production Order Extra {i}'}",
            "Notes": None if (is_fraud and random.random() < 0.5) else "Detailed production notes included.",
            "Status": status,
            "QuotedPrice": price,
            "EstimatedCompletionDate": rand_dt(30, 1),
            "CompletedAt": dt if status == "Completed" else None,
            "FulfillmentHours": round(random.uniform(1, 168), 1),
            "FraudScore": f_score,
            "IsFraudFlag": 1 if is_fraud else 0,
            "PaymentStatus": pay_stat,
            "CreatedAt": dt,
            "UpdatedAt": dt,
            "CreatedBy": bo,
            "UpdatedBy": bo,
            "IsDeleted": 0,
        })

    fraud_count = sum(1 for r in rows if r["IsFraudFlag"] == 1)
    result = save("BoProductionRequests_extra", rows)
    print(f"         -> Fraud rows: {fraud_count}/{count} ({100*fraud_count//count}%)")
    return result


# ── 4. Extra Product Reviews ──────────────────────────────────────────────────
def gen_extra_product_reviews(count=300):
    """300 extra reviews across all products and new users."""
    positive = [
        "Excellent quality! Very satisfied.",
        "Highly recommended to everyone.",
        "Amazing craftsmanship, worth every penny.",
        "Perfect product, fast delivery.",
        "Outstanding quality and finish.",
        "Absolutely love this product!",
    ]
    neutral = [
        "Product is okay, nothing special.",
        "Decent quality for the price.",
        "Average product, could be better.",
        "Does what it says, nothing more.",
    ]
    negative = [
        "Not as described in the listing.",
        "Very disappointed with quality.",
        "Slow shipping and poor packaging.",
        "Would not recommend this product.",
        "Quality is below expectations.",
    ]
    rows = []
    for _ in range(count):
        prod     = random.choice(PRODUCT_IDS)
        customer = random.choice(ALL_USER_IDS)
        rating   = random.choices([5,4,3,2,1], weights=[35,30,15,12,8])[0]
        text     = random.choice(positive if rating >= 4 else neutral if rating == 3 else negative)
        dt       = rand_dt(365, 1)
        rows.append({
            "ProductId": prod,
            "CustomerUserId": customer,
            "CustomerName": f"User-{customer[:6]}",
            "Rating": rating,
            "ReviewText": text,
            "IsAnonymous": 1 if random.random() < 0.15 else 0,
            "SentimentScore": None,
            "SentimentLabel": None,
            "FlaggedToxic": 0,
            "CreatedAt": dt,
            "CreatedBy": customer,
            "UpdatedAt": dt,
            "UpdatedBy": customer,
        })
    return save("ProductReviews_extra", rows)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  Talentree AI - EXTRA Seed Data (ML Model Improvement)")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 65)
    print()
    print("  Target improvements:")
    print("  - Churn model: 40 new users with varied churn patterns")
    print("  - Fraud model: 800 requests @ 15% fraud rate (~120 fraud rows)")
    print("  - Sentiment:   300 extra reviews")
    print()

    new_users = gen_new_users()
    gen_extra_login_histories(new_users)
    gen_extra_production_requests(800)
    gen_extra_product_reviews(300)

    print()
    print("=" * 65)
    print("  [INSTRUCTIONS FOR BACKEND TEAM]")
    print()
    print("  Insert order (to avoid FK violations):")
    print("  1. AspNetUsers_extra.json       -> INSERT into AspNetUsers")
    print("  2. LoginHistories_extra.json    -> INSERT into LoginHistories")
    print("  3. BoProductionRequests_extra.json -> INSERT into BoProductionRequests")
    print("  4. ProductReviews_extra.json    -> INSERT into ProductReviews")
    print()
    print("  After insert, call: POST /ai/train/all")
    print("  This retrains all models on the expanded dataset.")
    print("=" * 65)
    print("  [DONE] Files saved to: data/for_backend_team_extra/")
    print("=" * 65)


if __name__ == "__main__":
    main()
