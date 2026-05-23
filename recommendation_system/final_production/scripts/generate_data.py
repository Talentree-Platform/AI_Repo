import os
import json
import random
import numpy as np
from datetime import datetime, timedelta

def create_product_catalog(num_products=200):
    categories = {
        "electronics": ["Smartphone", "Laptop", "Wireless Earbuds", "Smart Watch", "Power Bank", "Bluetooth Speaker", "Tablet", "Charger Cable"],
        "clothing": ["T-Shirt", "Jeans", "Hoodie", "Jacket", "Sneakers", "Socks", "Cap", "Running Shorts"],
        "home_decor": ["Desk Lamp", "Scented Candle", "Throw Pillow", "Wall Clock", "Bonsai Tree", "Picture Frame", "Area Rug", "Curtains"],
        "grocery": ["Organic Coffee", "Green Tea", "Granola Bars", "Almond Butter", "Dark Chocolate", "Olive Oil", "Oat Milk", "Honey"],
        "beauty": ["Facial Cleanser", "Moisturizer", "Sunscreen", "Lip Balm", "Shampoo", "Face Mask", "Perfume", "Hand Cream"]
    }
    
    products = []
    for i in range(1, num_products + 1):
        cat = random.choice(list(categories.keys()))
        base_name = random.choice(categories[cat])
        product_name = f"{base_name} Model {chr(65 + (i % 26))}{i}"
        
        # Determine price ranges by category
        if cat == "electronics":
            price = round(random.uniform(20.0, 1000.0), 2)
        elif cat == "clothing":
            price = round(random.uniform(15.0, 150.0), 2)
        elif cat == "home_decor":
            price = round(random.uniform(10.0, 200.0), 2)
        elif cat == "grocery":
            price = round(random.uniform(3.0, 30.0), 2)
        else: # beauty
            price = round(random.uniform(8.0, 80.0), 2)
            
        description = f"Premium {product_name} in {cat} category. High-quality build, popular selection."
        
        products.append({
            "product_id": i,
            "product_name": product_name,
            "category": cat,
            "price": price,
            "description": description
        })
    return products

def create_raw_material_catalog(num_materials=100):
    categories = {
        "fabrics": ["Cotton Roll", "Polyester Blend", "Silk Yarn", "Denim Sheets", "Linen Fiber", "Wool Thread"],
        "metals": ["Aluminum Plate", "Steel Rods", "Copper Wire Coils", "Brass Sheets", "Titanium Screws"],
        "chemicals": ["Industrial Solvent", "Polymer Resin", "Organic Dyes", "Catalyst Agent", "Adhesive Liquid"],
        "agricultural": ["Raw Coffee Beans", "Cocoa Beans", "Cotton Fiber", "Sugar Cane Extract", "Essential Oils Extract"],
        "packaging": ["Cardboard Boxes", "Biodegradable Wrap", "Glass Bottles", "Tin Cans", "Paper Bags"]
    }
    
    materials = []
    for i in range(1, num_materials + 1):
        cat = random.choice(list(categories.keys()))
        base_name = random.choice(categories[cat])
        material_name = f"{base_name} Grade-{chr(65 + (i % 6))}{i}"
        
        if cat == "fabrics":
            price = round(random.uniform(5.0, 50.0), 2)
        elif cat == "metals":
            price = round(random.uniform(20.0, 300.0), 2)
        elif cat == "chemicals":
            price = round(random.uniform(10.0, 150.0), 2)
        elif cat == "agricultural":
            price = round(random.uniform(2.0, 40.0), 2)
        else: # packaging
            price = round(random.uniform(0.5, 10.0), 2)
            
        description = f"Industrial raw {material_name} in {cat} division. Certified for production use."
        
        materials.append({
            "material_id": i,
            "material_name": material_name,
            "category": cat,
            "price": price,
            "description": description
        })
    return materials

