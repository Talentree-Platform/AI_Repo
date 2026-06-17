import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db.connection import get_conn

conn = get_conn()
cursor = conn.cursor()

print("=== ALL USERS ===")
cursor.execute("SELECT Id FROM AspNetUsers")
users = [str(r[0]) for r in cursor.fetchall()]
print(f"Count: {len(users)}")
for u in users:
    print(f'  "{u}",')

print("\n=== BO PROFILE USER IDs ===")
cursor.execute("SELECT UserId FROM BusinessOwnerProfile WHERE IsDeleted=0")
bo_users = [str(r[0]) for r in cursor.fetchall()]
print(f"Count: {len(bo_users)}")
for u in bo_users:
    print(f'  "{u}",')

print("\n=== PRODUCTS ===")
cursor.execute("SELECT Id, Price FROM Products WHERE IsDeleted=0")
products = cursor.fetchall()
print(f"Count: {len(products)}")
for p in products:
    print(f"  Id={p[0]} Price={p[1]}")

cursor.close()
conn.close()
