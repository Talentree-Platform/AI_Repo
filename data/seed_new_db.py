"""
Talentree AI - Full Seed for NEW Database (db52715)
Updated to match the new database schema exactly.
"""
import pyodbc
import random
import sys
import os
import uuid
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONNECTION

# ── Real IDs from db52715 ────────────────────────────────────────────────────
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

# ── Helpers ──────────────────────────────────────────────────────────────────
def rand_date(days_back_max=180, days_back_min=1):
    delta = random.randint(days_back_min, days_back_max)
    return datetime.now() - timedelta(days=delta)

def rand_dt(days_back_max=180, days_back_min=1):
    return rand_date(days_back_max, days_back_min).strftime("%Y-%m-%d %H:%M:%S")

def stripe_id():
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "pi_" + "".join(random.choices(chars, k=24))

def get_connection():
    return pyodbc.connect(DB_CONNECTION)

# ── Seed Functions ────────────────────────────────────────────────────────────

def seed_transactions(cursor, count=1000):
    print(f"Seeding {count} Transactions...")
    types = ["Sale", "Refund", "Payout", "Fee"]
    weights = [70, 10, 15, 5]
    sql = """INSERT INTO Transactions
             (BusinessOwnerId, Type, Description, Amount, BalanceAfter,
              ReferenceId, ReferenceType, StripePaymentIntentId,
              AnomalyFlag, AnomalyScore, CreatedAt, UpdatedAt, CreatedBy, UpdatedBy)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    for _ in range(count):
        bo = random.choice(BO_USER_IDS)
        amount = round(random.uniform(50.0, 5000.0), 2)
        t = random.choices(types, weights=weights)[0]
        dt = rand_dt(180, 1)
        ref_id = random.randint(1000, 999999)
        ref_type = "Order" if t == "Sale" else "PayoutRequest" if t == "Payout" else "Other"
        is_anomaly = random.random() < 0.05
        score = round(random.uniform(0.7, 0.99), 2) if is_anomaly else round(random.uniform(0.01, 0.3), 2)
        
        cursor.execute(sql, (
            bo, t, f"{t} transaction", amount, amount * random.randint(1, 10),
            ref_id, ref_type, stripe_id(),
            1 if is_anomaly else 0, score, dt, dt, bo, bo
        ))
    print(f"  [OK] Inserted {count} Transactions")


def seed_login_histories(cursor, count=3000):
    print(f"Seeding {count} LoginHistories...")
    devices = ["iPhone 14", "Samsung Galaxy S23", "MacBook Pro", "Windows PC",
               "iPad Pro", "Huawei P50", "OnePlus 11", "Dell XPS"]
    locations = ["Cairo, Egypt", "Alexandria, Egypt", "Giza, Egypt",
                 "Riyadh, Saudi Arabia", "Dubai, UAE", "Mansoura, Egypt"]
    sql = """INSERT INTO LoginHistories
             (UserId, IpAddress, DeviceInfo, Location, LoginAt, IsSuccessful)
             VALUES (?,?,?,?,?,?)"""
    for _ in range(count):
        user = random.choice(ALL_USER_IDS)
        dt = rand_dt(365, 1)
        ip = f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"
        cursor.execute(sql, (user, ip, random.choice(devices), random.choice(locations),
                             dt, 1 if random.random() > 0.1 else 0))
    print(f"  [OK] Inserted {count} LoginHistories")


def seed_product_reviews(cursor, count=200):
    print(f"Seeding {count} ProductReviews...")
    positive = ["Excellent product!", "Highly recommended!", "Amazing craftsmanship.", "Perfect item."]
    neutral = ["Product is okay.", "Decent quality.", "Average product."]
    negative = ["Not as described.", "Very disappointed.", "Slow shipping."]
    
    sql = """INSERT INTO ProductReviews
             (ProductId, CustomerUserId, CustomerName, Rating, ReviewText,
              IsAnonymous, SentimentScore, SentimentLabel, FlaggedToxic,
              CreatedAt, CreatedBy, UpdatedAt, UpdatedBy)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    inserted = 0
    for _ in range(count):
        prod = random.choice(PRODUCT_IDS)
        customer = random.choice(ALL_USER_IDS)
        rating = random.choices([5, 4, 3, 2, 1], weights=[40, 30, 15, 10, 5])[0]
        review_text = random.choice(positive if rating >= 4 else neutral if rating == 3 else negative)
        sentiment_score = rating / 5.0
        sentiment_label = "Positive" if rating >= 4 else "Neutral" if rating == 3 else "Negative"
        dt = rand_dt(180, 1)
        
        cursor.execute(sql, (
            prod, customer, f"User {customer[:4]}", rating, review_text,
            0, sentiment_score, sentiment_label, 0,
            dt, customer, dt, customer
        ))
        inserted += 1
    print(f"  [OK] Inserted {inserted} ProductReviews")


