import pandas as pd
import numpy as np
from shared.feature_engineering.customer.interaction_weighting import apply_interaction_weights
from shared.feature_engineering.customer.recency_decay import apply_recency_decay
from shared.utils.logger import customer_logger

class CustomerFeatureBuilder:
    """Builds features for the B2C Customer Product Recommendation System."""
    
    def __init__(self, lambda_decay: float = 0.005):
        self.lambda_decay = lambda_decay

    def build_features(self, interactions_df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
        """Processes raw customer interactions and returns engineered user-item features."""
        customer_logger.info("Starting Customer Feature Engineering Pipeline...")
        
        # 1. Apply weights and recency decay
        df = apply_interaction_weights(interactions_df)
        df = apply_recency_decay(df, self.lambda_decay)
        
        # 2. Compute user-item weighted interaction scores (affinity)
        # Score = Sum of (interaction_weight * decay_weight) per user-item pair
        df['event_score'] = df['interaction_weight'] * df['decay_weight']
        
        user_item_scores = df.groupby(['user_id', 'item_id'])['event_score'].sum().reset_index()
        user_item_scores.rename(columns={'event_score': 'weighted_score'}, inplace=True)
        
        # 3. Compile User Profiles
        # Average spend per user (from purchases)
        purchases = df[df['interaction_type'].str.lower() == 'purchase']
        user_spend = purchases.groupby('user_id')['price'].agg(['mean', 'count']).reset_index()
        user_spend.rename(columns={'mean': 'avg_spend', 'count': 'purchase_count'}, inplace=True)
        
        # Favorite categories (top 3 categories based on sum of scores)
        user_cat_scores = df.groupby(['user_id', 'category'])['event_score'].sum().reset_index()
        # Sort and rank favorite categories
        user_cat_scores['rank'] = user_cat_scores.groupby('user_id')['event_score'].rank(method='first', ascending=False)
        top_cats = user_cat_scores[user_cat_scores['rank'] <= 3].pivot(index='user_id', columns='rank', values='category').reset_index()
        # Rename columns to favorite_category_1, favorite_category_2, favorite_category_3
        cat_cols = {1: 'favorite_category_1', 2: 'favorite_category_2', 3: 'favorite_category_3'}
        top_cats.rename(columns=cat_cols, inplace=True)
        
        # Recency score (days since last customer interaction)
        timestamps = pd.to_datetime(df['interaction_timestamp'])
        max_ts = timestamps.max()
        user_recency = df.groupby('user_id')['interaction_timestamp'].max().reset_index()
        user_recency['recency_days'] = (max_ts - pd.to_datetime(user_recency['interaction_timestamp'])).dt.total_seconds() / (24 * 3600)
        user_recency.drop(columns=['interaction_timestamp'], inplace=True)
        
        # Join user features
        user_features = pd.merge(user_recency, top_cats, on='user_id', how='left')
        user_features = pd.merge(user_features, user_spend, on='user_id', how='left')
        user_features['avg_spend'] = user_features['avg_spend'].fillna(0.0)
        user_features['purchase_count'] = user_features['purchase_count'].fillna(0).astype(int)
        
        # 4. Compile Product / Item Profiles
        # Global popularity (interaction count and avg event score)
        item_pop = df.groupby('item_id')['event_score'].agg(['count', 'sum']).reset_index()
        item_pop.rename(columns={'count': 'item_interaction_count', 'sum': 'item_score_sum'}, inplace=True)
        
        # Merge product characteristics
        product_info = products_df[['product_id', 'category', 'price']].rename(columns={'product_id': 'item_id', 'category': 'product_category'})
        item_features = pd.merge(product_info, item_pop, on='item_id', how='left')
        item_features['item_interaction_count'] = item_features['item_interaction_count'].fillna(0).astype(int)
        item_features['item_score_sum'] = item_features['item_score_sum'].fillna(0.0)
        
        # 5. Repeated purchase score per user-item pair
        # How many times user purchased this item
        user_item_purchases = purchases.groupby(['user_id', 'item_id']).size().reset_index(name='repeated_purchase_count')
        
        # 6. Merge everything into a comprehensive user-item Feature Frame
        features = pd.merge(user_item_scores, user_features, on='user_id', how='left')
        features = pd.merge(features, item_features, on='item_id', how='left')
        features = pd.merge(features, user_item_purchases, on=['user_id', 'item_id'], how='left')
        features['repeated_purchase_count'] = features['repeated_purchase_count'].fillna(0).astype(int)
        
        customer_logger.info(f"Customer feature compilation complete. Created {len(features)} feature rows.")
        return features
