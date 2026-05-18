"""
Talentree AI - Synthetic Data Seed Generator
=============================================
Generates realistic data matching the exact DB schema and INSERTs it
into the deployed database. Uses real FK IDs pulled from the DB.

Resumes from where it left off:
  - Transactions: already done (1000 rows)
  - LoginHistories: already done (3000 rows)
  - ProductReviews: FIXED - removed CreatedAt/UpdatedAt/CreatedBy
  - SupportTickets: FIXED - removed CreatedAt/UpdatedAt/CreatedBy
  - TicketMessages: FIXED - removed CreatedAt/UpdatedAt/CreatedBy
  - OnboardingProgress: FIXED - removed CreatedAt/UpdatedAt/CreatedBy
  - PayoutRequests: has audit columns - OK
  - BoProductionRequests: has audit columns - OK
  - Products: UPDATE only
  - AspNetUsers: UPDATE only
"""

import pyodbc
import random
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONNECTION

# -- Real IDs pulled from DB -----------------------------------------------

BO_USER_IDS = [
    "ddeeb941-52cc-44b4-abac-6218be47ee40",
    "c07bfde7-e0fd-40ee-905f-7deca56fe4f6",
    "063be7d9-abe4-484e-a2ad-c467146eb062",
    "288dabd0-9a20-4a7a-9e2b-3c1c40e73d23",
    "f9e95d18-ccd2-46b8-95b8-9785ebaedff5",
    "11111111-1111-1111-1111-111111111101",
    "22222222-2222-2222-2222-222222222202",
    "33333333-3333-3333-3333-333333333303",
]

ALL_USER_IDS = [
    "063be7d9-abe4-484e-a2ad-c467146eb062",
    "11111111-1111-1111-1111-111111111101",
    "22222222-2222-2222-2222-222222222202",
    "288dabd0-9a20-4a7a-9e2b-3c1c40e73d23",
    "33333333-3333-3333-3333-333333333303",
    "3937727a-1e99-42ca-9ed3-cfb2bc9a6fb0",
    "876888eb-4501-44c0-9b38-fbdfb1b98c56",
    "c07bb942-ebb3-42b9-a6c2-7a5d03ccc4b2",
    "c07bfde7-e0fd-40ee-905f-7deca56fe4f6",
    "ddeeb941-52cc-44b4-abac-6218be47ee40",
    "e3a7cea7-4877-4785-80b6-39ad8de90c19",
    "f9e95d18-ccd2-46b8-95b8-9785ebaedff5",
    "fc5f5185-c651-4a3d-9262-55a977d2861a",
    "ff9c889a-5024-4ca0-9b94-65d29e407eb8",
]

PRODUCT_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
PRODUCT_PRICES = {1: 189.99, 2: 149.99, 3: 229.99, 4: 275.00,
                  5: 199.99, 6: 159.99, 7: 349.99, 8: 120.00,
                  9: 149.99, 10: 199.99, 11: 129.99, 12: 259.99}

# -- Helpers ----------------------------------------------------------------

def rand_date(days_back_max=180, days_back_min=1):
    delta = random.randint(days_back_min, days_back_max)
    return datetime.now() - timedelta(days=delta)

def rand_datetime_str(days_back_max=180, days_back_min=1):
    return rand_date(days_back_max, days_back_min).strftime("%Y-%m-%d %H:%M:%S")

def stripe_id():
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "pi_" + "".join(random.choices(chars, k=24))

def get_connection():
    return pyodbc.connect(DB_CONNECTION)

# -- Seed Functions (RESUME - skip already done) ----------------------------

