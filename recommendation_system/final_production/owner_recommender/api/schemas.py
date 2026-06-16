from pydantic import BaseModel, Field

from typing import Any

class OwnerRecommendRequest(BaseModel):
    top_k: int = Field(default=6, ge=1, le=50, description="Number of material recommendations to return", example=6)

class MaterialRecommendation(BaseModel):
    material_id: int
    material_name: str
    category: str
    price: float
    description: str
    predicted_demand_qty: float
    urgency_days_elapsed: int
    urgency_cycle_days: int
    score: float

class OwnerRecommendResponse(BaseModel):
    owner_id: Any
    recommendations: list[MaterialRecommendation]
    model_version: str

class OwnerRetrainResponse(BaseModel):
    success: bool
    message: str
    owner_precision_at_5: float
