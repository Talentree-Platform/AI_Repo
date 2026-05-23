from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from customer_recommender.api.schemas import (
    CustomerRecommendRequest, 
    CustomerRecommendResponse, 
    CustomerRetrainResponse
)
from customer_recommender.services.recommender_service import customer_service
from customer_recommender.retraining.pipeline import run_retraining_pipeline
from shared.utils.logger import customer_logger

router = APIRouter(prefix="/customer", tags=["Customer Recommendation System"])

@router.get("/health")
async def health_check():
    """Simple service status endpoint."""
    model_status = "active" if customer_service.model is not None else "fallback_popular"
    return {
        "status": "healthy",
        "service": "customer_recommender",
        "model_status": model_status
    }

@router.post("/recommend", response_model=CustomerRecommendResponse)
async def get_customer_recommendations(request: CustomerRecommendRequest):
    """
    Computes hybrid user-item and content-based recommendation lists for a customer.
    Falls back to global popular products if user is not in database.
    """
    customer_logger.info(f"API request: customer_id={request.customer_id}, top_k={request.top_k}")
    
    try:
        recs = customer_service.get_recommendations(
            customer_id=request.customer_id, 
            top_k=request.top_k
        )
        
        info = customer_service.get_model_info()
        model_ver = info.get("last_modified", "v1")
        
        return CustomerRecommendResponse(
            customer_id=request.customer_id,
            recommendations=recs,
            model_version=str(model_ver)
        )
    except Exception as e:
        customer_logger.error(f"Error computing recommendations for customer {request.customer_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal recommendation compilation failure")

@router.get("/model-info")
async def get_model_info():
    """Returns currently loaded model state variables and active parameter specifications."""
    return customer_service.get_model_info()

@router.post("/retrain")
async def trigger_retraining(background_tasks: BackgroundTasks):
    """
    Triggers online retraining as a background task. 
    Prevents API requests from being blocked during model compilation.
    """
    customer_logger.info("Online retraining triggered via API endpoint.")
    
    # Run the retraining pipeline asynchronously
    background_tasks.add_task(run_retraining_pipeline)
    
    return {
        "success": True,
        "message": "Customer model retraining started in the background."
    }
