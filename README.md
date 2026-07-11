# 🌾 AgriBot – Smart Farming Advisor

An AI-powered Smart Farming Advice web application built with **Python Flask** and **IBM watsonx.ai (Granite models)**. Designed for farmers across Tamil Nadu's six agro-climatic zones, supporting both **English and Tamil** input/output.

---

## ✨ Features

| Feature | Description |
|---|---|
| 💬 AI Chat | Conversational farming advice powered by IBM Granite model |
| 🌦 Weather Check | Real-time weather via Open-Meteo API (no key required) |
| 🌾 Crop & Season Advice | Granite model knowledge for Tamil Nadu zones |
| 💰 Mandi Price | Simulated indicative APMC prices |
| 📊 Cost-Benefit Estimator | Per-acre cost breakdown + expected profit |
| 📋 Scheme Finder | PMFBY, PM-KISAN, seed subsidies & more |
| 🌙 Dark Mode | System-aware, persisted preference |
| 📱 Mobile Responsive | Full Bootstrap 5.3 responsive design |

---

## 🗂 Project Structure

```
.
├── app.py                 # Flask app, watsonx.ai client, agent loop, API routes
├── tools.py               # All tool functions (weather, price, cost-benefit, schemes)
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── templates/
│   └── index.html         # Single-page frontend (Bootstrap 5.3)
├── static/
│   ├── css/style.css      # Custom styles + dark mode tokens
│   └── js/app.js          # Chat logic, quick-action forms, theme toggle
└── README.md
```

---

## 🚀 Setup & Installation

### 1. Prerequisites

- Python 3.11+
- An [IBM Cloud account](https://cloud.ibm.com) with watsonx.ai access
- A watsonx.ai project (copy its **Project ID**)
- An **IBM Cloud API Key** (from IAM → API Keys)

### 2. Clone & install dependencies

```bash
git clone <your-repo-url>
cd agribot
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
IBM_API_KEY=your_ibm_cloud_api_key_here
WATSONX_PROJECT_ID=your_watsonx_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-3-3-8b-instruct
FLASK_SECRET_KEY=some-random-secret-string
FLASK_DEBUG=False
```

> ⚠️ **Never commit your `.env` file.** It is listed in `.gitignore`.

### 4. Run the application

```bash
python app.py
```

Open your browser at **http://localhost:5000**

### 5. Production deployment (optional)

```bash
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

---

## 🎛 Quick-Action Menu Options

The 2-column button grid above the chat input offers these one-tap actions — all routed through the single `/api/chat` endpoint:

| Button | Fields | How It Works |
|---|---|---|
| 🌦 **Weather Check** | District name | Geocodes via Open-Meteo → fetches current weather + 4-day forecast. No API key needed. |
| 🌾 **Crop & Season Advice** | District / zone | Sends query to Granite model; uses its trained agricultural knowledge for Tamil Nadu zones. |
| 💰 **Today's Mandi Price** | Crop name | Looks up simulated indicative APMC price from in-memory reference data. |
| 📊 **Cost-Benefit Estimator** | Crop name, Land (acres) | Static per-acre input costs × land size + modal mandi price = profit/ROI estimate. |
| 📋 **Scheme Finder** | Crop, Acres, Farmer category | Matches against embedded eligibility rules for PMFBY, PM-KISAN, seed subsidies, NHM, KCC, and more. |

---

## 🛠 Customising Agent Behaviour

Open `app.py` and edit the `AGENT_INSTRUCTIONS` block at the top of the file:

```python
AGENT_INSTRUCTIONS = """
You are AgriBot...
TONE & STYLE: ...
DOMAIN SCOPE: ...
SAFETY RULES: ...
"""
```

Key configurable areas:
- **Tone** – formal/informal, language preference
- **Agro-climatic zones** – restrict or expand scope
- **Safety rules** – pesticide advice guardrails, chemical dosage restrictions
- **Domain scope** – add or remove crop types, regions

---

## 🌐 External APIs Used

| API | Purpose | Auth Required |
|---|---|---|
| [Open-Meteo Geocoding](https://geocoding-api.open-meteo.com/v1/search) | Convert district name → lat/lon | ❌ None |
| [Open-Meteo Forecast](https://api.open-meteo.com/v1/forecast) | Current weather + forecast | ❌ None |
| [IBM watsonx.ai](https://us-south.ml.cloud.ibm.com) | Granite LLM inference | ✅ IBM API Key |

Mandi prices are **simulated** with a static reference dictionary + small daily variation. No external price API or signup is required.

---

## 🔒 Safety & Disclaimers

- AgriBot **never** recommends specific pesticide dosages or brand names.
- All price and yield figures are **indicative** — verify with your local APMC before trading.
- Always consult a local Agriculture Officer or KVK for critical decisions.
- **Kisan Call Centre**: 1800-180-1551 (free, multilingual)

---

## 📦 Supported Crops (Cost-Benefit & Prices)

Paddy · Rice · Wheat · Tomato · Onion · Cotton · Groundnut · Sugarcane · Banana · Brinjal · Chilli · Turmeric · Coconut · Maize · Soybean · Black Gram · Green Gram · Sunflower · Ginger · Garlic

---

## 🐛 Troubleshooting

| Issue | Fix |
|---|---|
| `Configuration missing: IBM_API_KEY` | Ensure `.env` is present and contains valid credentials |
| `Agent error: 401 Unauthorized` | Check your IBM API Key is valid and not expired |
| Weather tool returns "not found" | Try a nearby major city name (e.g. "Coimbatore" instead of a village name) |
| Slow first response | Model is initialised on first request — subsequent calls are faster |