def seed_product_reviews(cursor, count=200):
    """ProductReviews: NO CreatedAt/UpdatedAt/CreatedBy columns"""
    print(f"Seeding {count} ProductReviews...")
    positive_reviews = [
        "Excellent product! Exceeded my expectations completely.",
        "Very high quality, fast delivery. Highly recommended!",
        "Amazing craftsmanship, worth every penny.",
        "Perfect item, exactly as described. Will buy again.",
        "Outstanding quality. The seller is very professional.",
        "Great product, beautiful design and fast shipping.",
        "Love it! Will definitely order again from this seller.",
        "Premium quality materials, very satisfied with purchase.",
    ]
    neutral_reviews = [
        "Product is okay, as expected. Nothing special.",
        "Decent quality for the price. Average experience.",
        "It is fine. Could be better packaging.",
        "Acceptable. Arrived on time. Nothing outstanding.",
        "Average product. Not bad but not great either.",
    ]
    negative_reviews = [
        "Not as described. Quality is disappointing.",
        "Packaging was damaged on arrival. Poor experience.",
        "Expected better quality for this price.",
        "Took too long to deliver. Product quality is average.",
        "Would not recommend. Very poor quality materials.",
        "Disappointed with this purchase. Will not buy again.",
    ]
    sql = """INSERT INTO ProductReviews
             (ProductId, CustomerUserId, CustomerName, Rating, ReviewText,
              IsAnonymous, SentimentScore, SentimentLabel, FlaggedToxic)
             VALUES (?,?,?,?,?,?,?,?,?)"""
    customer_names = ["Ahmed Hassan", "Sara Mohamed", "Omar Khalil", "Nadia Ali",
                      "Youssef Ibrahim", "Mariam Samir", "Karim Taha", "Layla Nour",
                      "Tarek Mostafa", "Hana Adel", "Amr Fathy", "Dina Osama"]
    inserted = 0
    for _ in range(count):
        product_id = random.choice(PRODUCT_IDS)
        customer_id = random.choice(ALL_USER_IDS)
        rating = random.choices([1, 2, 3, 4, 5], weights=[3, 5, 12, 35, 45])[0]
        if rating >= 4:
            review_text = random.choice(positive_reviews)
            sentiment_score = round(random.uniform(0.4, 0.95), 2)
            sentiment_label = "Positive"
        elif rating == 3:
            review_text = random.choice(neutral_reviews)
            sentiment_score = round(random.uniform(-0.1, 0.4), 2)
            sentiment_label = "Neutral"
        else:
            review_text = random.choice(negative_reviews)
            sentiment_score = round(random.uniform(-0.95, -0.1), 2)
            sentiment_label = "Negative"
        is_anonymous = 1 if random.random() < 0.1 else 0
        cursor.execute(sql, (
            product_id, customer_id,
            random.choice(customer_names),
            rating, review_text, is_anonymous,
            sentiment_score, sentiment_label, 0
        ))
        inserted += 1
    print(f"  [OK] Inserted {inserted} ProductReviews")


def seed_support_tickets(cursor, count=100):
    """SupportTickets: NO CreatedAt/UpdatedAt/CreatedBy columns"""
    print(f"Seeding {count} SupportTickets...")
    categories = ["Technical", "Account", "Payment", "Other"]
    statuses = ["Open", "InProgress", "Resolved", "Closed"]
    priorities = ["Low", "Medium", "High", "Urgent"]
    subjects = {
        "Technical": ["App not loading correctly", "Dashboard shows wrong data",
                      "Cannot upload product images", "Login page error",
                      "Product search not working", "Page timeout error"],
        "Account": ["Cannot reset password", "Email verification issue",
                    "Profile update not saving", "Account suspended incorrectly",
                    "Login issues on mobile", "Profile settings not working"],
        "Payment": ["Payment failed for order", "Refund not received yet",
                    "Wrong amount charged", "Payout request pending",
                    "Bank transfer not showing", "Payment gateway error"],
        "Other": ["How to add new product?", "Shipping options available",
                  "Partnership inquiry", "General question about platform",
                  "Feature request for dashboard"],
    }
    sql = """INSERT INTO SupportTickets
             (UserId, UserType, Category, Subject, Status, Priority,
              PriorityScore, AutoCategory)
             VALUES (?,?,?,?,?,?,?,?)"""
    inserted = 0
    for _ in range(count):
        user_id = random.choice(BO_USER_IDS)
        category = random.choice(categories)
        status = random.choices(statuses, weights=[30, 25, 30, 15])[0]
        priority = random.choices(priorities, weights=[20, 40, 30, 10])[0]
        priority_score = {"Low": round(random.uniform(0.1, 0.3), 2),
                          "Medium": round(random.uniform(0.3, 0.6), 2),
                          "High": round(random.uniform(0.6, 0.8), 2),
                          "Urgent": round(random.uniform(0.8, 0.99), 2)}[priority]
        subject = random.choice(subjects[category])
        cursor.execute(sql, (
            user_id, "BusinessOwner", category, subject,
            status, priority, priority_score, category
        ))
        inserted += 1
    print(f"  [OK] Inserted {inserted} SupportTickets")


def seed_ticket_messages(cursor):
    """TicketMessages: NO CreatedAt/UpdatedAt/CreatedBy columns"""
    print("Seeding TicketMessages...")
    cursor.execute("SELECT Id, UserId FROM SupportTickets")
    tickets = cursor.fetchall()
    admin_messages = [
        "Thank you for contacting us. Could you provide more details?",
        "We are looking into this issue for you.",
        "This has been resolved. Please let us know if you need further help.",
        "We apologize for the inconvenience. The issue is being escalated.",
    ]
    user_messages = [
        "I am still experiencing the same problem.",
        "Thank you for the quick response!",
        "When will this be fixed?",
        "The issue has been resolved. Thank you!",
        "Can you please check again?",
        "I need urgent help with this.",
    ]
    sql = """INSERT INTO TicketMessages
             (TicketId, SenderType, Message)
             VALUES (?,?,?)"""
    inserted = 0
    for ticket in tickets:
        ticket_id = ticket[0]
        num_messages = random.randint(1, 5)
        for j in range(num_messages):
            sender = "BusinessOwner" if j % 2 == 0 else "Admin"
            msg = random.choice(user_messages if sender == "BusinessOwner" else admin_messages)
            cursor.execute(sql, (ticket_id, sender, msg))
            inserted += 1
    print(f"  [OK] Inserted {inserted} TicketMessages")


