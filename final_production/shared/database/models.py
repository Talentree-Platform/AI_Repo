from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, func
from shared.database.connection import Base

# ---------------------------------------------------------------------------
# Enum value maps — mirror the backend C# enums exactly
# ---------------------------------------------------------------------------
_USER_TYPE_MAP   = {0: "customer", 1: "owner", 2: "supplier"}
_ITEM_TYPE_MAP   = {0: "product",  1: "raw_material"}
_ACTION_TYPE_MAP = {0: "view",     1: "click",  2: "purchase", 3: "reorder"}

# Reverse maps — used when seeding / writing back to DB
_USER_TYPE_INT   = {v: k for k, v in _USER_TYPE_MAP.items()}
_ITEM_TYPE_INT   = {v: k for k, v in _ITEM_TYPE_MAP.items()}
_ACTION_TYPE_INT = {v: k for k, v in _ACTION_TYPE_MAP.items()}

# Category ID → Name lookup (matches backend seeding map)
_PRODUCT_CATEGORY_MAP = {
    1: "Fashion & Accessories",
    2: "Handmade & Crafts",
    3: "Natural & Beauty Products",
}


class Interaction(Base):
    """
    Maps to the backend 'UserInteractions' SQL Server table.
    UserType, ItemType, ActionType are stored as integers (C# enums).
    to_dict() converts them back to the internal string names used by the ML pipeline.
    """
    __tablename__ = "UserInteractions"

    # Python attr name      DB column name         Type
    interaction_id        = Column("Id",                   Integer,  primary_key=True, index=True, autoincrement=True)
    user_id               = Column("UserId",               Integer,  nullable=False, index=True)
    user_type             = Column("UserType",             Integer,  nullable=False)   # 0=customer, 1=owner, 2=supplier
    item_id               = Column("ItemId",               Integer,  nullable=False, index=True)
    item_type             = Column("ItemType",             Integer,  nullable=False)   # 0=product, 1=raw_material
    interaction_type      = Column("ActionType",           Integer,  nullable=False)   # 0=view, 1=click, 2=purchase, 3=reorder
    category              = Column("Category",             String(100), nullable=False)
    quantity              = Column("Quantity",             Integer,  nullable=False, default=1)
    price                 = Column("Price",                Float,    nullable=False)
    interaction_timestamp = Column("InteractionTimestamp", DateTime, nullable=False, index=True, server_default=func.now())
    created_at            = Column("CreatedAt",            DateTime, nullable=False, server_default=func.now())

    def to_dict(self):
        """Converts ORM record into dict using internal ML-friendly string names."""
        return {
            "interaction_id":        self.interaction_id,
            "user_id":               self.user_id,
            "user_type":             _USER_TYPE_MAP.get(self.user_type, str(self.user_type)),
            "item_id":               self.item_id,
            "item_type":             _ITEM_TYPE_MAP.get(self.item_type, str(self.item_type)),
            "interaction_type":      _ACTION_TYPE_MAP.get(self.interaction_type, str(self.interaction_type)),
            "category":              self.category,
            "quantity":              self.quantity,
            "price":                 self.price,
            "interaction_timestamp": self.interaction_timestamp.isoformat() if self.interaction_timestamp else None,
            "created_at":            self.created_at.isoformat() if self.created_at else None,
        }


class Product(Base):
    """
    Maps to the backend 'Products' SQL Server table.
    Reads Id, Name, Price, Description, CategoryId from DB.
    to_dict() resolves CategoryId → category string so the ML pipeline
    continues to receive the 'category' string column it expects.
    """
    __tablename__ = "Products"

    product_id   = Column("Id",          Integer,      primary_key=True, index=True)
    product_name = Column("Name",         String(150),  nullable=False)
    price        = Column("Price",        Float,        nullable=False)
    description  = Column("Description",  String(500),  nullable=True)
    category_id  = Column("CategoryId",   Integer,      nullable=True)   # FK to Categories table

    def to_dict(self):
        """
        Converts ORM record into ML-ready dict.
        CategoryId is resolved to the category string so feature engineering
        code that reads df['category'] continues to work without any changes.
        """
        return {
            "product_id":   self.product_id,
            "product_name": self.product_name,
            "category":     _PRODUCT_CATEGORY_MAP.get(self.category_id, "Unknown"),
            "price":        self.price,
            "description":  self.description or "",
        }


class RawMaterial(Base):
    """
    Maps to the backend 'RawMaterials' SQL Server table.
    The real table stores Category as a string directly (no FK).
    """
    __tablename__ = "RawMaterials"

    material_id   = Column("Id",          Integer,     primary_key=True, index=True)
    material_name = Column("Name",         String(150), nullable=False)
    category      = Column("Category",     String(100), nullable=False)
    price         = Column("Price",        Float,       nullable=False)
    description   = Column("Description",  String(500), nullable=True)

    def to_dict(self):
        """Converts ORM record into ML-ready dict using internal field names."""
        return {
            "material_id":   self.material_id,
            "material_name": self.material_name,
            "category":      self.category,
            "price":         self.price,
            "description":   self.description or "",
        }
