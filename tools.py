"""
Smart Farming Agent – Tool Functions
All external calls use free, no-auth APIs. Mock data is used for Mandi prices.
"""

import requests

# ──────────────────────────────────────────────────────────────────────────────
# 1. WEATHER  (Open-Meteo – no API key required)
# ──────────────────────────────────────────────────────────────────────────────

def get_weather(district: str) -> dict:
    """
    Geocode the district name via Open-Meteo Geocoding API, then fetch
    current weather + 3-day forecast from the Open-Meteo Forecast API.
    Returns a plain dict that the agent can format as text.
    """
    try:
        # Step 1: geocode
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": district, "count": 1, "language": "en", "format": "json"}
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return {
                "error": True,
                "message": f"Could not find location '{district}'. Please check the spelling or try a nearby city name."
            }

        result = geo_data["results"][0]
        lat = result["latitude"]
        lon = result["longitude"]
        location_name = result.get("name", district)
        country = result.get("country", "")
        admin1 = result.get("admin1", "")

        # Step 2: forecast
        wx_url = "https://api.open-meteo.com/v1/forecast"
        wx_params = {
            "latitude": lat,
            "longitude": lon,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
                "apparent_temperature",
            ],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "weather_code",
            ],
            "timezone": "Asia/Kolkata",
            "forecast_days": 4,
        }
        wx_resp = requests.get(wx_url, params=wx_params, timeout=10)
        wx_resp.raise_for_status()
        wx = wx_resp.json()

        current = wx.get("current", {})
        daily   = wx.get("daily", {})

        # WMO weather code → human label (subset)
        def wmo_label(code):
            mapping = {
                0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Foggy", 48: "Icy fog",
                51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
                61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
                80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
                95: "Thunderstorm", 96: "Thunderstorm with hail",
            }
            return mapping.get(code, f"Code {code}")

        forecast_days = []
        dates     = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precip    = daily.get("precipitation_sum", [])
        wx_codes  = daily.get("weather_code", [])

        for i in range(min(4, len(dates))):
            forecast_days.append({
                "date":       dates[i],
                "max_temp":   max_temps[i] if i < len(max_temps) else None,
                "min_temp":   min_temps[i] if i < len(min_temps) else None,
                "precip_mm":  precip[i]    if i < len(precip)    else None,
                "condition":  wmo_label(wx_codes[i]) if i < len(wx_codes) else "N/A",
            })

        return {
            "error": False,
            "location": f"{location_name}, {admin1}, {country}".strip(", "),
            "current": {
                "temperature":    current.get("temperature_2m"),
                "feels_like":     current.get("apparent_temperature"),
                "humidity":       current.get("relative_humidity_2m"),
                "precipitation":  current.get("precipitation"),
                "wind_speed":     current.get("wind_speed_10m"),
                "condition":      wmo_label(current.get("weather_code", 0)),
            },
            "forecast": forecast_days,
        }

    except requests.RequestException as exc:
        return {"error": True, "message": f"Weather API request failed: {exc}"}


# ──────────────────────────────────────────────────────────────────────────────
# 2. MANDI PRICE  (simulated – no external API key needed)
# ──────────────────────────────────────────────────────────────────────────────

