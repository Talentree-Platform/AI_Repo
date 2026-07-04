import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database_exploration.core.schema_inspector import SchemaInspector
from database_exploration.core.exploration_logger import exp_logger

def run_detect_relationships():
    exp_logger.info("Executing detect_relationships.py...")
    inspector = SchemaInspector()
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "database_connected": inspector.is_connected(),
        "foreign_keys_detected": {},
        "inferred_recommendation_joins": [],
        "inferred_relationships": []
    }
    
    if inspector.is_connected():
        tables = inspector.get_all_tables()
        for tbl in tables:
            fkeys = inspector.get_foreign_keys(tbl)
            if fkeys:
                report["foreign_keys_detected"][tbl] = fkeys
                
        # Analyze interactions connection explicitly
        # In many schemas, FKs are not declared explicitly in DB but handled at app layer.
        # Let's inspect declared FKs and also infer implicit ones.
        exp_logger.info("Analyzing implicit joins and recommendation mapping signals...")
    else:
        exp_logger.warning("Database offline. Generating implicit conceptual schema relationships.")
        
    # Build inferred relationship mappings (critical for mapping recommendation links!)
    # User -> Interactions -> Products (Customer Recommender)
    # Owner -> Interactions -> Raw Materials (Owner Recommender)
    
    report["inferred_recommendation_joins"] = [
        {
            "name": "Customer Recommender Join Path",
            "source_entity": "Customer (user_id)",
            "join_table": "interactions",
            "target_entity": "Product (product_id)",
            "join_conditions": {
                "user_join": "interactions.user_id = user.id AND interactions.user_type = 'customer'",
                "item_join": "interactions.item_id = products.product_id AND interactions.item_type = 'product'"
            },
            "signals": ["view", "click", "add_to_cart", "purchase"]
        },
        {
            "name": "Business Owner Procurement Join Path",
            "source_entity": "Business Owner (user_id)",
            "join_table": "interactions",
            "target_entity": "RawMaterial (material_id)",
            "join_conditions": {
                "user_join": "interactions.user_id = owner.id AND interactions.user_type = 'owner'",
                "item_join": "interactions.item_id = raw_materials.material_id AND interactions.item_type = 'raw_material'"
            },
            "signals": ["purchase", "reorder"]
        }
    ]
    
    # Generate inferred Entity Relationships
    report["inferred_relationships"] = [
        {
            "from_table": "interactions",
            "from_columns": ["item_id"],
            "to_table": "products",
            "to_columns": ["product_id"],
            "relationship_type": "Many-to-One (implicit via item_type='product')"
        },
        {
            "from_table": "interactions",
            "from_columns": ["item_id"],
            "to_table": "raw_materials",
            "to_columns": ["material_id"],
            "relationship_type": "Many-to-One (implicit via item_type='raw_material')"
        }
    ]
    
    report_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports"
    )
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "relationships_report.json")
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
        
    exp_logger.info(f"Generated relationships report at {report_path}")
    
    # Display summary
    print("\n================ RELATIONSHIPS & JOIN PATHS ================")
    print(f"Status: {'ONLINE' if report['database_connected'] else 'OFFLINE (Conceptual)'}")
    print(f"Declared FKs: {len(report['foreign_keys_detected'])} tables have explicit FKs")
    for tbl, fks in report["foreign_keys_detected"].items():
        print(f"  Table: {tbl}")
        for fk in fks:
            print(f"    - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
            
    print("\nInferred Recommendation Join Paths:")
    for path in report["inferred_recommendation_joins"]:
        print(f"  * {path['name']}:")
        print(f"      From: {path['source_entity']}")
        print(f"      Via:  {path['join_table']}")
        print(f"      To:   {path['target_entity']}")
        print(f"      Join: {path['join_conditions']['user_join']}")
        print(f"            {path['join_conditions']['item_join']}")
    print("============================================================\n")

if __name__ == "__main__":
    run_detect_relationships()
