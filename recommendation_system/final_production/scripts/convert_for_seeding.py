import os
import json
from datetime import datetime, timezone

def convert_products_for_seeding(source_path: str, target_path: str):
    """Converts products.json to match SQL Server 'Products' table schema."""
    print(f"Reading products from: {source_path}")
    with open(source_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
        
    category_map = {
        "Fashion & Accessories": 1,
        "Handmade & Crafts": 2,
        "Natural & Beauty Products": 3
    }
    
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    converted_products = []
    
    for p in products:
        category_name = p.get("category", "")
        category_id = category_map.get(category_name)
        if category_id is None:
            raise ValueError(f"Unknown product category: '{category_name}' for product ID {p.get('product_id')}")
            
        converted = {
            "Id": int(p["product_id"]),
            "Name": str(p["product_name"]),
            "Description": str(p.get("description", "")),
            "Price": float(p["price"]),
            "CreatedAt": current_time,
            "UpdatedAt": None,
            "CreatedBy": None,
            "UpdatedBy": None,
            "IsDeleted": False,
            "DeletedAt": None,
            "ApprovedAt": current_time,
            "ApprovedBy": "SystemSeeder",
            "BusinessOwnerProfileId": 1,  # Default system owner
            "CategoryId": category_id,
            "RejectionReason": None,
            "Status": 1,  # Active
            "StockQuantity": 100,  # Default seeding stock
            "Tags": None,
            "AvgRating": None,
            "CartAddCount": 0,
            "DemandForecastQty": None,
            "DemandForecastUpdatedAt": None,
            "DescriptionQualityScore": None,
            "LowStockFlag": False,
            "PurchaseCount": 0,
            "RevenueTotal": 0.0,
            "ViewCount": 0,
            "DeletedBy": None,
            "IsVisible": True,
            "FeaturedOrder": 0,
            "IsFeatured": False
        }
        converted_products.append(converted)
        
    print(f"Successfully converted {len(converted_products)} products.")
    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(converted_products, f, indent=2, ensure_ascii=False)
    print(f"Wrote seeding products to: {target_path}")
    return converted_products

def convert_raw_materials_for_seeding(source_path: str, target_path: str):
    """Converts raw_materials.json to match SQL Server 'RawMaterials' table schema."""
    print(f"Reading raw materials from: {source_path}")
    with open(source_path, 'r', encoding='utf-8') as f:
        materials = json.load(f)
        
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    converted_materials = []
    
    for m in materials:
        converted = {
            "Id": int(m["material_id"]),
            "Name": str(m["material_name"]),
            "Description": str(m.get("description", "")),
            "Price": float(m["price"]),
            "Unit": "pcs",  # Standard unit for starter kits/items
            "MinimumOrderQuantity": 1,
            "StockQuantity": 100,  # Default stock level
            "IsAvailable": True,
            "Category": str(m["category"]),
            "PictureUrl": None,
            "SupplierId": 1,  # Default system supplier
            "CreatedAt": current_time,
            "UpdatedAt": None,
            "CreatedBy": None,
            "UpdatedBy": None,
            "IsDeleted": False,
            "DeletedAt": None,
            "DeletedBy": None,
            "OrderFrequency": 0,
            "PriceTrend": ""
        }
        converted_materials.append(converted)
        
    print(f"Successfully converted {len(converted_materials)} raw materials.")
    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(converted_materials, f, indent=2, ensure_ascii=False)
    print(f"Wrote seeding raw materials to: {target_path}")
    return converted_materials

def run_self_validation(products: list, raw_materials: list):
    """Self-validates fields and constraints of generated datasets."""
    print("\n--- Running Seeding Data Schema Self-Validation ---")
    
    # Required/Non-nullable columns from Products database schema
    required_product_cols = [
        "Id", "Name", "Description", "Price", "CreatedAt", "IsDeleted", 
        "BusinessOwnerProfileId", "CategoryId", "Status", "StockQuantity", 
        "CartAddCount", "LowStockFlag", "PurchaseCount", "RevenueTotal", 
        "ViewCount", "IsVisible", "FeaturedOrder", "IsFeatured"
    ]
    
    # Required/Non-nullable columns from RawMaterials database schema
    required_material_cols = [
        "Id", "Name", "Description", "Price", "Unit", "MinimumOrderQuantity", 
        "StockQuantity", "IsAvailable", "Category", "SupplierId", 
        "CreatedAt", "IsDeleted", "OrderFrequency", "PriceTrend"
    ]
    
    # Validate Products
    print("Validating Products...")
    for idx, p in enumerate(products):
        # 1. Check all required columns are present and not None
        for col in required_product_cols:
            if col not in p:
                raise ValueError(f"[Product Index {idx}] Missing required column '{col}'")
            if p[col] is None:
                raise ValueError(f"[Product Index {idx}, ID {p['Id']}] Column '{col}' is None but is non-nullable in database.")
                
        # 2. Check CategoryId value ranges
        if p["CategoryId"] not in [1, 2, 3]:
            raise ValueError(f"[Product ID {p['Id']}] CategoryId must be 1, 2, or 3. Got {p['CategoryId']}.")
            
        # 3. Check data types
        if not isinstance(p["Id"], int):
            raise TypeError(f"[Product ID {p['Id']}] Id must be integer.")
        if not isinstance(p["Price"], (int, float)):
            raise TypeError(f"[Product ID {p['Id']}] Price must be a numeric value.")
        if not isinstance(p["IsDeleted"], bool):
            raise TypeError(f"[Product ID {p['Id']}] IsDeleted must be boolean.")
            
    print("[SUCCESS] All products successfully passed database schema validation.")
    
    # Validate Raw Materials
    print("Validating Raw Materials...")
    for idx, m in enumerate(raw_materials):
        # 1. Check all required columns are present and not None
        for col in required_material_cols:
            if col not in m:
                raise ValueError(f"[Material Index {idx}] Missing required column '{col}'")
            if m[col] is None:
                raise ValueError(f"[Material Index {idx}, ID {m['Id']}] Column '{col}' is None but is non-nullable in database.")
                
        # 2. Check data types
        if not isinstance(m["Id"], int):
            raise TypeError(f"[Material ID {m['Id']}] Id must be integer.")
        if not isinstance(m["Price"], (int, float)):
            raise TypeError(f"[Material ID {m['Id']}] Price must be a numeric value.")
        if not isinstance(m["IsAvailable"], bool):
            raise TypeError(f"[Material ID {m['Id']}] IsAvailable must be boolean.")
            
    print("[SUCCESS] All raw materials successfully passed database schema validation.")

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "data")
    
    src_products = os.path.join(data_dir, "products.json")
    tgt_products = os.path.join(data_dir, "products_db_seeding.json")
    
    src_materials = os.path.join(data_dir, "raw_materials.json")
    tgt_materials = os.path.join(data_dir, "raw_materials_db_seeding.json")
    
    # Run conversion
    converted_prods = convert_products_for_seeding(src_products, tgt_products)
    converted_mats = convert_raw_materials_for_seeding(src_materials, tgt_materials)
    
    # Run validation
    run_self_validation(converted_prods, converted_mats)
    print("\n--- Seeding Files Ready for Delivery to Backend Team! ---")
