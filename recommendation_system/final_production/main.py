import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from shared.config.settings import settings
from shared.utils.logger import api_logger
from shared.database.connection import check_db_connection

# Import routes
from customer_recommender.api.routes import router as customer_router
from owner_recommender.api.routes import router as owner_router

# Import services to trigger boot loading
from customer_recommender.services.recommender_service import customer_service
from owner_recommender.services.recommender_service import owner_service

# Initialize FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-Grade Enterprise Dual Recommendation System Service (FastAPI + SQL Server + MLflow + Docker)",
    version="1.0.0"
)

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directories if they don't exist
os.makedirs("customer_recommender/static/css", exist_ok=True)
os.makedirs("customer_recommender/static/js", exist_ok=True)
os.makedirs("owner_recommender/static/css", exist_ok=True)
os.makedirs("owner_recommender/static/js", exist_ok=True)
os.makedirs("customer_recommender/templates", exist_ok=True)
os.makedirs("owner_recommender/templates", exist_ok=True)

# Mount static files
app.mount("/customer-static", StaticFiles(directory="customer_recommender/static"), name="customer_static")
app.mount("/owner-static", StaticFiles(directory="owner_recommender/static"), name="owner_static")

# Configure independent template handlers
customer_templates = Jinja2Templates(directory="customer_recommender/templates")
owner_templates = Jinja2Templates(directory="owner_recommender/templates")

# Include sub-routers
app.include_router(customer_router)
app.include_router(owner_router)

@app.on_event("startup")
async def startup_event():
    """Startup operations: logs status, checks models and validates DB."""
    api_logger.info("Initializing Enterprise Recommendation Service startup hooks...")
    
    # Verify model presence or trigger fallbacks
    customer_loaded = customer_service.load_model()
    owner_loaded = owner_service.load_model()
    
    db_status = "Connected" if check_db_connection() else "Disconnected/Local Flat Files Only"
    
    api_logger.info(f"Startup check complete:")
    api_logger.info(f"  SQL Server Database: {db_status}")
    api_logger.info(f"  Customer Recommendation Model Active: {customer_loaded}")
    api_logger.info(f"  Owner Recommendation Model Active: {owner_loaded}")

@app.get("/health")
async def global_health():
    """API health status endpoint checks system state and databases."""
    db_ok = check_db_connection()
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENV,
        "database_connected": db_ok,
        "customer_model_loaded": customer_service.model is not None,
        "owner_model_loaded": owner_service.model is not None
    }

# ----------------------------------------------------
# DASHBOARD FRONTEND ROUTING
# ----------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def main_landing(request: Request):
    """Sleek corporate portal page redirecting to customer and owner dashboards."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Talentree Platform | AI recommendation portal</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-primary: #0a0e17;
                --bg-card: rgba(16, 24, 40, 0.7);
                --text-primary: #ffffff;
                --text-secondary: #94a3b8;
                --accent-customer: #3b82f6;
                --accent-owner: #10b981;
                --border-color: rgba(255, 255, 255, 0.08);
            }
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
            body {
                font-family: 'Outfit', sans-serif;
                background-color: var(--bg-primary);
                color: var(--text-primary);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                background-image: 
                    radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.05) 0%, transparent 40%),
                    radial-gradient(circle at 90% 80%, rgba(16, 115, 81, 0.05) 0%, transparent 40%);
                padding: 20px;
            }
            .container {
                max-width: 1000px;
                width: 100%;
                text-align: center;
            }
            .header {
                margin-bottom: 50px;
            }
            .header h1 {
                font-size: 2.8rem;
                font-weight: 800;
                letter-spacing: -0.03em;
                margin-bottom: 12px;
                background: linear-gradient(135deg, #ffffff 30%, #94a3b8 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .header p {
                font-size: 1.1rem;
                color: var(--text-secondary);
                max-width: 600px;
                margin: 0 auto;
                line-height: 1.6;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 30px;
                margin-bottom: 40px;
            }
            .card {
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 20px;
                padding: 40px 30px;
                text-align: left;
                transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
                backdrop-filter: blur(16px);
                position: relative;
                overflow: hidden;
            }
            .card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 4px;
                transition: all 0.4s ease;
            }
            .card.customer::before {
                background: linear-gradient(90deg, var(--accent-customer), #60a5fa);
            }
            .card.owner::before {
                background: linear-gradient(90deg, var(--accent-owner), #34d399);
            }
            .card:hover {
                transform: translateY(-8px);
                border-color: rgba(255, 255, 255, 0.15);
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            }
            .card-title {
                font-size: 1.6rem;
                font-weight: 600;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .card-desc {
                color: var(--text-secondary);
                line-height: 1.6;
                margin-bottom: 30px;
                font-size: 0.95rem;
                height: 70px;
            }
            .btn {
                display: inline-block;
                width: 100%;
                padding: 14px 24px;
                border-radius: 12px;
                font-weight: 600;
                text-decoration: none;
                text-align: center;
                transition: all 0.3s ease;
                font-size: 0.95rem;
            }
            .card.customer .btn {
                background: var(--accent-customer);
                color: #ffffff;
            }
            .card.customer .btn:hover {
                background: #2563eb;
                box-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
            }
            .card.owner .btn {
                background: var(--accent-owner);
                color: #ffffff;
            }
            .card.owner .btn:hover {
                background: #059669;
                box-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
            }
            .footer {
                color: rgba(255, 255, 255, 0.3);
                font-size: 0.85rem;
                margin-top: 30px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Enterprise Recommendation Engine</h1>
                <p>Decoupled multi-pipeline MLOps platform serving hybrid B2C customer catalog selections and business intelligent cyclical procurement forecasts.</p>
            </div>
            
            <div class="grid">
                <div class="card customer">
                    <h3 class="card-title">🛒 Customer Product Portal</h3>
                    <p class="card-desc">B2C Product Recommendation System leveraging Item-Item Collaborative Similarity and TF-IDF Content weighting with Precision@K validation checks.</p>
                    <a href="/customer-ui" class="btn">Launch Customer Console →</a>
                </div>
                
                <div class="card owner">
                    <h3 class="card-title">💼 Business Procurement</h3>
                    <p class="card-desc">B2B Raw Material Procurement planning tool analyzing reorder calendars, purchase cycle durations, and multi-period aggregated Ridge demand forecasting.</p>
                    <a href="/owner-ui" class="btn">Launch Procurement Console →</a>
                </div>
            </div>
            
            <div class="footer">
                Talentree AI Platform © 2026 | Production Grade MLOps Architecture
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/customer-ui", response_class=HTMLResponse)
async def serve_customer_ui(request: Request):
    """Serves the Customer Dashboard Jinja2 HTML page."""
    return customer_templates.TemplateResponse("customer_ui.html", {"request": request})

@app.get("/owner-ui", response_class=HTMLResponse)
async def serve_owner_ui(request: Request):
    """Serves the Business Owner Dashboard Jinja2 HTML page."""
    return owner_templates.TemplateResponse("owner_ui.html", {"request": request})
