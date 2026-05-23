from sqlalchemy import Column, Integer, String, Float, DateTime, func
from shared.database.connection import Base

class Interaction(Base):
    __tablename__ = "interactions"

    interaction_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_type = Column(String(20), nullable=False) # 'customer' or 'owner'
    user_id = Column(Integer, nullable=False, index=True)
    item_id = Column(Integer, nullable=False, index=True)
    item_type = Column(String(20), nullable=False) # 'product' or 'raw_material'
    interaction_type = Column(String(50), nullable=False) # 'view', 'purchase', 'reorder', 'click'
    category = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Float, nullable=False)
    interaction_timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    def to_dict(self):
        """Converts ORM record into dict format for serializing/features."""
        return {
            "interaction_id": self.interaction_id,
            "user_type": self.user_type,
            "user_id": self.user_id,
            "item_id": self.item_id,
            "item_type": self.item_type,
            "interaction_type": self.interaction_type,
            "category": self.category,
            "quantity": self.quantity,
            "price": self.price,
            "interaction_timestamp": self.interaction_timestamp.isoformat() if self.interaction_timestamp else None
        }