def seed_support_tickets(cursor, count=100):
    print(f"Seeding {count} SupportTickets...")
    # Category: 0=Payment, 1=ProductQuality, 2=Delivery, 3=Account, 4=Technical
    categories = [0, 1, 2, 3, 4]
    # Priority: 0=Low, 1=Medium, 2=High, 3=Critical
    priorities = [0, 1, 2, 3]
    # Status: 0=Open, 1=InProgress, 2=Resolved, 3=Closed
    statuses = [0, 1, 2, 3]

    sql = """INSERT INTO SupportTickets
             (BusinessOwnerUserId, Category, Subject, Description, Status, Priority,
              TicketNumber, CreatedAt, CreatedBy, UpdatedAt, UpdatedBy, IsDeleted)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"""

    for i in range(count):
        bo = random.choice(BO_USER_IDS)
        dt = rand_dt(180, 1)
        ticket_num = f"TKT-{random.randint(10000,99999)}"

        cursor.execute(sql, (
            bo, random.choice(categories),
            f"Support Issue #{i+1}", "Customer needs help with this issue.",
            random.choice(statuses), random.choice(priorities),
            ticket_num, dt, bo, dt, bo, 0
        ))
    print(f"  [OK] Inserted {count} SupportTickets")


def seed_ticket_messages(cursor):
    print("Seeding TicketMessages...")
    cursor.execute("SELECT Id, BusinessOwnerUserId FROM SupportTickets")
    tickets = cursor.fetchall()
    
    sql = """INSERT INTO TicketMessages
             (TicketId, Content, IsAdminMessage, SenderId, EmailSent,
              CreatedAt, CreatedBy, UpdatedAt, UpdatedBy)
             VALUES (?,?,?,?,?,?,?,?,?)"""
    inserted = 0
    for ticket_id, bo_id in tickets:
        num_msgs = random.randint(1, 4)
        for i in range(num_msgs):
            dt = rand_dt(180, 1)
            is_admin = i % 2 == 0
            # Ensure sender_id matches exactly a valid ALL_USER_IDS or null if admin is unmapped in this script context
            # We'll use the BO as sender for non-admin, and random user for admin to satisfy FK
            sender = random.choice(ALL_USER_IDS) if is_admin else bo_id
            
            cursor.execute(sql, (
                ticket_id, "Please see details.", 1 if is_admin else 0,
                sender, 1, dt, sender, dt, sender
            ))
            inserted += 1
    print(f"  [OK] Inserted {inserted} TicketMessages")


def seed_onboarding_progress(cursor):
    print("Seeding OnboardingProgress...")
    # Table only has 5 columns: Id, BusinessOwnerId, TourCompleted, ChecklistProductAdded, ChecklistPaymentSet, ChecklistProfileDone
    sql = """INSERT INTO OnboardingProgress
             (BusinessOwnerId, TourCompleted, ChecklistProductAdded, ChecklistPaymentSet, ChecklistProfileDone)
             VALUES (?,?,?,?,?)"""
    inserted = 0
    
    # Clean up existing to avoid duplicates if BO exists
    cursor.execute("DELETE FROM OnboardingProgress")
    
    for bo_id in BO_USER_IDS:
        cursor.execute(sql, (
            bo_id,
            1 if random.random() > 0.2 else 0,
            1 if random.random() > 0.4 else 0,
            1 if random.random() > 0.5 else 0,
            1 if random.random() > 0.1 else 0
        ))
        inserted += 1
    print(f"  [OK] Inserted {inserted} OnboardingProgress rows")