_MANDI_DATA = {
    # crop_lower: { "unit": str, "min": ₹, "max": ₹, "modal": ₹, "market": str }
    "paddy":      {"unit": "quintal", "min": 1800, "max": 2200, "modal": 2020, "market": "Thanjavur APMC"},
    "rice":       {"unit": "quintal", "min": 2800, "max": 3400, "modal": 3100, "market": "Chennai Koyambedu"},
    "wheat":      {"unit": "quintal", "min": 2000, "max": 2300, "modal": 2150, "market": "Coimbatore APMC"},
    "tomato":     {"unit": "kg",      "min": 8,    "max": 25,   "modal": 14,   "market": "Hosur APMC"},
    "onion":      {"unit": "kg",      "min": 10,   "max": 30,   "modal": 18,   "market": "Madurai APMC"},
    "cotton":     {"unit": "quintal", "min": 5800, "max": 7200, "modal": 6500, "market": "Coimbatore APMC"},
    "groundnut":  {"unit": "quintal", "min": 4500, "max": 5800, "modal": 5200, "market": "Tirunelveli APMC"},
    "sugarcane":  {"unit": "tonne",   "min": 2800, "max": 3200, "modal": 3000, "market": "Erode APMC"},
    "banana":     {"unit": "dozen",   "min": 20,   "max": 60,   "modal": 38,   "market": "Trichy APMC"},
    "brinjal":    {"unit": "kg",      "min": 6,    "max": 18,   "modal": 10,   "market": "Vellore APMC"},
    "chilli":     {"unit": "kg",      "min": 80,   "max": 160,  "modal": 110,  "market": "Guntur APMC"},
    "turmeric":   {"unit": "quintal", "min": 7000, "max": 12000,"modal": 9500, "market": "Erode APMC"},
    "coconut":    {"unit": "unit",    "min": 14,   "max": 22,   "modal": 17,   "market": "Pollachi APMC"},
    "maize":      {"unit": "quintal", "min": 1600, "max": 1950, "modal": 1780, "market": "Salem APMC"},
    "soybean":    {"unit": "quintal", "min": 3800, "max": 4500, "modal": 4200, "market": "Coimbatore APMC"},
    "black gram": {"unit": "quintal", "min": 5500, "max": 7500, "modal": 6400, "market": "Madurai APMC"},
    "green gram": {"unit": "quintal", "min": 6000, "max": 8000, "modal": 7200, "market": "Chennai APMC"},
    "sunflower":  {"unit": "quintal", "min": 4500, "max": 5800, "modal": 5200, "market": "Tiruppur APMC"},
    "ginger":     {"unit": "kg",      "min": 25,   "max": 80,   "modal": 50,   "market": "Nilgiris APMC"},
    "garlic":     {"unit": "kg",      "min": 50,   "max": 140,  "modal": 90,   "market": "Dindigul APMC"},
}

def get_mandi_price(crop: str) -> dict:
    """Return today's simulated mandi price for the requested crop."""
    import random, datetime
    key = crop.strip().lower()
    data = _MANDI_DATA.get(key)

    # fuzzy match – check if any key is a substring of the query or vice versa
    if not data:
        for k, v in _MANDI_DATA.items():
            if k in key or key in k:
                data = v
                key  = k
                break

    if not data:
        available = ", ".join(sorted(_MANDI_DATA.keys()))
        return {
            "error": True,
            "message": (
                f"Price data not available for '{crop}'. "
                f"Available crops: {available}."
            ),
        }

    # add slight daily variation (±5 %)
    variation = random.uniform(0.95, 1.05)
    modal_today = round(data["modal"] * variation)

    return {
        "error":     False,
        "crop":      key.title(),
        "unit":      data["unit"],
        "min_price": data["min"],
        "max_price": data["max"],
        "modal_price": modal_today,
        "market":    data["market"],
        "date":      datetime.date.today().isoformat(),
        "note":      "Simulated indicative prices – verify with local APMC before trading.",
    }


# ──────────────────────────────────────────────────────────────────────────────
# 3. COST-BENEFIT ESTIMATOR  (static reference data – no API)
# ──────────────────────────────────────────────────────────────────────────────

