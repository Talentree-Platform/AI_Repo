from abc import ABC, abstractmethod
import pandas as pd

class BaseDataSource(ABC):
    """Abstract Base Class defining the contract for data sources in the Talentree Recommendation System."""
    
    @abstractmethod
    def load_customer_interactions(self) -> pd.DataFrame:
        """Loads and returns customer product interaction data."""
        pass
        
    @abstractmethod
    def load_owner_interactions(self) -> pd.DataFrame:
        """Loads and returns owner procurement interaction data."""
        pass
        
    @abstractmethod
    def load_products(self) -> pd.DataFrame:
        """Loads and returns product catalog data."""
        pass
        
    @abstractmethod
    def load_raw_materials(self) -> pd.DataFrame:
        """Loads and returns raw materials catalog data."""
        pass
