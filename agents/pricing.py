import logging
import re
import ast
import json
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage

from orchestrator.state import AgentState
from services.llm_service import chat_fast, chat_creative
from services.geo_service import detect_location_from_text
from services.search_service import search_web_tool
from prompts.pricing_prompt import (
    get_market_detection_prompt, 
    get_search_query_generation_prompt, 
    get_pricing_recommendation_prompt
)

logger = logging.getLogger("talentree.agents.pricing")

def detect_market_from_query(query: str, chat_model) -> dict:
    prompt_str = get_market_detection_prompt(query)
    try:
        prompt = PromptTemplate.from_template(prompt_str)
        chain = prompt | chat_model
        resp = chain.invoke({"user_query": query}).content.strip()
        
        match = re.search(r'\{.*\}', resp, re.DOTALL)
        if match:
            match_str = match.group(0).strip()
            try:
                data = ast.literal_eval(match_str)
            except Exception:
                try:
                    data = json.loads(match_str)
                except Exception:
                    data = None
            if data and isinstance(data, dict):
                if data.get("country") and data.get("country") != "DEFAULT":
                    return {
                        "country": data["country"],
                        "currency": data["currency"],
                        "country_code": data["country_code"]
                    }
        return None
    except Exception as e:
        logger.error(f"Error detecting market from query: {e}")
        return None

def parse_json_list(text: str) -> list:
    text = text.strip()
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    # Fallback line-by-line cleaner if JSON parsing fails
    lines = []
    for line in text.split('\n'):
        line_clean = line.strip().strip('"').strip("'").strip(',').strip('[]').strip()
        if line_clean and len(line_clean) > 3:
            lines.append(line_clean)
    return lines

def pricing_node(state: AgentState) -> dict:
    brand = state.get("brand_profile", {})
    category = brand.get("category", "Unknown")
    query = state.get("current_query", "")
    messages = state.get("messages", [])
    
    # 1. Override location context if target market is explicitly specified in the query
    detected_ctx = detect_market_from_query(query, chat_fast) or detect_location_from_text(query)
    if detected_ctx:
        logger.info(f"Explicit target market detected in query: {detected_ctx['country']} ({detected_ctx['currency']})")
        location_ctx = detected_ctx
    else:
        location_ctx = state.get("location_context", {"country": "Egypt", "country_code": "EG", "currency": "EGP"})
        
    country = location_ctx.get("country", "Egypt")
    currency = location_ctx.get("currency", "EGP")
    code = location_ctx.get("country_code", "EG")
    
    # 2. Generate search queries (competitor prices + potential currency exchange rate)
    detect_prompt = get_search_query_generation_prompt(query, country, currency)
    try:
        prompt_detect = PromptTemplate.from_template(detect_prompt)
        chain_detect = prompt_detect | chat_fast
        queries_json = chain_detect.invoke({
            "user_query": query, 
            "category": category,
            "country": country,
            "currency": currency
        }).content.strip()
        
        search_queries = parse_json_list(queries_json)
        if not search_queries:
            search_queries = [f"{category} competitor price in {country} {currency}"]
    except Exception as e:
        logger.error(f"Error generating search queries: {e}")
        search_queries = [f"{category} competitor price in {country} {currency}"]

    # 3. Execute search tool for all queries (limit to 3 to prevent rate limits)
    search_snippets = []
    for sq in search_queries[:3]:
        logger.info(f"Pricing Agent searching the web for: '{sq}' in country code '{code}'")
        res = search_web_tool(sq, code)
        if res:
            search_snippets.append(f"--- Search results for '{sq}': ---\n{res}")
            
    search_data = "\n\n".join(search_snippets) if search_snippets else "No competitor data found."
    
    is_ar = any(u'\u0600' <= char <= u'\u06FF' for char in query) if query else False
    if is_ar:
        lang_rule = "You MUST respond entirely in clear, professional Arabic. Do NOT reply in English."
    else:
        lang_rule = "You MUST respond entirely in English. Do NOT reply in Arabic."

    system_prompt = get_pricing_recommendation_prompt(
        country=country,
        currency=currency,
        search_data=search_data,
        brand_name=brand.get("name", "Unknown"),
        category=category,
        brand_desc=brand.get("description", "Unknown"),
        brand_tone=brand.get("tone", "Professional"),
        target_audience=brand.get("target_audience", "General public"),
        lang_rule=lang_rule
    )

    full_messages = [SystemMessage(content=system_prompt)] + messages
    resp = chat_creative.invoke(full_messages)
    return {"agent_output": resp.content.strip()}