# Per-acre cost breakdown (INR) for common Tamil Nadu crops
_CROP_COSTS = {
    "paddy": {
        "seed": 1200, "fertilizer": 4500, "pesticide": 1500,
        "labor": 8000, "irrigation": 3000, "misc": 1500,
        "avg_yield_per_acre": 20,   # quintals
        "yield_unit": "quintal",
        "season_days": 120,
    },
    "tomato": {
        "seed": 2500, "fertilizer": 6000, "pesticide": 3000,
        "labor": 12000, "irrigation": 4000, "misc": 2000,
        "avg_yield_per_acre": 8000, # kg
        "yield_unit": "kg",
        "season_days": 90,
    },
    "cotton": {
        "seed": 3000, "fertilizer": 7000, "pesticide": 5000,
        "labor": 15000, "irrigation": 4000, "misc": 2000,
        "avg_yield_per_acre": 8,    # quintals
        "yield_unit": "quintal",
        "season_days": 180,
    },
    "groundnut": {
        "seed": 4000, "fertilizer": 4000, "pesticide": 1500,
        "labor": 8000, "irrigation": 2500, "misc": 1500,
        "avg_yield_per_acre": 10,   # quintals
        "yield_unit": "quintal",
        "season_days": 110,
    },
    "sugarcane": {
        "seed": 8000, "fertilizer": 10000, "pesticide": 3000,
        "labor": 20000, "irrigation": 8000, "misc": 3000,
        "avg_yield_per_acre": 35,   # tonnes
        "yield_unit": "tonne",
        "season_days": 360,
    },
    "maize": {
        "seed": 1500, "fertilizer": 4000, "pesticide": 1000,
        "labor": 6000, "irrigation": 2000, "misc": 1000,
        "avg_yield_per_acre": 20,   # quintals
        "yield_unit": "quintal",
        "season_days": 90,
    },
    "onion": {
        "seed": 2000, "fertilizer": 5000, "pesticide": 2000,
        "labor": 10000, "irrigation": 4000, "misc": 1500,
        "avg_yield_per_acre": 6000, # kg
        "yield_unit": "kg",
        "season_days": 120,
    },
    "black gram": {
        "seed": 1500, "fertilizer": 2500, "pesticide": 800,
        "labor": 5000, "irrigation": 1500, "misc": 700,
        "avg_yield_per_acre": 6,    # quintals
        "yield_unit": "quintal",
        "season_days": 75,
    },
    "turmeric": {
        "seed": 15000, "fertilizer": 6000, "pesticide": 2000,
        "labor": 18000, "irrigation": 5000, "misc": 2000,
        "avg_yield_per_acre": 25,   # quintals (dry)
        "yield_unit": "quintal",
        "season_days": 270,
    },
    "banana": {
        "seed": 5000, "fertilizer": 8000, "pesticide": 3000,
        "labor": 14000, "irrigation": 6000, "misc": 2000,
        "avg_yield_per_acre": 800,  # dozen
        "yield_unit": "dozen",
        "season_days": 300,
    },
}

