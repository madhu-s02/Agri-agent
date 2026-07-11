"""
Smart Farming Advice Agent – Flask Backend
IBM watsonx.ai (Granite model) + tool functions + stateless chat API
"""
from __future__ import annotations

import os
import json
import datetime
import re
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

# ── load .env before anything else ───────────────────────────────────────────
load_dotenv()

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from tools import (
    get_weather,
    get_mandi_price,
    estimate_cost_benefit,
    find_schemes,
)

# ═════════════════════════════════════════════════════════════════════════════
# AGENT INSTRUCTIONS  – edit this block to change tone, scope, safety rules
# ═════════════════════════════════════════════════════════════════════════════
AGENT_INSTRUCTIONS = """
You are AgriBot, a friendly and knowledgeable Smart Farming Advisor for farmers
in Tamil Nadu, India. You support farmers across all six agro-climatic zones:
  1. North-Eastern  2. North-Western  3. Western  4. Southern  5. High Rainfall
  6. Hilly & High-Altitude

TONE & STYLE:
- Be warm, respectful, and practical – as if you are a trusted local agriculture officer.
- Use simple language. When replying in Tamil, use clear, conversational Tamil.
- Give actionable, concrete advice – not generic platitudes.
- Format responses with short paragraphs or bullet points; keep it readable on mobile.
- If the user writes in Tamil, reply in Tamil. If in English, reply in English.
  If mixed, match the dominant language.

DOMAIN SCOPE:
- Crop cultivation advice for Tamil Nadu crops: paddy, millets, pulses, oilseeds,
  sugarcane, cotton, banana, vegetables, spices, flowers, coconut.
- Pest & disease identification and Integrated Pest Management (IPM).
- Soil health, organic farming, and water management.
- Government schemes, subsidies, Kisan Credit Card, PMFBY insurance.
- Mandi prices, market linkage, FPO/cooperative advice.
- Seasonal calendar and crop rotation for Tamil Nadu agro-climatic zones.
- Weather interpretation and farm operation scheduling.

SAFETY RULES (NON-NEGOTIABLE):
- NEVER recommend specific pesticide dosages, brand names, or mixing instructions.
  Always say: "Please consult your local Agriculture Officer or licensed agrochemical
  dealer for pesticide dosage recommendations."
- Do not provide medical advice to farmers or animals.
- Do not make financial investment guarantees. Always add a caveat that prices and
  yields vary.
- If a question is outside your farming domain, politely decline and redirect the
  farmer to the appropriate authority.
- For chemical fertilizer dosages, recommend soil testing first and suggest the
  farmer consult the nearest Krishi Vigyan Kendra (KVK).
""".strip()

# ═════════════════════════════════════════════════════════════════════════════
# WATSONX CLIENT
# ═════════════════════════════════════════════════════════════════════════════

def _build_model() -> ModelInference:
    api_key    = os.environ["IBM_API_KEY"]
    project_id = os.environ["WATSONX_PROJECT_ID"]
    url        = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    model_id   = os.environ.get("WATSONX_MODEL_ID", "meta-llama/llama-3-3-70b-instruct")

    credentials = Credentials(api_key=api_key, url=url)
    return ModelInference(
        model_id=model_id,
        credentials=credentials,
        project_id=project_id,
        params={
            GenParams.MAX_NEW_TOKENS: 1024,
            GenParams.TEMPERATURE:    0.4,
            GenParams.REPETITION_PENALTY: 1.1,
        },
    )


# Lazy singleton – built on first request to avoid startup cost
_model: ModelInference | None = None

def get_model() -> ModelInference:
    global _model
    if _model is None:
        _model = _build_model()
    return _model


# ═════════════════════════════════════════════════════════════════════════════
# TOOL DISPATCHER
# ═════════════════════════════════════════════════════════════════════════════

def _dispatch_tool(tool_name: str, args: dict) -> str:
    """Execute a tool and return its result as a JSON string."""
    try:
        if tool_name == "get_weather":
            result = get_weather(args.get("district", ""))
        elif tool_name == "get_mandi_price":
            result = get_mandi_price(args.get("crop", ""))
        elif tool_name == "estimate_cost_benefit":
            result = estimate_cost_benefit(
                args.get("crop", ""),
                args.get("land_acres", 1),
            )
        elif tool_name == "find_schemes":
            result = find_schemes(
                args.get("crop", ""),
                args.get("land_acres", 1),
                args.get("farmer_category", "small"),
            )
        else:
            result = {"error": True, "message": f"Unknown tool: {tool_name}"}
    except Exception as exc:  # noqa: BLE001
        result = {"error": True, "message": str(exc)}

    return json.dumps(result, ensure_ascii=False)


# ═════════════════════════════════════════════════════════════════════════════
# INTENT DETECTION  – parse quick-action messages server-side, no LLM needed
# ═════════════════════════════════════════════════════════════════════════════

# Patterns that map a user message to a tool call directly
_INTENT_PATTERNS = [
    # Weather
    (re.compile(
        r'weather.*?for\s+(.+?)(?:\?|$)|forecast.*?for\s+(.+?)(?:\?|$)',
        re.I),
     lambda m: ("get_weather", {"district": (m.group(1) or m.group(2)).strip()})),

    # Mandi price
    (re.compile(
        r"(?:mandi|market)\s+price.*?for\s+(.+?)(?:\?|$)|price.*?for\s+(.+?)(?:\?|$)|today'?s.*?price.*?for\s+(.+?)(?:\?|$)",
        re.I),
     lambda m: ("get_mandi_price", {"crop": (m.group(1) or m.group(2) or m.group(3)).strip()})),

    # Cost-benefit
    (re.compile(
        r'cost.*?benefit.*?(?:for\s+)?(\w[\w\s]*?)\s+on\s+([\d.]+)\s*acres?',
        re.I),
     lambda m: ("estimate_cost_benefit", {"crop": m.group(1).strip(), "land_acres": float(m.group(2))})),

    # Scheme finder
    (re.compile(
        r'scheme.*?(\w[\w\s]*?)\s+on\s+([\d.]+)\s*acres?.*?(small|marginal|large)',
        re.I),
     lambda m: ("find_schemes", {"crop": m.group(1).strip(), "land_acres": float(m.group(2)), "farmer_category": m.group(3).strip()})),
]


