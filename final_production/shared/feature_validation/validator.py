import pandas as pd
from shared.utils.logger import db_logger

class FeatureValidationError(ValueError):
    """Custom exception raised when features fail validation checks."""
    pass

class FeatureValidator:
    """Performs schema, quality, boundary, and integrity checks on engineered features before storage and model training."""
    
    @staticmethod
    def validate_customer_features(df: pd.DataFrame) -> bool:
        """Validates engineered B2C customer features."""
        db_logger.info("Validating Customer Features...")
        
        # 1. Required Columns Check
        required_cols = ['user_id', 'item_id', 'weighted_score', 'recency_days']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise FeatureValidationError(f"Missing required feature columns: {missing_cols}")
            
        # 2. Duplicate Check
        if df.duplicated(subset=['user_id', 'item_id']).any():
            dupe_count = df.duplicated(subset=['user_id', 'item_id']).sum()
            raise FeatureValidationError(f"Duplicate user-item records detected! Found {dupe_count} duplicate pairs.")
            
        # 3. ID Validation
        if (df['user_id'] < 0).any() or (df['item_id'] < 0).any():
            raise FeatureValidationError("Invalid user_id or item_id detected (negative values not allowed).")
            
        # 4. Null checks on critical identifiers
        null_user = df['user_id'].isna().sum()
        null_item = df['item_id'].isna().sum()
        if null_user > 0 or null_item > 0:
            raise FeatureValidationError(f"Null identifiers detected! null user_ids={null_user}, null item_ids={null_item}")
            
        # 5. Score Boundaries
        if (df['weighted_score'] < 0).any():
            raise FeatureValidationError("Invalid negative weighted interaction scores detected.")
            
        # 6. Recency Boundaries
        if (df['recency_days'] < 0).any():
            raise FeatureValidationError("Invalid negative recency_days detected.")
            
        db_logger.info("Customer Features validation passed successfully!")
        return True

    @staticmethod
    def validate_owner_features(df: pd.DataFrame) -> bool:
        """Validates engineered B2B owner features."""
        db_logger.info("Validating Owner Features...")
        
        # 1. Required Columns Check
        required_cols = ['user_id', 'item_id', 'weighted_score', 'avg_procurement_interval_days']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise FeatureValidationError(f"Missing required feature columns: {missing_cols}")
            
        # 2. Duplicate Check
        if df.duplicated(subset=['user_id', 'item_id']).any():
            dupe_count = df.duplicated(subset=['user_id', 'item_id']).sum()
            raise FeatureValidationError(f"Duplicate owner-item records detected! Found {dupe_count} duplicate pairs.")
            
        # 3. ID Validation
        if (df['user_id'] < 0).any() or (df['item_id'] < 0).any():
            raise FeatureValidationError("Invalid user_id or item_id detected (negative values not allowed).")
            
        # 4. Procurement quantities must be positive
        if 'avg_procurement_quantity' in df.columns:
            if (df['avg_procurement_quantity'] < 0).any():
                raise FeatureValidationError("Negative average procurement quantities detected.")
                
        # 5. Interval boundaries must be positive
        if (df['avg_procurement_interval_days'] < 0).any():
            raise FeatureValidationError("Negative average procurement interval days detected.")
            
        db_logger.info("Owner Features validation passed successfully!")
        return True