def seed_payout_requests(cursor):
    print("Seeding PayoutRequests...")
    statuses = ["Pending", "Approved", "Processing", "Completed", "Rejected"]
    banks = ["CIB Bank", "NBE", "Banque Misr", "QNB Egypt", "HSBC Egypt"]
    names = ["Ahmed Hassan", "Sara Mohamed", "Omar Khalil", "Nadia Ali"]
    
    # Cleanup to avoid duplicates per BO+Status if it has unique index
    cursor.execute("DELETE FROM PayoutRequests")
    
    sql = """INSERT INTO PayoutRequests
             (BusinessOwnerId, Amount, Currency, Status, BankName, AccountHolderName,
              AccountIdentifierEnc, RoutingSwiftCode, CreatedAt, UpdatedAt, CreatedBy, UpdatedBy)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"""
    inserted = 0
    for bo_id in BO_USER_IDS:
        for status in random.sample(statuses, random.randint(1, 3)):
            amount = round(random.uniform(500, 20000), 2)
            dt = rand_dt(120, 1)
            cursor.execute(sql, (
                bo_id, amount, "EGP", status, random.choice(banks), random.choice(names),
                f"ENC_{random.randint(100000000,999999999)}", "XXXXXXXX",
                dt, dt, bo_id, bo_id
            ))
            inserted += 1
    print(f"  [OK] Inserted {inserted} PayoutRequests")


def seed_production_requests(cursor, count=200):
    print(f"Seeding {count} BoProductionRequests...")
    statuses = ["Submitted", "UnderReview", "Quoted", "Confirmed", "InProduction", "Completed", "Rejected"]
    
    sql = """INSERT INTO BoProductionRequests
             (BusinessOwnerId, Title, Notes, Status, QuotedPrice,
              EstimatedCompletionDate, CompletedAt, FraudScore, IsFraudFlag,
              PaymentStatus, CreatedAt, UpdatedAt, CreatedBy, UpdatedBy)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    for i in range(count):
        bo = random.choice(BO_USER_IDS)
        status = random.choice(statuses)
        is_fraud = random.random() < 0.08
        f_score = round(random.uniform(0.55, 0.95), 2) if is_fraud else round(random.uniform(0.0, 0.25), 2)
        dt = rand_dt(180, 1)
        
        cursor.execute(sql, (
            bo, f"Request {i}", "Notes...", status, random.randint(100, 5000),
            dt, dt if status == "Completed" else None,
            f_score, 1 if is_fraud else 0, "Paid", dt, dt, bo, bo
        ))
    print(f"  [OK] Inserted {count} BoProductionRequests")


def update_products(cursor):
    print("Updating Products with stats...")
    for pid in PRODUCT_IDS:
        cursor.execute("""
            UPDATE Products
            SET ViewCount=?, CartAddCount=?, PurchaseCount=?,
                RevenueTotal=?, AvgRating=?
            WHERE Id=?
        """, (random.randint(150, 3000), random.randint(20, 400),
              random.randint(10, 150), random.uniform(500, 5000),
              random.uniform(3.5, 5.0), pid))
    print(f"  [OK] Updated {len(PRODUCT_IDS)} Products")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Talentree AI - Full Seed for db52715 (New Schema)")
    print("=" * 60)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Delete existing data in proper order to avoid FK errors
        cursor.execute("DELETE FROM TicketMessages")
        cursor.execute("DELETE FROM SupportTickets")
        cursor.execute("DELETE FROM ProductReviews")
        cursor.execute("DELETE FROM Transactions")
        cursor.execute("DELETE FROM LoginHistories")
        cursor.execute("DELETE FROM BoProductionRequests")
        conn.commit()
        
        seed_transactions(cursor, 1000)
        conn.commit()

        seed_login_histories(cursor, 3000)
        conn.commit()

        seed_product_reviews(cursor, 200)
        conn.commit()

        seed_support_tickets(cursor, 100)
        conn.commit()

        seed_ticket_messages(cursor)
        conn.commit()

        seed_onboarding_progress(cursor)
        conn.commit()

        seed_payout_requests(cursor)
        conn.commit()

        seed_production_requests(cursor, 200)
        conn.commit()

        update_products(cursor)
        conn.commit()

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
    main()