def _detect_intent(message: str) -> tuple[str, dict] | None:
    """Return (tool_name, args) if the message matches a known intent, else None."""
    for pattern, builder in _INTENT_PATTERNS:
        m = pattern.search(message)
        if m:
            try:
                return builder(m)
            except Exception:
                continue
    return None


# ═════════════════════════════════════════════════════════════════════════════
# CORE AGENT FUNCTION  (all quick-action buttons route through here)
# ═════════════════════════════════════════════════════════════════════════════

def run_agent(user_message: str, history: list[dict] | None = None) -> str:
    """
    Stateless agent loop:
      1. Detect tool intent directly from message (fast path – no LLM round-trip).
      2. If tool needed: call tool, then ask LLM to format the result as a
         friendly farming answer.
      3. If no tool needed: ask LLM directly.

    history format: [{"role": "user"|"assistant", "content": "..."}]
    """
    model   = get_model()
    history = history or []

    # ── Step 1: direct intent detection (reliable, no model guessing) ─────────
    intent = _detect_intent(user_message)
    if intent:
        tool_name, tool_args = intent
        tool_result_str = _dispatch_tool(tool_name, tool_args)
        # Ask LLM to turn raw tool data into a helpful farmer-friendly answer
        synthesis_prompt = (
            f"The farmer asked: {user_message}\n\n"
            f"Here is the data retrieved:\n{tool_result_str}\n\n"
            f"Please write a clear, friendly, actionable answer for the farmer "
            f"based on this data. Format it nicely with bullet points where helpful."
        )
        messages = [
            {"role": "system", "content": AGENT_INSTRUCTIONS},
            {"role": "user",   "content": synthesis_prompt},
        ]
        response = model.chat(messages=messages)
        return _extract_text(response).strip()

    # ── Step 2: pure LLM answer (crop advice, general questions, Tamil, etc.) ──
    messages = [{"role": "system", "content": AGENT_INSTRUCTIONS}]
    for turn in history[-10:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    response = model.chat(messages=messages)
    return _extract_text(response).strip()


def _extract_text(response: dict) -> str:
    """Pull the generated text out of a watsonx chat response."""
    if "choices" in response:
        return response["choices"][0]["message"]["content"]
    return response.get("results", [{}])[0].get("generated_text", "")


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD DATA  (used on initial page load)
# ═════════════════════════════════════════════════════════════════════════════

def get_dashboard_data() -> dict:
    """Return lightweight data for the farming dashboard panel."""
    today = datetime.date.today()

    # Quick crop price snapshot (a few staples)
    price_snapshot = []
    for crop in ["paddy", "tomato", "onion", "cotton", "groundnut"]:
        p = get_mandi_price(crop)
        if not p.get("error"):
            price_snapshot.append({
                "crop":   p["crop"],
                "price":  p["modal_price"],
                "unit":   p["unit"],
                "market": p["market"],
            })

    # Seasonal tip based on month
    month = today.month
    tips_map = {
        (1, 2):   "☀️  Rabi harvest season – plan post-harvest storage to avoid moisture damage.",
        (3, 4):   "🌡️  Summer crops: consider short-duration varieties. Ensure irrigation planning.",
        (5, 6):   "🌧️  Pre-kharif: prepare land before the Southwest Monsoon arrives.",
        (7, 8):   "🌱  Kharif sowing in full swing – monitor for stem borer and blast.",
        (9, 10):  "🍂  Northeast Monsoon approaching – prepare drainage channels.",
        (11, 12): "🌾  Samba/Thaladi paddy harvesting – check for proper grain moisture.",
    }
    tip = next(
        (v for k, v in tips_map.items() if k[0] <= month <= k[1]),
        "🌿  Consult your local agriculture officer for tailored seasonal advice.",
    )

    return {
        "date":            today.strftime("%d %B %Y"),
        "price_snapshot":  price_snapshot,
        "seasonal_tip":    tip,
        "weather_note":    "Enter your district in Weather Check for a live forecast.",
    }


# ═════════════════════════════════════════════════════════════════════════════
# FLASK APP
# ═════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")


@app.route("/")
def index():
    dashboard = get_dashboard_data()
    return render_template("index.html", dashboard=dashboard)


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Single shared endpoint for all chat messages AND quick-action buttons.
    Request body (JSON):
      {
        "message":  str,                  # user's message (required)
        "history":  list[dict] | null     # optional prior turns
      }
    """
    data = request.get_json(force=True, silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history      = data.get("history") or []

    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400

    try:
        reply = run_agent(user_message, history)
        return jsonify({"reply": reply})
    except KeyError as exc:
        missing = str(exc).strip("'")
        return jsonify({
            "error": (
                f"Configuration missing: {missing}. "
                "Please check your .env file and ensure IBM_API_KEY and "
                "WATSONX_PROJECT_ID are set."
            )
        }), 500
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Agent error: {exc}"}), 500


@app.route("/api/dashboard", methods=["GET"])
def dashboard_api():
    """Refresh dashboard data (prices change with every call due to simulation)."""
    return jsonify(get_dashboard_data())


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=5000)
