import pandas as pd
import numpy as np
from shared.feature_engineering.owner.recency_decay import apply_recency_decay
from shared.utils.logger import owner_logger

class OwnerFeatureBuilder:
    """Builds features for the B2B Business Owner Raw Material Recommendation System."""
    
    def __init__(self, lambda_decay: float = 0.003):
        self.lambda_decay = lambda_decay
        self.interaction_weights = {
            "view": 1.0,
            "click": 2.0,
            "add_to_cart": 3.0,
            "purchase": 5.0,
            "reorder": 7.0
        }

    def build_features(self, interactions_df: pd.DataFrame, raw_materials_df: pd.DataFrame) -> pd.DataFrame:
        """Processes raw owner interactions and returns engineered procurement feature signals."""
        owner_logger.info("Starting Business Owner Feature Engineering Pipeline...")
        
        # Make a copy of input
        df = interactions_df.copy()
        
        # 1. Apply interaction weights
        df['interaction_type_lower'] = df['interaction_type'].str.lower().str.strip()
        df['interaction_weight'] = df['interaction_type_lower'].map(self.interaction_weights).fillna(1.0)
        df.drop(columns=['interaction_type_lower'], inplace=True)
        
        # 2. Apply recency decay
        df = apply_recency_decay(df, self.lambda_decay)
        
        # Score = Sum of (weight * decay * quantity) for business supply orders
        df['event_score'] = df['interaction_weight'] * df['decay_weight'] * df['quantity']
        
        # 3. Compile User-Item Procurement Aggregates
        user_item_grouped = df.groupby(['user_id', 'item_id'])
        user_item_stats = user_item_grouped.agg(
            weighted_score=('event_score', 'sum'),
            avg_procurement_quantity=('quantity', 'mean'),
            total_quantity_procured=('quantity', 'sum'),
            procurement_count=('quantity', 'count')
        ).reset_index()
        
        # 4. Calculate Procurement Intervals (Reorder Cycle Days)
        # Average days between owner purchases
        df['interaction_timestamp'] = pd.to_datetime(df['interaction_timestamp'])
        df_sorted = df.sort_values(by=['user_id', 'interaction_timestamp'])
        
        # Diff consecutive orders for same user
        df_sorted['prev_timestamp'] = df_sorted.groupby('user_id')['interaction_timestamp'].shift(1)
        df_sorted['interval_days'] = (df_sorted['interaction_timestamp'] - df_sorted['prev_timestamp']).dt.total_seconds() / (24 * 3600)
        
        user_intervals = df_sorted.groupby('user_id')['interval_days'].mean().reset_index()
        user_intervals.rename(columns={'interval_days': 'avg_procurement_interval_days'}, inplace=True)
        
        # 5. Seasonal Procurement Indices
        # Group by user and month to get seasonal trends
        df['month'] = df['interaction_timestamp'].dt.month
        user_month_volume = df.groupby(['user_id', 'month']).size().reset_index(name='month_order_count')
        # Standardize seasonality score (monthly count / total user count)
        user_total_orders = df.groupby('user_id').size().reset_index(name='total_user_orders')
        seasonality = pd.merge(user_month_volume, user_total_orders, on='user_id')
        seasonality['seasonal_procurement_index'] = seasonality['month_order_count'] / seasonality['total_user_orders']
        
        # Favorite month (most active month for reordering)
        fav_month = seasonality.sort_values(by=['user_id', 'seasonal_procurement_index'], ascending=[True, False]).groupby('user_id').first().reset_index()
        fav_month = fav_month[['user_id', 'month']].rename(columns={'month': 'peak_procurement_month'})
        
        # 6. Supplier/Category Affinity Profile
        user_cat_scores = df.groupby(['user_id', 'category'])['event_score'].sum().reset_index()
        user_cat_scores['rank'] = user_cat_scores.groupby('user_id')['event_score'].rank(method='first', ascending=False)
        top_cats = user_cat_scores[user_cat_scores['rank'] <= 2].pivot(index='user_id', columns='rank', values='category').reset_index()
        top_cats.rename(columns={1.0: 'supplier_affinity_category_1', 2.0: 'supplier_affinity_category_2'}, inplace=True)
        
        # Merge all Owner characteristics
        user_features = pd.merge(user_intervals, fav_month, on='user_id', how='left')
        user_features = pd.merge(user_features, top_cats, on='user_id', how='left')
        user_features['avg_procurement_interval_days'] = user_features['avg_procurement_interval_days'].fillna(30.0) # Default to monthly cycle if single data point
        
        # 7. Material popularity/demand features
        mat_pop = df.groupby('item_id')['event_score'].agg(['count', 'sum']).reset_index()
        mat_pop.rename(columns={'count': 'material_interaction_count', 'sum': 'material_demand_score'}, inplace=True)
        
        material_info = raw_materials_df[['material_id', 'category', 'price']].rename(columns={'material_id': 'item_id', 'category': 'material_category'})
        item_features = pd.merge(material_info, mat_pop, on='item_id', how='left')
        item_features['material_interaction_count'] = item_features['material_interaction_count'].fillna(0).astype(int)
        item_features['material_demand_score'] = item_features['material_demand_score'].fillna(0.0)
        
        # 8. Reorder count per user-item pair (explicit reorder events)
        reorders = df[df['interaction_type'].str.lower() == 'reorder']
        user_item_reorders = reorders.groupby(['user_id', 'item_id']).size().reset_index(name='reorder_count')
        
        # 9. Assemble full B2B feature dataset
        features = pd.merge(user_item_stats, user_features, on='user_id', how='left')
        features = pd.merge(features, item_features, on='item_id', how='left')
        features = pd.merge(features, user_item_reorders, on=['user_id', 'item_id'], how='left')
        features['reorder_count'] = features['reorder_count'].fillna(0).astype(int)
        
        owner_logger.info(f"Business owner feature engineering complete. Created {len(features)} feature rows.")
        return features