def seed_onboarding_progress(cursor):
    """OnboardingProgress: NO CreatedAt/UpdatedAt/CreatedBy columns"""
    print("Seeding OnboardingProgress (1 per BO)...")
    sql = """INSERT INTO OnboardingProgress
             (BusinessOwnerId, TourCompleted, ChecklistProductAdded,
              ChecklistPaymentSet, ChecklistProfileDone)
             VALUES (?,?,?,?,?)"""
    cursor.execute("SELECT BusinessOwnerId FROM OnboardingProgress")
    existing = {row[0] for row in cursor.fetchall()}
    inserted = 0
    for bo_id in BO_USER_IDS:
        if bo_id in existing:
            continue
        tour = random.random() > 0.3
        product = random.random() > 0.2
        payment = random.random() > 0.5
        profile = random.random() > 0.15
        cursor.execute(sql, (
            bo_id,
            1 if tour else 0,
            1 if product else 0,
            1 if payment else 0,
            1 if profile else 0,
        ))
        inserted += 1
    print(f"  [OK] Inserted {inserted} OnboardingProgress rows")


def seed_payout_requests(cursor, count=50):
    """PayoutRequests: HAS CreatedAt/UpdatedAt/CreatedBy columns"""
    print(f"Seeding {count} PayoutRequests...")
    statuses = ["Pending", "Approved", "Processing", "Completed", "Rejected"]
    banks = ["CIB Bank", "NBE - National Bank of Egypt", "Banque Misr",
             "QNB Egypt", "HSBC Egypt", "Faisal Islamic Bank"]
    sql = """INSERT INTO PayoutRequests
             (BusinessOwnerId, Amount, Currency, Status,
              BankName, AccountHolderName, AccountIdentifierEnc,
              RoutingSwiftCode, CreatedAt, UpdatedAt, CreatedBy)
             VALUES (?,?,?,?,?,?,?,?,?,?,?)"""
    names = ["Ahmed Hassan", "Sara Mohamed", "Omar Khalil", "Nadia Ali", "Karim Taha"]
    inserted = 0
    for _ in range(count):
        bo_id = random.choice(BO_USER_IDS)
        amount = round(random.uniform(500, 20000), 2)
        status = random.choices(statuses, weights=[30, 20, 15, 25, 10])[0]
        bank = random.choice(banks)
        created = rand_datetime_str(120, 1)
        cursor.execute(sql, (
            bo_id, amount, "EGP", status,
            bank, random.choice(names),
            f"ENC_{random.randint(100000000, 999999999)}",
            "XXXXXXXX",
            created, created, bo_id
        ))
        inserted += 1
    print(f"  [OK] Inserted {inserted} PayoutRequests")


