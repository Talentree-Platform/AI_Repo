import numpy as np
import pandas as pd

def apply_recency_decay(df: pd.DataFrame, lambda_decay: float = 0.003) -> pd.DataFrame:
    """Calculates exponential time-decay weight for interactions.
    
    Formula: decay_weight = exp(-lambda * days_since_interaction)
    Default lambda is smaller (0.003) to decay slower for procurement calendars.
    """
    df = df.copy()
    
    if 'interaction_timestamp' not in df.columns:
        df['decay_weight'] = 1.0
        return df
        
    timestamps = pd.to_datetime(df['interaction_timestamp'])
    max_ts = timestamps.max()
    
    days_since = (max_ts - timestamps).dt.total_seconds() / (24 * 3600)
    df['decay_weight'] = np.exp(-lambda_decay * days_since)
    
    return df
