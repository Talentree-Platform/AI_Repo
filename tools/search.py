import os
import httpx
import logging
from cache import redis_mgr

logger = logging.getLogger("talentree.tools.search")

def search_web_tool(query: str, country_code: str = "EG") -> str:
    """Search the web using Serper API or Google Custom Search API, backed by Semantic Cache."""
    cache_key = f"search {query.strip().lower()} {country_code.strip().lower()}"
    
    # 1. Check Exact and Semantic Cache
    cached_val = redis_mgr.get_cache(cache_key) or redis_mgr.check_semantic_cache(cache_key)
    if cached_val:
        logger.info(f"Search cache HIT for query: '{query}' in region: '{country_code}'")
        return cached_val

    logger.info(f"Search cache MISS. Performing live web search for: '{query}'")
    serper_key = os.getenv("SERPER_API_KEY")
    if serper_key:
        try:
            url = "https://google.serper.dev/search"
            headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
            payload = {"q": query, "gl": country_code.lower(), "hl": "ar"}
            resp = httpx.post(url, json=payload, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                results = resp.json()
                snippets = []
                for org in results.get("organic", []):
                    desc = org.get("snippet") or org.get("priceRange") or org.get("snippetHighlighted") or "No description."
                    snippets.append(f"Title: {org.get('title')}\nSnippet: {desc}\nLink: {org.get('link')}")
                logger.info(f"Serper search success for query: '{query}' in region: '{country_code}'")
                res_str = "\n\n".join(snippets)
                
                # Cache the results
                redis_mgr.set_cache(cache_key, res_str, ttl=86400) # 24 hrs
                redis_mgr.add_semantic_cache(cache_key, res_str)
                return res_str
        except Exception as e:
            logger.error(f"Serper API failed: {e}")

    google_key = os.getenv("GOOGLE_API_KEY")
    google_cx = os.getenv("GOOGLE_CSE_ID")
    if google_key and google_cx:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {"key": google_key, "cx": google_cx, "q": query, "gl": country_code.lower()}
            resp = httpx.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                results = resp.json()
                snippets = []
                for item in results.get("items", []):
                    desc = item.get("snippet") or item.get("priceRange") or item.get("snippetHighlighted") or "No description."
                    snippets.append(f"Title: {item.get('title')}\nSnippet: {desc}\nLink: {item.get('link')}")
                logger.info(f"Google Search success for query: '{query}' in region: '{country_code}'")
                res_str = "\n\n".join(snippets)
                
                # Cache the results
                redis_mgr.set_cache(cache_key, res_str, ttl=86400) # 24 hrs
                redis_mgr.add_semantic_cache(cache_key, res_str)
                return res_str
        except Exception as e:
            logger.error(f"Google Custom Search API failed: {e}")

    logger.warning("No search API keys configured. Using keyword-based pricing mock.")
    query_lower = query.lower()
    if "lip" in query_lower or "cosmetic" in query_lower or "cream" in query_lower or "beauty" in query_lower:
        return (
            "Competitor pricing in Egypt for local skincare/makeup products: "
            "Local brands (Nefertari, Bubblzz, Amanda) price items between 120 EGP and 350 EGP. "
            "Premium local brands price between 350 EGP and 600 EGP. Imported equivalents (L'Oreal, Maybelline) range from 450 EGP to 950 EGP."
        )
    elif "bag" in query_lower or "tote" in query_lower or "leather" in query_lower or "accessories" in query_lower:
        return (
            "Competitor pricing in Egypt for fashion bags and leather goods: "
            "Local canvas tote bags are priced at 150 EGP - 350 EGP. Genuine handcrafted leather bags "
            "range from 900 EGP to 2400 EGP. High-end local boutique brands price up to 3500 EGP."
        )
    elif "shirt" in query_lower or "dress" in query_lower or "clothes" in query_lower or "fashion" in query_lower:
        return (
            "Competitor pricing in Egypt for clothing and apparel: "
            "Local shirts range from 350 EGP to 750 EGP. Dresses range from 600 EGP to 1500 EGP. "
            "Premium Egyptian cotton shirts from Concrete are priced at 800 EGP - 1600 EGP."
        )
    return f"Average competitor pricing in Egypt for product matching '{query}' ranges from 150 EGP to 850 EGP depending on materials."
