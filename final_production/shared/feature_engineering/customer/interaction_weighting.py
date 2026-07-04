import pandas as pd

INTERACTION_WEIGHTS = {
    "view": 1.0,
    "click": 2.0,
    "add_to_cart": 3.0,
    "purchase": 5.0,
    "reorder": 7.0
}

def apply_interaction_weights(df: pd.DataFrame) -> pd.DataFrame:
    """Adds a standard 'interaction_weight' column based on 'interaction_type'."""
    df = df.copy()
    
    # Lowercase interaction types
    df['interaction_type_lower'] = df['interaction_type'].str.lower().str.strip()
    
    # Map weights, default to 1.0 if not found
    df['interaction_weight'] = df['interaction_type_lower'].map(INTERACTION_WEIGHTS).fillna(1.0)
    
    # Drop temporary column
    df = df.drop(columns=['interaction_type_lower'])
    
    return df
