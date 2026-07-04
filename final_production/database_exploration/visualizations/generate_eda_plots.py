import os
import sys
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database_exploration.core.db_connector import get_exploration_engine, load_data_fallback, check_exploration_connection
from database_exploration.core.exploration_logger import exp_logger

def check_visualization_libraries() -> bool:
    """Verifies that matplotlib and seaborn are available for plotting."""
    try:
        import matplotlib
        import seaborn
        matplotlib.use('Agg') # Non-interactive backend to save plots without UI window popup
        return True
    except ImportError as e:
        exp_logger.warning(f"Visualization libraries missing: {e}. Please run 'pip install matplotlib seaborn'")
        return False

def generate_all_plots():
    exp_logger.info("Starting visualization plots generator...")
    if not check_visualization_libraries():
        print("\n[WARNING] Matplotlib or Seaborn not installed. Cannot generate plots.")
        print("Please run: pip install matplotlib seaborn\n")
        return
        
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    # Configure plot aesthetics (premium dark grid theme)
    sns.set_theme(style="darkgrid")
    plt.rcParams.update({
        'font.size': 10,
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'figure.titlesize': 16
    })

    db_connected, _ = check_exploration_connection()
    engine = get_exploration_engine()
    
    # 1. LOAD DATA
    df = None
    if db_connected and engine is not None:
        try:
            df = pd.read_sql("SELECT * FROM interactions", engine)
            exp_logger.info(f"Loaded {len(df)} rows from SQL Server for plotting.")
        except Exception as e:
            exp_logger.warning(f"Failed to query database for plotting: {e}. Trying fallback.")
            df = None
            
    if df is None:
        df = load_data_fallback("interactions")
        
    if df is None or len(df) == 0:
        exp_logger.error("No interaction data loaded. Plot generation aborted.")
        return
        
    # Create output directory
    vis_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(vis_dir, exist_ok=True)
    
    # Process Timestamps
    df["interaction_timestamp"] = pd.to_datetime(df["interaction_timestamp"])
    
    # Let's generate each chart!
    
    # --- CHART 1: Interaction Frequencies ---
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df, x="interaction_type", hue="user_type", palette="viridis")
    plt.title("Interaction Frequency Counts by User Type")
    plt.xlabel("Interaction Type")
    plt.ylabel("Event Count")
    plt.tight_layout()
    chart1_path = os.path.join(vis_dir, "interaction_frequencies.png")
    plt.savefig(chart1_path, dpi=300)
    plt.close()
    exp_logger.info(f"Saved Chart: {chart1_path}")
    
    # --- CHART 2: Popular Products (Top 10) ---
    plt.figure(figsize=(10, 6))
    cust_df = df[df["user_type"].str.lower() == "customer"]
    if len(cust_df) > 0:
        top_items = cust_df["item_id"].value_counts().head(10).reset_index()
        top_items.columns = ["Product ID", "Interactions Count"]
        sns.barplot(data=top_items, x="Interactions Count", y="Product ID", orient="h", palette="magma", hue="Product ID", legend=False)
        plt.title("Top 10 Most Interacted Products (Customer Pathway)")
        plt.xlabel("Total Interactions")
        plt.ylabel("Product ID")
        plt.tight_layout()
        chart2_path = os.path.join(vis_dir, "popular_products.png")
        plt.savefig(chart2_path, dpi=300)
        plt.close()
        exp_logger.info(f"Saved Chart: {chart2_path}")
        
    # --- CHART 3: Category Distributions ---
    plt.figure(figsize=(12, 6))
    if "category" in df.columns:
        cat_counts = df["category"].value_counts().head(8).reset_index()
        cat_counts.columns = ["Category", "Event Count"]
        sns.barplot(data=cat_counts, x="Event Count", y="Category", palette="plasma", hue="Category", legend=False)
        plt.title("Distribution of Interactions Across Top Categories")
        plt.xlabel("Total Events")
        plt.ylabel("Category")
        plt.tight_layout()
        chart3_path = os.path.join(vis_dir, "category_distributions.png")
        plt.savefig(chart3_path, dpi=300)
        plt.close()
        exp_logger.info(f"Saved Chart: {chart3_path}")
        
    # --- CHART 4: Reorder Trends (Purchases vs. Reorders over Time) ---
    plt.figure(figsize=(12, 6))
    purchases = df[df["interaction_type"].str.lower().isin(["purchase", "reorder"])]
    if len(purchases) > 0:
        purchases["date"] = purchases["interaction_timestamp"].dt.date
        temporal_trend = purchases.groupby(["date", "interaction_type"]).size().reset_index(name="count")
        sns.lineplot(data=temporal_trend, x="date", y="count", hue="interaction_type", palette="Set1", linewidth=2)
        plt.title("Temporal Reorder and Purchase Activity Trends")
        plt.xlabel("Date")
        plt.ylabel("Event Count")
        plt.xticks(rotation=45)
        plt.tight_layout()
        chart4_path = os.path.join(vis_dir, "reorder_trends.png")
        plt.savefig(chart4_path, dpi=300)
        plt.close()
        exp_logger.info(f"Saved Chart: {chart4_path}")

    # --- CHART 5: Temporal Activity Heatmap (Hour of Day vs Weekday) ---
    plt.figure(figsize=(12, 6))
    df["Hour"] = df["interaction_timestamp"].dt.hour
    df["Day"] = df["interaction_timestamp"].dt.day_name()
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot_df = df.groupby(["Day", "Hour"]).size().unstack(fill_value=0)
    pivot_df = pivot_df.reindex(day_order)
    sns.heatmap(pivot_df, cmap="coolwarm", cbar_kws={'label': 'Activity Volume'})
    plt.title("User Interaction Activity Density Heatmap")
    plt.xlabel("Hour of Day")
    plt.ylabel("Day of Week")
    plt.tight_layout()
    chart5_path = os.path.join(vis_dir, "temporal_activity.png")
    plt.savefig(chart5_path, dpi=300)
    plt.close()
    exp_logger.info(f"Saved Chart: {chart5_path}")
    
    # --- CHART 6: Missing Value Heatmap ---
    plt.figure(figsize=(10, 6))
    sns.heatmap(df.isnull(), cbar=False, yticklabels=False, cmap="viridis")
    plt.title("Missing Value Density Map (Interactions Table)")
    plt.tight_layout()
    chart6_path = os.path.join(vis_dir, "missing_value_heatmap.png")
    plt.savefig(chart6_path, dpi=300)
    plt.close()
    exp_logger.info(f"Saved Chart: {chart6_path}")
    
    print(f"\nSuccessfully generated premium EDA charts inside: {vis_dir}")
    print("Files created:")
    print("  - interaction_frequencies.png")
    print("  - popular_products.png")
    print("  - category_distributions.png")
    print("  - reorder_trends.png")
    print("  - temporal_activity.png")
    print("  - missing_value_heatmap.png\n")

if __name__ == "__main__":
    generate_all_plots()
