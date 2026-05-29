import os
import sys
import json
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database_exploration.core.db_connector import get_exploration_engine, load_data_fallback, check_exploration_connection
from database_exploration.core.exploration_logger import exp_logger

def analyze_signals(df: pd.DataFrame, source_name: str) -> dict:
    """Performs deep profiling of recommendation signals on interactions data."""
    total_records = len(df)
    
    report = {
        "analysis_timestamp": datetime.now().isoformat(),
        "source_dataset": source_name,
        "total_interactions": total_records,
        "customer_pathway": {},
        "owner_pathway": {}
    }
    
    if total_records == 0:
        exp_logger.warning("Empty interactions dataset. Recommendation signals cannot be analyzed.")
        return report
        
    # Standardize column names/types
    if "interaction_timestamp" in df.columns:
        df["interaction_timestamp"] = pd.to_datetime(df["interaction_timestamp"])
        
    # --- CUSTOMER SIDE PROFILING ---
    # customer rows are interactions where user_type is 'customer'
    cust_df = df[df["user_type"].str.lower() == "customer"] if "user_type" in df.columns else df
    
    if len(cust_df) > 0:
        total_cust = len(cust_df)
        signal_types = cust_df["interaction_type"].value_counts().to_dict()
        user_counts = cust_df["user_id"].nunique()
        item_counts = cust_df["item_id"].nunique()
        category_counts = cust_df["category"].nunique() if "category" in cust_df.columns else 0
        
        # Calculate repeated purchase rates
        purchases = cust_df[cust_df["interaction_type"].str.lower() == "purchase"]
        repeat_purchases_count = 0
        if len(purchases) > 0:
            user_item_purch = purchases.groupby(["user_id", "item_id"]).size()
            repeat_purchases_count = int((user_item_purch > 1).sum())
            
        report["customer_pathway"] = {
            "total_customer_interactions": total_cust,
            "unique_active_customers": int(user_counts),
            "unique_products_interacted": int(item_counts),
            "unique_categories": int(category_counts),
            "signal_distributions": {str(k): int(v) for k, v in signal_types.items()},
            "signal_percentages": {str(k): float((v / total_cust * 100)) for k, v in signal_types.items()},
            "purchases_count": len(purchases),
            "repeated_purchases_count": repeat_purchases_count,
            "reorder_rate": float((repeat_purchases_count / len(purchases) * 100)) if len(purchases) > 0 else 0.0,
            "sparsity_ratio": float(1 - (total_cust / (user_counts * item_counts))) if (user_counts * item_counts) > 0 else 1.0
        }
    else:
        report["customer_pathway"] = {"status": "No customer interaction data found"}
        
    # --- OWNER SIDE PROFILING ---
    # owner rows are interactions where user_type is 'owner' (or we use owner_interactions dataset directly)
    # Check if there is user_type == 'owner' in this df. Otherwise, we try to load owner_interactions.json
    owner_df = df[df["user_type"].str.lower() == "owner"] if "user_type" in df.columns else pd.DataFrame()
    
    # If owner_df is empty and we loaded fallback interactions, check if we need to load owner_interactions fallback explicitly
    if len(owner_df) == 0 and source_name == "JSON Fallback (customer_interactions.json)":
        exp_logger.info("Loading separate owner_interactions JSON to profile business procurement pathways...")
        owner_fallback_df = load_data_fallback("owner_interactions")
        if owner_fallback_df is not None:
            owner_df = owner_fallback_df
            source_name = f"{source_name} + owner_interactions.json"
            
    if len(owner_df) > 0:
        total_owner = len(owner_df)
        signal_types_owner = owner_df["interaction_type"].value_counts().to_dict()
        user_counts_owner = owner_df["user_id"].nunique()
        item_counts_owner = owner_df["item_id"].nunique()
        category_counts_owner = owner_df["category"].nunique() if "category" in owner_df.columns else 0
        
        # Aggregate seasonality indices
        procurements = owner_df[owner_df["interaction_type"].str.lower().isin(["purchase", "reorder"])]
        monthly_distribution = {}
        if len(procurements) > 0 and "interaction_timestamp" in procurements.columns:
            procurements_ts = pd.to_datetime(procurements["interaction_timestamp"], errors='coerce')
            months = procurements_ts.dropna().dt.strftime("%B").value_counts().to_dict()
            monthly_distribution = {str(k): int(v) for k, v in months.items()}
            
        report["owner_pathway"] = {
            "total_owner_interactions": total_owner,
            "unique_active_owners": int(user_counts_owner),
            "unique_materials_procured": int(item_counts_owner),
            "unique_categories": int(category_counts_owner),
            "signal_distributions": {str(k): int(v) for k, v in signal_types_owner.items()},
            "signal_percentages": {str(k): float((v / total_owner * 100)) for k, v in signal_types_owner.items()},
            "monthly_procurement_peaks": monthly_distribution,
            "sparsity_ratio": float(1 - (total_owner / (user_counts_owner * item_counts_owner))) if (user_counts_owner * item_counts_owner) > 0 else 1.0
        }
    else:
        report["owner_pathway"] = {"status": "No owner/procurement interaction data found"}
        
    return report

