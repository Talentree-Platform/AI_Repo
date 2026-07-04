from pydantic import BaseModel, Field

from typing import Any

class CustomerRecommendRequest(BaseModel):
    customer_id: Any = Field(..., description="Unique customer identifier (integer ID or remote DB UUID)", example=123)
    top_k: int = Field(default=6, ge=1, le=50, description="Number of product recommendations to return", example=6)

class ProductRecommendation(BaseModel):
    product_id: int
    product_name: str
    category: str
    price: float
    description: str
    score: float

class CustomerRecommendResponse(BaseModel):
    customer_id: Any
    recommendations: list[ProductRecommendation]
    model_version: str

class CustomerRetrainResponse(BaseModel):
    success: bool
    message: str
    precision_at_5: float
