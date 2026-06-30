import os
import logging
from dotenv import load_dotenv

# Load environments
load_dotenv()

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("talentree")

# Hugging Face token config
HF_TOKEN = os.getenv("HF_TOKEN")
if HF_TOKEN:
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = HF_TOKEN
    os.environ["HF_TOKEN"] = HF_TOKEN

# ==========================================
# MOCK DATABASE LAYER (REPLACING SQL SERVER)
# ==========================================
MOCK_PROFILES = {
    1: {
        "id": 1,
        "name": "Tech Galaxy",
        "category": "Electronics",
        "description": "Premium electronics store selling high-tech accessories and smart gadgets.",
        "website": "techgalaxy.com",
        "instagram": "@techgalaxy"
    },
    2: {
        "id": 2,
        "name": "Fashion House",
        "category": "Fashion",
        "description": "Elegant local boutique specializing in high-quality apparel and accessories.",
        "website": "fashionhouse.com",
        "instagram": "@fashionhouse"
    },
    3: {
        "id": 3,
        "name": "Fresh Mart",
        "category": "Food",
        "description": "Organic local grocer offering fresh fruits, vegetables, and local delicacies.",
        "website": "freshmart.com",
        "instagram": "@freshmart"
    }
}

MOCK_PRODUCTS = {
    1: [
        {"id": 101, "name": "Handwoven Cotton Tote Bag", "price": 189.99, "tags": "bag, cotton, local"},
        {"id": 102, "name": "Leather Strap Bracelet Set", "price": 149.99, "tags": "accessory, leather"},
        {"id": 103, "name": "Smart Watch Screen Protector", "price": 49.99, "tags": "electronics, gadget"}
    ],
    2: [
        {"id": 201, "name": "Embroidered Linen Scarf", "price": 250.00, "tags": "scarf, linen, fashion"},
        {"id": 202, "name": "Denim Crossbody Bag", "price": 320.00, "tags": "bag, denim, premium"}
    ],
    3: [
        {"id": 301, "name": "Organic Honey Jar", "price": 120.00, "tags": "honey, organic, local"},
        {"id": 302, "name": "Fresh Olive Oil Bottle", "price": 180.00, "tags": "oil, olive, premium"}
    ]
}

def fetch_all_business_profiles() -> list[dict]:
    """Returns all business profiles (forwarding to repository)."""
    from repositories.user_repository import get_all_business_profiles as repo_get_all
    return repo_get_all()

def fetch_profile_and_catalog(profile_id: int) -> dict:
    """Returns business profile and products for a given profile ID (forwarding to repository)."""
    from repositories.user_repository import get_profile_and_catalog as repo_get_one
    return repo_get_one(profile_id)