def run_signals_analysis():
    exp_logger.info("Executing analyze_recommendation_signals.py...")
    db_connected, _ = check_exploration_connection()
    engine = get_exploration_engine()
    
    df = None
    source_name = ""
    
    if db_connected and engine is not None:
        try:
            # Query active database interactions
            query = "SELECT * FROM interactions"
            df = pd.read_sql(query, engine)
            source_name = "SQL Server Database"
            exp_logger.info(f"Loaded {len(df)} interactions from SQL Database.")
        except Exception as e:
            exp_logger.warning(f"Failed to query interactions: {e}. Trying fallback.")
            df = None
            
    if df is None:
        # Load customer interactions fallback
        df = load_data_fallback("interactions")
        source_name = "JSON Fallback (customer_interactions.json)"
        
    if df is not None:
        report = analyze_signals(df, source_name)
        
        report_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "reports"
        )
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, "recommendation_signals_report.json")
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)
            
        exp_logger.info(f"Wrote signals analysis report to: {report_path}")
        
        # Display output summary
        print("\n================ RECOMMENDATION SIGNAL PROFILES ================")
        print(f"Interactions Source: {report['source_dataset']}")
        print(f"Total Rows Checked: {report['total_interactions']}")
        
        if "total_customer_interactions" in report["customer_pathway"]:
            cust = report["customer_pathway"]
            print("\n--- Customer Product Recommender Signals (B2C) ---")
            print(f"  Active Customers: {cust['unique_active_customers']}")
            print(f"  Products Checked: {cust['unique_products_interacted']}")
            print(f"  Sparsity Ratio:   {cust['sparsity_ratio'] * 100:.3f}%")
            print("  Signal Shares:")
            for sig, count in cust["signal_distributions"].items():
                pct = cust["signal_percentages"][sig]
                print(f"    - {sig}: {count} ({pct:.2f}%)")
            print(f"  Repeat Purchase Rate: {cust['reorder_rate']:.2f}% (from {cust['purchases_count']} purchases)")
            
        if "total_owner_interactions" in report["owner_pathway"]:
            own = report["owner_pathway"]
            print("\n--- Business Owner Procurement Signals (B2B) ---")
            print(f"  Active Owners:   {own['unique_active_owners']}")
            print(f"  Materials:       {own['unique_materials_procured']}")
            print(f"  Sparsity Ratio:  {own['sparsity_ratio'] * 100:.3f}%")
            print("  Signal Shares:")
            for sig, count in own["signal_distributions"].items():
                pct = own["signal_percentages"][sig]
                print(f"    - {sig}: {count} ({pct:.2f}%)")
            if own["monthly_procurement_peaks"]:
                print("  Monthly Peaks (Procurements):")
                sorted_months = sorted(own["monthly_procurement_peaks"].items(), key=lambda x: x[1], reverse=True)
                for month, val in sorted_months[:4]:
                    print(f"    - {month}: {val} orders")
        print("================================================================\n")
    else:
        print("\nError: Could not load interaction data to profile recommendation signals.")

if __name__ == "__main__":
    run_signals_analysis()