def generate_data():
    print("Generating synthetic catalogs...")
    products = create_product_catalog(200)
    raw_materials = create_raw_material_catalog(100)
    
    # Save Catalogs
    os.makedirs("data", exist_ok=True)
    with open("data/products.json", "w") as f:
        json.dump(products, f, indent=2)
    with open("data/raw_materials.json", "w") as f:
        json.dump(raw_materials, f, indent=2)
        
    start_date = datetime.now() - timedelta(days=90)
    
    # ----------------------------------------------------
    # CUSTOMER INTERACTIONS (60,000 interactions)
    # ----------------------------------------------------
    print("Generating customer interactions...")
    customer_interactions = []
    num_customers = 1000
    
    # Assign favorite categories to customers to form clusters
    customer_preferences = {}
    for cust_id in range(1, num_customers + 1):
        primary = random.choice([p["category"] for p in products])
        secondary = random.choice([p["category"] for p in products])
        customer_preferences[cust_id] = [primary, secondary]
        
    product_by_cat = {}
    for p in products:
        product_by_cat.setdefault(p["category"], []).append(p)

    interaction_types = ["view", "click", "purchase"]
    weights = [0.45, 0.40, 0.15]
    
    for i in range(60000):
        cust_id = random.randint(1, num_customers)
        pref_cats = customer_preferences[cust_id]
        
        # 80% chance to choose from preferred categories, 20% random exploration
        if random.random() < 0.8:
            selected_cat = random.choice(pref_cats)
        else:
            selected_cat = random.choice(list(product_by_cat.keys()))
            
        prod = random.choice(product_by_cat[selected_cat])
        int_type = random.choices(interaction_types, weights=weights)[0]
        
        # Seasonality: weekends get more activity, holidays, time-of-day
        days_offset = random.randint(0, 89)
        hour = random.choice(list(range(24)))
        # Peak hours: 18:00 - 22:00
        if random.random() < 0.6:
            hour = random.choice(list(range(18, 23)))
            
        int_time = start_date + timedelta(days=days_offset, hours=hour, minutes=random.randint(0, 59))
        
        # Quantity
        quantity = 1
        if int_type == "purchase":
            quantity = random.randint(1, 4)
            
        customer_interactions.append({
            "user_type": "customer",
            "user_id": cust_id,
            "item_id": prod["product_id"],
            "item_type": "product",
            "interaction_type": int_type,
            "category": prod["category"],
            "quantity": quantity,
            "price": prod["price"],
            "interaction_timestamp": int_time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
    # Sort by timestamp
    customer_interactions.sort(key=lambda x: x["interaction_timestamp"])
    with open("data/customer_interactions.json", "w") as f:
        json.dump(customer_interactions, f, indent=2)
        
    # ----------------------------------------------------
    # OWNER PROCUREMENT INTERACTIONS (40,000 interactions)
    # ----------------------------------------------------
    print("Generating owner procurement interactions...")
    owner_interactions = []
    num_owners = 100
    
    material_by_cat = {}
    for m in raw_materials:
        material_by_cat.setdefault(m["category"], []).append(m)
        
    # Assign standard procurement cycles to each owner-material pairing
    # cycles: 7 days, 14 days, 21 days, 30 days
    owner_schedules = []
    for owner_id in range(1, num_owners + 1):
        # Owners procure about 5-15 raw materials regularly
        num_materials_procured = random.randint(5, 15)
        subscribed_materials = random.sample(raw_materials, num_materials_procured)
        
        for mat in subscribed_materials:
            cycle_days = random.choice([7, 14, 21, 28])
            # Random starting date offset within the first 14 days
            start_offset = random.randint(0, 14)
            owner_schedules.append({
                "owner_id": owner_id,
                "material": mat,
                "cycle": cycle_days,
                "start_offset": start_offset,
                "base_qty": random.randint(50, 400)
            })
            
    # Simulating standard reorders over the 90 days period
    current_time = start_date
    end_date = datetime.now()
    
    # Run a daily schedule simulator to generate realistic cyclic time-series procurement data!
    sim_date = start_date
    while sim_date <= end_date:
        for sched in owner_schedules:
            owner_id = sched["owner_id"]
            mat = sched["material"]
            cycle = sched["cycle"]
            start_offset = sched["start_offset"]
            
            days_since_start = (sim_date - start_date).days
            
            # Check if this day is a procurement day (with some noise of ±2 days)
            # Or occasional random purchases
            is_procurement_day = ((days_since_start - start_offset) % cycle == 0)
            
            if is_procurement_day or (random.random() < 0.02): # 2% chance of emergency purchase
                # Interaction Type
                int_type = "reorder" if (is_procurement_day and random.random() < 0.8) else "purchase"
                
                # Seasonality: Business cycles might have higher volumes at start/end of month
                multiplier = 1.0
                if sim_date.day in [1, 2, 28, 29, 30]:
                    multiplier = 1.25
                    
                quantity = int(sched["base_qty"] * multiplier * random.uniform(0.85, 1.15))
                hour = random.randint(8, 17) # Business hours: 8am to 5pm
                int_time = sim_date + timedelta(hours=hour, minutes=random.randint(0, 59))
                
                owner_interactions.append({
                    "user_type": "owner",
                    "user_id": owner_id,
                    "item_id": mat["material_id"],
                    "item_type": "raw_material",
                    "interaction_type": int_type,
                    "category": mat["category"],
                    "quantity": quantity,
                    "price": mat["price"],
                    "interaction_timestamp": int_time.strftime("%Y-%m-%d %H:%M:%S")
                })
                
        sim_date += timedelta(days=1)
        
    # We want exactly 40,000 or close. Let's fill/trim slightly to make it robust and match expectations
    target_owner_count = 40000
    if len(owner_interactions) > target_owner_count:
        owner_interactions = random.sample(owner_interactions, target_owner_count)
    else:
        # Pad with random browses/reorders if under-filled
        diff = target_owner_count - len(owner_interactions)
        for _ in range(diff):
            sched = random.choice(owner_schedules)
            mat = sched["material"]
            days_offset = random.randint(0, 89)
            hour = random.randint(8, 17)
            int_time = start_date + timedelta(days=days_offset, hours=hour, minutes=random.randint(0, 59))
            owner_interactions.append({
                "user_type": "owner",
                "user_id": sched["owner_id"],
                "item_id": mat["material_id"],
                "item_type": "raw_material",
                "interaction_type": random.choice(["reorder", "purchase"]),
                "category": mat["category"],
                "quantity": int(sched["base_qty"] * random.uniform(0.7, 1.3)),
                "price": mat["price"],
                "interaction_timestamp": int_time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
    # Sort and save
    owner_interactions.sort(key=lambda x: x["interaction_timestamp"])
    with open("data/owner_interactions.json", "w") as f:
        json.dump(owner_interactions, f, indent=2)
        
    print(f"Data generation complete! Totals:")
    print(f"  Products catalog: {len(products)}")
    print(f"  Raw materials catalog: {len(raw_materials)}")
    print(f"  Customer Interactions: {len(customer_interactions)}")
    print(f"  Owner Interactions: {len(owner_interactions)}")

if __name__ == "__main__":
    generate_data()
