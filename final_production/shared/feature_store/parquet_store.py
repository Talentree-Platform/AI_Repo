import os
import glob
import pandas as pd
from typing import List, Optional
from shared.config.settings import settings
from shared.utils.logger import db_logger

class ParquetFeatureStore:
    """Enterprise-style versioned Parquet feature store."""
    
    def __init__(self):
        self.store_dir = settings.FEATURE_STORE_DIR
        os.makedirs(self.store_dir, exist_ok=True)
        db_logger.info(f"Initialized Parquet Feature Store at: {self.store_dir}")

    def _get_file_path(self, name: str, version: int) -> str:
        """Returns path for a specific feature dataset and version."""
        return os.path.join(self.store_dir, f"{name}_v{version}.parquet")

    def save_features(self, df: pd.DataFrame, name: str) -> int:
        """Saves a feature DataFrame, automatically incrementing the version number.
        
        Returns the version number saved.
        """
        # Determine next version
        latest_ver = self.get_latest_version_number(name)
        next_ver = latest_ver + 1
        
        path = self._get_file_path(name, next_ver)
        
        db_logger.info(f"Saving '{name}' features version {next_ver} to {path}...")
        
        try:
            # We save as parquet. Requires pyarrow or fastparquet.
            df.to_parquet(path, index=False)
            db_logger.info(f"Successfully saved {len(df)} feature rows to parquet.")
            return next_ver
        except ImportError as ie:
            db_logger.error("Missing dependency for Parquet export. Please run 'pip install pyarrow'")
            # If pyarrow is missing, we raise an ImportError with a clear message
            raise ImportError("Parquet file support requires 'pyarrow' or 'fastparquet'. Run 'pip install pyarrow'") from ie
        except Exception as e:
            db_logger.error(f"Error saving features to Parquet: {e}")
            raise e

    def load_features(self, name: str, version: Optional[int] = None) -> pd.DataFrame:
        """Loads features for a specific name and version.
        
        If version is None, loads the latest version.
        """
        if version is None:
            version = self.get_latest_version_number(name)
            if version == 0:
                raise FileNotFoundError(f"No feature datasets found in store for name '{name}'")
                
        path = self._get_file_path(name, version)
        
        db_logger.info(f"Loading '{name}' features version {version} from {path}...")
        
        if not os.path.exists(path):
            db_logger.error(f"Feature path does not exist: {path}")
            raise FileNotFoundError(f"Feature dataset {name} version {version} not found.")
            
        try:
            df = pd.read_parquet(path)
            db_logger.info(f"Loaded {len(df)} features from {path}")
            return df
        except Exception as e:
            db_logger.error(f"Error loading features from Parquet: {e}")
            raise e

    def get_latest_version_number(self, name: str) -> int:
        """Scans the directory and returns the highest version number discovered for this dataset."""
        pattern = os.path.join(self.store_dir, f"{name}_v*.parquet")
        files = glob.glob(pattern)
        
        if not files:
            return 0
            
        versions = []
        for f in files:
            basename = os.path.basename(f)
            # Extrapolate version number from name_v{version}.parquet
            try:
                ver_str = basename.replace(f"{name}_v", "").replace(".parquet", "")
                versions.append(int(ver_str))
            except ValueError:
                continue
                
        return max(versions) if versions else 0

    def list_versions(self, name: str) -> List[int]:
        """Lists all version numbers available for a dataset."""
        pattern = os.path.join(self.store_dir, f"{name}_v*.parquet")
        files = glob.glob(pattern)
        
        versions = []
        for f in files:
            basename = os.path.basename(f)
            try:
                ver_str = basename.replace(f"{name}_v", "").replace(".parquet", "")
                versions.append(int(ver_str))
            except ValueError:
                continue
                
        return sorted(versions)