def seed_production_requests(cursor, count=200):
    """BoProductionRequests: HAS CreatedAt/UpdatedAt/CreatedBy columns"""
    print(f"Seeding {count} more BoProductionRequests...")
    statuses = ["Submitted", "UnderReview", "Quoted", "Confirmed",
                "InProduction", "Completed", "Rejected", "Cancelled"]
    weights = [15, 15, 10, 10, 15, 25, 5, 5]
    titles = [
        "Summer Abaya Collection - 200 Units", "Linen Dress Set - Spring Line",
        "Embroidered Hijabs - Eid Collection", "Leather Handbags - Limited Run",
        "Cotton Casual Shirts - 150 Units", "Modest Swimwear - 100 Units",
        "Scented Candle Gift Sets - 500 Units", "Macrame Wall Art - Large Format",
        "Resin Jewellery Collection - 200 Pieces", "Handmade Clay Pots - 150 Units",
        "Argan Oil Hair Serum - 300 Bottles", "Rose Water Toner - 500 Units",
        "Shea Body Butter - 400 Jars", "Natural Soap Bars Collection - 600 Units",
        "Vitamin C Face Serum - 250 Bottles", "Herbal Face Mask - 200 Units",
        "Coconut Hair Mask - 300 Jars", "Lavender Bath Salts - 450 Bags",
        "Printed Scarves - 300 Units", "Personalized Gift Boxes - 300 Units",
        "Wooden Photo Frames - 100 Units", "Dried Flower Arrangements - 200 Units",
        "Vintage Denim Jackets - 80 Units", "Hand-painted Ceramics - 80 Units",
    ]
    sql = """INSERT INTO BoProductionRequests
             (BusinessOwnerId, Title, Notes, Status, QuotedPrice,
              EstimatedCompletionDate, CompletedAt,
              IsFraudFlag, FraudScore, PaymentStatus,
              CreatedAt, UpdatedAt, CreatedBy)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    inserted = 0
    for _ in range(count):
        bo_id = random.choice(BO_USER_IDS)
        title = random.choice(titles) + f" #{random.randint(100,999)}"
        status = random.choices(statuses, weights=weights)[0]
        is_fraud = random.random() < 0.08
        fraud_score = round(random.uniform(0.55, 0.95), 2) if is_fraud else round(random.uniform(0.0, 0.25), 2)
        quoted = round(random.uniform(2000, 50000), 2) if status not in ("Submitted", "UnderReview") else None
        created_dt = rand_date(180, 7)
        created = created_dt.strftime("%Y-%m-%d %H:%M:%S")
        est_complete = None
        completed_at = None
        if status in ("Confirmed", "InProduction", "Completed"):
            est_complete = (created_dt + timedelta(days=random.randint(14, 60))).strftime("%Y-%m-%d %H:%M:%S")
        if status == "Completed":
            completed_at = (created_dt + timedelta(days=random.randint(10, 50))).strftime("%Y-%m-%d %H:%M:%S")
        payment_status = "Paid" if status == "Completed" and random.random() > 0.3 else "Unpaid"
        cursor.execute(sql, (
            bo_id, title, "Production request for seasonal collection.",
            status, quoted, est_complete, completed_at,
            1 if is_fraud else 0, fraud_score,
            payment_status, created, created, bo_id
        ))
        inserted += 1
    print(f"  [OK] Inserted {inserted} BoProductionRequests")


def update_products(cursor):
    print("Updating Products with realistic view/purchase counts...")
    for product_id, price in PRODUCT_PRICES.items():
        view_count = random.randint(150, 3000)
        cart_count = random.randint(20, 400)
        purchase_count = random.randint(10, 150)
        revenue_total = round(price * purchase_count, 2)
        avg_rating = round(random.uniform(3.5, 5.0), 1)
        cursor.execute("""
            UPDATE Products
            SET ViewCount = ?, CartAddCount = ?, PurchaseCount = ?,
                RevenueTotal = ?, AvgRating = ?
            WHERE Id = ?
        """, (view_count, cart_count, purchase_count, revenue_total, avg_rating, product_id))
    print(f"  [OK] Updated {len(PRODUCT_PRICES)} Products")


def update_users_login_count(cursor):
    print("Updating AspNetUsers.LoginCount...")
    for user_id in ALL_USER_IDS:
        login_count = random.randint(1, 200)
        cursor.execute("UPDATE AspNetUsers SET LoginCount = ? WHERE Id = ?",
                       (login_count, user_id))
    print(f"  [OK] Updated {len(ALL_USER_IDS)} users LoginCount")


# -- Main (RESUME - skip already completed steps) --------------------------

def run_resume():
    print("=" * 60)
    print("  Talentree AI - Seed Generator (RESUME)")
    print("  Skipping: Transactions (1000 done), LoginHistories (3000 done)")
    print("  Running: Reviews, Tickets, Messages, Onboarding, Payouts,")
    print("           ProdRequests, Products UPDATE, Users UPDATE")
    print("=" * 60)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # SKIP: Transactions (1000 already inserted)
        # SKIP: LoginHistories (3000 already inserted)

        seed_product_reviews(cursor, 200)
        conn.commit()
        print("  >> Committed ProductReviews")

        seed_support_tickets(cursor, 100)
        conn.commit()
        print("  >> Committed SupportTickets")

        seed_ticket_messages(cursor)
        conn.commit()
        print("  >> Committed TicketMessages")

        seed_onboarding_progress(cursor)
        conn.commit()
        print("  >> Committed OnboardingProgress")

        seed_payout_requests(cursor, 50)
        conn.commit()
        print("  >> Committed PayoutRequests")

        seed_production_requests(cursor, 200)
        conn.commit()
        print("  >> Committed BoProductionRequests")

        update_products(cursor)
        conn.commit()
        print("  >> Committed Products UPDATE")

        update_users_login_count(cursor)
        conn.commit()
        print("  >> Committed AspNetUsers UPDATE")

        print("=" * 60)
        print("  [OK] ALL SEEDING COMPLETE!")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_resume()
