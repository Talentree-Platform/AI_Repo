import httpx
import logging

logger = logging.getLogger("talentree.services.geolocation")

def get_ip_location(ip: str) -> dict:
    """Detect country and currency dynamically using IP Geolocation API."""
    # Fallback to public IP if client is local for testing dynamically from local environment
    if not ip or ip in ("127.0.0.1", "localhost", "::1", "testclient") or ip.startswith("192.168.") or ip.startswith("10."):
        try:
            resp = httpx.get("https://api.ipify.org?format=json", timeout=2.0)
            if resp.status_code == 200:
                resolved_ip = resp.json().get("ip")
                if resolved_ip:
                    ip = resolved_ip
                    logger.info(f"Localhost/Private IP fallback: Using public IP {ip} for location detection.")
        except Exception as e:
            logger.warning(f"Could not resolve public IP for local testing fallback: {e}")

    if not ip or ip in ("127.0.0.1", "localhost", "::1", "testclient") or ip.startswith("192.168.") or ip.startswith("10."):
        return {"country": "Egypt", "country_code": "EG", "currency": "EGP"}
        
    try:
        resp = httpx.get(f"http://ip-api.com/json/{ip}", timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                country = data.get("country", "Egypt")
                code = data.get("countryCode", "EG")
                currency_map = {
                    "EG": "EGP", "SA": "SAR", "AE": "AED", "KW": "KWD",
                    "QA": "QAR", "BH": "BHD", "OM": "OMR", "JO": "JOD",
                    "LB": "LBP", "US": "USD", "GB": "GBP", "EU": "EUR"
                }
                currency = currency_map.get(code, "USD")
                return {"country": country, "country_code": code, "currency": currency}
    except Exception as e:
        logger.error(f"IP Geolocation failed for IP {ip}: {e}")
    return {"country": "Egypt", "country_code": "EG", "currency": "EGP"}

def detect_location_from_text(text: str) -> dict:
    if not text:
        return None
    text_lower = text.lower()
    
    # Tier 1: Check country keywords first
    if any(k in text_lower for k in ["سعود", "saudi", "ksa", "الرياض", "سعودي"]):
        return {"country": "Saudi Arabia", "country_code": "SA", "currency": "SAR"}
    if any(k in text_lower for k in ["مصر", "egypt", "القاهرة", "مصري"]):
        return {"country": "Egypt", "country_code": "EG", "currency": "EGP"}
    if any(k in text_lower for k in ["امارات", "إمارات", "uae", "دبي", "اماراتي"]):
        return {"country": "United Arab Emirates", "country_code": "AE", "currency": "AED"}
    if any(k in text_lower for k in ["كويت", "kuwait"]):
        return {"country": "Kuwait", "country_code": "KW", "currency": "KWD"}
    if any(k in text_lower for k in ["قطر", "qatar"]):
        return {"country": "Qatar", "country_code": "QA", "currency": "QAR"}
    if any(k in text_lower for k in ["بحرين", "bahrain"]):
        return {"country": "Bahrain", "country_code": "BH", "currency": "BHD"}
    if any(k in text_lower for k in ["عمان", "oman"]):
        return {"country": "Oman", "country_code": "OM", "currency": "OMR"}
    if any(k in text_lower for k in ["اردن", "أردن", "jordan"]):
        return {"country": "Jordan", "country_code": "JO", "currency": "JOD"}
    if any(k in text_lower for k in ["لبنان", "lebanon"]):
        return {"country": "Lebanon", "country_code": "LB", "currency": "LBP"}
    if any(k in text_lower for k in ["امريكا", "أمريكا", "usa"]):
        return {"country": "United States", "country_code": "US", "currency": "USD"}
    if any(k in text_lower for k in ["بريطانيا", "uk"]):
        return {"country": "United Kingdom", "country_code": "GB", "currency": "GBP"}
    if any(k in text_lower for k in ["اوروبا", "أوروبا"]):
        return {"country": "Europe", "country_code": "EU", "currency": "EUR"}

    # Tier 2: Check currency keywords only if no country was explicitly mentioned
    if any(k in text_lower for k in ["sar", "riyal", "ريال", "رس"]):
        return {"country": "Saudi Arabia", "country_code": "SA", "currency": "SAR"}
    if any(k in text_lower for k in ["egp", "pound", "جنيه"]):
        return {"country": "Egypt", "country_code": "EG", "currency": "EGP"}
    if any(k in text_lower for k in ["aed", "dirham", "درهم"]):
        return {"country": "United Arab Emirates", "country_code": "AE", "currency": "AED"}
    if any(k in text_lower for k in ["kwd", "dinar", "دينار"]):
        return {"country": "Kuwait", "country_code": "KW", "currency": "KWD"}
    if any(k in text_lower for k in ["qar"]):
        return {"country": "Qatar", "country_code": "QA", "currency": "QAR"}
    if any(k in text_lower for k in ["bhd"]):
        return {"country": "Bahrain", "country_code": "BH", "currency": "BHD"}
    if any(k in text_lower for k in ["omr"]):
        return {"country": "Oman", "country_code": "OM", "currency": "OMR"}
    if any(k in text_lower for k in ["jod"]):
        return {"country": "Jordan", "country_code": "JO", "currency": "JOD"}
    if any(k in text_lower for k in ["lbp"]):
        return {"country": "Lebanon", "country_code": "LB", "currency": "LBP"}
    if any(k in text_lower for k in ["usd", "dollar", "دولار"]):
        return {"country": "United States", "country_code": "US", "currency": "USD"}
    if any(k in text_lower for k in ["gbp", "sterling", "استرليني"]):
        return {"country": "United Kingdom", "country_code": "GB", "currency": "GBP"}
    if any(k in text_lower for k in ["eur", "euro", "يورو"]):
        return {"country": "Europe", "country_code": "EU", "currency": "EUR"}

    return None
