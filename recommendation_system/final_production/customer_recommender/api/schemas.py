from pydantic import BaseModel, Field

class CustomerRecommendRequest(BaseModel):
    customer_id: int = Field(..., description="Unique customer identifier", example=123)
    top_k: int = Field(default=5, ge=1, le=50, description="Number of product recommendations to return", example=5)

class ProductRecommendation(BaseModel):
    product_id: int
    product_name: str
    category: str
    price: float
    description: str
    score: float

class CustomerRecommendResponse(BaseModel):
    customer_id: int
    recommendations: list[ProductRecommendation]
    model_version: str

class CustomerRetrainResponse(BaseModel):
    success: bool
    message: str
    precision_at_5: float