def estimate_cost_benefit(crop: str, land_acres: float) -> dict:
    """
    Returns a cost-benefit estimate for growing `crop` on `land_acres` acres.
    Uses static per-acre cost data + current simulated mandi modal price.
    """
    key = crop.strip().lower()
    cost_data = _CROP_COSTS.get(key)

    # fuzzy match
    if not cost_data:
        for k, v in _CROP_COSTS.items():
            if k in key or key in k:
                cost_data = v
                key = k
                break

    if not cost_data:
        available = ", ".join(sorted(_CROP_COSTS.keys()))
        return {
            "error": True,
            "message": (
                f"Cost data not available for '{crop}'. "
                f"Supported crops: {available}."
            ),
        }

    try:
        acres = float(land_acres)
        if acres <= 0:
            return {"error": True, "message": "Land size must be greater than 0."}
    except (ValueError, TypeError):
        return {"error": True, "message": "Invalid land size provided."}

    # Per-acre totals
    cost_per_acre = (
        cost_data["seed"]
        + cost_data["fertilizer"]
        + cost_data["pesticide"]
        + cost_data["labor"]
        + cost_data["irrigation"]
        + cost_data["misc"]
    )
    total_cost = cost_per_acre * acres

    # Expected yield
    total_yield = cost_data["avg_yield_per_acre"] * acres
    yield_unit  = cost_data["yield_unit"]

    # Price lookup (simulated)
    price_info = get_mandi_price(key)
    if price_info.get("error"):
        modal_price = None
        revenue_est = None
        profit_est  = None
        roi_pct     = None
    else:
        modal_price = price_info["modal_price"]
        revenue_est = total_yield * modal_price
        profit_est  = revenue_est - total_cost
        roi_pct     = round((profit_est / total_cost) * 100, 1) if total_cost else 0

    return {
        "error":          False,
        "crop":           key.title(),
        "land_acres":     acres,
        "season_days":    cost_data["season_days"],
        "cost_breakdown": {
            "seed_total":       round(cost_data["seed"]        * acres),
            "fertilizer_total": round(cost_data["fertilizer"]  * acres),
            "pesticide_total":  round(cost_data["pesticide"]   * acres),
            "labor_total":      round(cost_data["labor"]       * acres),
            "irrigation_total": round(cost_data["irrigation"]  * acres),
            "misc_total":       round(cost_data["misc"]        * acres),
        },
        "total_cost":     round(total_cost),
        "expected_yield": round(total_yield, 2),
        "yield_unit":     yield_unit,
        "modal_price_per_unit": modal_price,
        "estimated_revenue": round(revenue_est) if revenue_est is not None else None,
        "estimated_profit":  round(profit_est)  if profit_est  is not None else None,
        "roi_percent":       roi_pct,
        "note": (
            "These are approximate figures based on Tamil Nadu averages. "
            "Actual results depend on soil quality, rainfall, and market conditions."
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# 4. SCHEME FINDER  (static eligibility rules – no API)
# ──────────────────────────────────────────────────────────────────────────────

_SCHEMES = [
    {
        "name": "PM Fasal Bima Yojana (PMFBY)",
        "type": "Crop Insurance",
        "description": (
            "Provides financial support to farmers suffering crop loss/damage due to "
            "unforeseen events like natural calamities, pests, and diseases."
        ),
        "eligible_crops": ["paddy", "wheat", "maize", "cotton", "groundnut",
                           "sugarcane", "soybean", "black gram", "green gram", "sunflower"],
        "min_land_acres": 0,
        "max_land_acres": 1000,
        "farmer_categories": ["small", "marginal", "large", "all"],
        "benefit": "Up to 100% of insured amount for complete crop loss. Premium: 1.5–5%.",
        "how_to_apply": "Apply through nearest bank branch, CSC, or insurance company before crop season.",
        "contact": "State Agriculture Department / Bank",
    },
    {
        "name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "type": "Income Support",
        "description": "Direct income support of ₹6,000/year in three installments to farmer families.",
        "eligible_crops": ["all"],
        "min_land_acres": 0,
        "max_land_acres": 1000,
        "farmer_categories": ["small", "marginal", "all"],
        "benefit": "₹6,000 per year (₹2,000 every 4 months) transferred directly to bank account.",
        "how_to_apply": "Register at pmkisan.gov.in or nearest CSC/Agriculture office.",
        "contact": "pmkisan.gov.in | Helpline: 155261",
    },
    {
        "name": "Tamil Nadu Seed Subsidy Scheme",
        "type": "Input Subsidy",
        "description": "Subsidised certified seeds distributed through TNSC / Agriculture Department.",
        "eligible_crops": ["paddy", "maize", "black gram", "green gram", "groundnut",
                           "sunflower", "soybean", "cotton"],
        "min_land_acres": 0,
        "max_land_acres": 5,
        "farmer_categories": ["small", "marginal"],
        "benefit": "50% subsidy on certified seeds (up to 2 acres). Free mini-kit seeds for SC/ST farmers.",
        "how_to_apply": "Contact Block Agriculture Officer (BAO) or nearest Agri Extension Centre.",
        "contact": "Block Agriculture Office / District Agriculture Department",
    },
    {
        "name": "National Horticulture Mission (NHM)",
        "type": "Development Scheme",
        "description": "Promotes horticulture crops with subsidies on planting material, drip irrigation, and post-harvest infrastructure.",
        "eligible_crops": ["banana", "tomato", "onion", "chilli", "turmeric",
                           "ginger", "garlic", "brinjal", "coconut"],
        "min_land_acres": 0.5,
        "max_land_acres": 4,
        "farmer_categories": ["small", "marginal", "all"],
        "benefit": "25–50% subsidy on planting material, drip/sprinkler irrigation, cold storage.",
        "how_to_apply": "Apply through Horticulture Department or District Horticulture Officer.",
        "contact": "District Horticulture Office",
    },
    {
        "name": "Kisan Credit Card (KCC)",
        "type": "Credit Scheme",
        "description": "Short-term credit for crop cultivation, post-harvest expenses, and allied activities.",
        "eligible_crops": ["all"],
        "min_land_acres": 0,
        "max_land_acres": 1000,
        "farmer_categories": ["small", "marginal", "large", "all"],
        "benefit": "Revolving credit at 4–7% p.a. interest. Up to ₹3 lakh at concessional rate.",
        "how_to_apply": "Apply at nearest bank (SBI, Cooperative Bank, RRB). Documents: land records, ID proof.",
        "contact": "Nearest nationalized bank / cooperative bank",
    },
    {
        "name": "TNAU Free Farm Machinery Scheme",
        "type": "Mechanization",
        "description": "Subsidised farm machinery (tractors, tillers, weeders) for small and marginal farmers via CHC.",
        "eligible_crops": ["all"],
        "min_land_acres": 0,
        "max_land_acres": 5,
        "farmer_categories": ["small", "marginal"],
        "benefit": "50% subsidy (up to ₹1 lakh) on approved farm equipment. CHC rental at nominal rates.",
        "how_to_apply": "Contact Agricultural Engineering Department or TNAU extension centre.",
        "contact": "Agricultural Engineering Department, Tamil Nadu",
    },
    {
        "name": "Drip & Sprinkler Irrigation Subsidy (TNAU/NABARD)",
        "type": "Infrastructure Subsidy",
        "description": "Subsidy on micro-irrigation systems to improve water use efficiency.",
        "eligible_crops": ["sugarcane", "banana", "tomato", "onion", "cotton",
                           "groundnut", "turmeric", "chilli"],
        "min_land_acres": 0.5,
        "max_land_acres": 10,
        "farmer_categories": ["small", "marginal", "all"],
        "benefit": "50–90% subsidy on drip/sprinkler systems depending on farmer category and crop.",
        "how_to_apply": "Apply through Agriculture Department. Empanelled manufacturers supply and install.",
        "contact": "District Agriculture Office / NABARD",
    },
]

def find_schemes(crop: str, land_acres: float, farmer_category: str) -> dict:
    """
    Match government schemes based on crop, land size, and farmer category.
    farmer_category: 'small' (<2 acres), 'marginal' (2–5 acres), 'large' (>5 acres)
    """
    try:
        acres = float(land_acres)
    except (ValueError, TypeError):
        acres = 0.0

    category = farmer_category.strip().lower()
    crop_key  = crop.strip().lower()

    matched = []
    for scheme in _SCHEMES:
        # crop eligibility
        crop_ok = (
            "all" in scheme["eligible_crops"]
            or crop_key in scheme["eligible_crops"]
            or any(k in crop_key or crop_key in k for k in scheme["eligible_crops"])
        )
        # land eligibility
        land_ok = scheme["min_land_acres"] <= acres <= scheme["max_land_acres"]
        # category eligibility
        cat_ok  = (
            "all" in scheme["farmer_categories"]
            or category in scheme["farmer_categories"]
        )

        if crop_ok and land_ok and cat_ok:
            matched.append(scheme)

    if not matched:
        return {
            "error": False,
            "matched": [],
            "message": (
                f"No schemes found matching crop='{crop}', land={acres} acres, "
                f"category='{farmer_category}'. "
                "Try adjusting the category (small/marginal/large) or consult your local Agriculture Office."
            ),
        }

    return {
        "error":   False,
        "crop":    crop.title(),
        "acres":   acres,
        "category": farmer_category,
        "matched": matched,
        "count":   len(matched),
    }
