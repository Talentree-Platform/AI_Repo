from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from owner_recommender.api.schemas import (
    OwnerRecommendRequest, 
    OwnerRecommendResponse
)
from owner_recommender.services.recommender_service import owner_service
from owner_recommender.retraining.pipeline import run_owner_retraining_pipeline
from shared.utils.logger import owner_logger
from shared.auth.dependencies import get_current_user_id

router = APIRouter(prefix="/owner", tags=["Business Owner Procurement Recommendation System"])

@router.get("/health")
async def health_check():
    """Simple service status endpoint."""
    model_status = "active" if owner_service.model is not None else "fallback_popular"
    return {
        "status": "healthy",
        "service": "owner_recommender",
        "model_status": model_status
    }

@router.get("/list")
async def get_owners_list():
    """Fetches a list of business owners from remote SQL database or local demo fallback."""
    from shared.database.connection import engine
    import pandas as pd
    
    if engine is not None:
        try:
            owner_query = """
                SELECT Id as owner_id, BusinessName as name 
                FROM BusinessOwnerProfile 
                WHERE IsDeleted = 0
            """
            df = pd.read_sql(owner_query, engine)
            if len(df) > 0:
                # Convert owner_id to string for uniform UI parsing
                df["owner_id"] = df["owner_id"].astype(str)
                return df.to_dict(orient="records")
        except Exception as e:
            owner_logger.warning(f"Failed to query owners from SQL DB: {e}. Falling back to demo data.")
            
    # Local fallback demo list (with active pre-trained synthetic IDs and names)
    return [
        {"owner_id": "1", "name": "Tech Galaxy (Owner #1)"},
        {"owner_id": "2", "name": "Fashion House (Owner #2)"},
        {"owner_id": "3", "name": "Fresh Mart (Owner #3)"},
        {"owner_id": "33", "name": "Active Demo Owner #33"},
        {"owner_id": "55", "name": "Active Demo Owner #55"},
        {"owner_id": "76", "name": "Active Demo Owner #76"},
    ]

@router.post("/recommend", response_model=OwnerRecommendResponse)
async def get_owner_recommendations(
    request: OwnerRecommendRequest,
    owner_id: str = Depends(get_current_user_id)
):
    """
    Computes procurement recommendations for a business owner.
    The owner identity is extracted server-side from the validated JWT Bearer token.
    Ranks items based on cyclic interval calendars, demand quantity forecasting regressors, and history.
    """
    owner_logger.info(f"API request: owner_id={owner_id}, top_k={request.top_k}")
    
    try:
        recs = owner_service.get_recommendations(
            owner_id=owner_id, 
            top_k=request.top_k
        )
        
        info = owner_service.get_model_info()
        model_ver = info.get("last_modified", "v1")
        
        return OwnerRecommendResponse(
            owner_id=owner_id,
            recommendations=recs,
            model_version=str(model_ver)
        )
    except Exception as e:
        owner_logger.error(f"Error computing recommendations for owner {owner_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal recommendation compilation failure")

@router.get("/model-info")
async def get_model_info():
    """Returns currently loaded model state variables and active parameter specifications."""
    return owner_service.get_model_info()

@router.post("/retrain")
async def trigger_retraining(background_tasks: BackgroundTasks):
    """
    Triggers online retraining as a background task. 
    Prevents API requests from being blocked during model compilation.
    """
    owner_logger.info("Online retraining triggered via API endpoint.")
    
    # Run the retraining pipeline asynchronously
    background_tasks.add_task(run_owner_retraining_pipeline)
    
    return {
        "success": True,
        "message": "Owner model retraining started in the background."
    }
