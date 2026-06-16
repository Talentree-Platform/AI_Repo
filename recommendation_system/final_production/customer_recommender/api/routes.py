from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from customer_recommender.api.schemas import (
    CustomerRecommendRequest, 
    CustomerRecommendResponse, 
    CustomerRetrainResponse
)
from customer_recommender.services.recommender_service import customer_service
from customer_recommender.retraining.pipeline import run_retraining_pipeline
from shared.utils.logger import customer_logger
from shared.auth.dependencies import get_current_user_id

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

@router.get("/list")
async def get_customers_list():
    """Fetches a list of B2C customers from remote SQL database or local demo fallback."""
    from shared.database.connection import engine
    import pandas as pd
    
    if engine is not None:
        try:
            cust_query = """
                SELECT u.Id as user_id, u.DisplayName as name
                FROM AspNetUsers u 
                JOIN AspNetUserRoles ur ON u.Id = ur.UserId 
                WHERE ur.RoleId = '8cdb5170-bc99-483e-b7fc-b9e394e09c69'
            """
            df = pd.read_sql(cust_query, engine)
            if len(df) > 0:
                return df.to_dict(orient="records")
        except Exception as e:
            customer_logger.warning(f"Failed to query customers from SQL DB: {e}. Falling back to demo data.")
            
    # Local fallback demo list (with active pre-trained synthetic IDs and names)
    return [
        {"user_id": "123", "name": "Active Demo User #123 (Fashion enthusiast)"},
        {"user_id": "456", "name": "Active Demo User #456 (Crafts lover)"},
        {"user_id": "789", "name": "Active Demo User #789 (Natural beauty buyer)"},
        {"user_id": "297", "name": "Demo User #297"},
        {"user_id": "106", "name": "Demo User #106"},
        {"user_id": "415", "name": "Demo User #415"},
    ]

@router.post("/recommend", response_model=CustomerRecommendResponse)
async def get_customer_recommendations(
    request: CustomerRecommendRequest,
    customer_id: str = Depends(get_current_user_id)
):
    """
    Computes hybrid user-item and content-based recommendation lists for a customer.
    The customer identity is extracted server-side from the validated JWT Bearer token.
    Falls back to global popular products if user is not in database.
    """
    customer_logger.info(f"API request: customer_id={customer_id}, top_k={request.top_k}")
    
    try:
        recs = customer_service.get_recommendations(
            customer_id=customer_id, 
            top_k=request.top_k
        )
        
        info = customer_service.get_model_info()
        model_ver = info.get("last_modified", "v1")
        
        return CustomerRecommendResponse(
            customer_id=customer_id,
            recommendations=recs,
            model_version=str(model_ver)
        )
    except Exception as e:
        customer_logger.error(f"Error computing recommendations for customer {customer_id}: {e}")
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
