"""
esg_data.py
───────────
ESG score lookup + ML prediction for unknown stocks.
 
Three separate models predict E, S, G independently:
  E model inputs: sector, industry_type, capex_ratio, operating_margin
  S model inputs: sector, industry_type, gross_margin, rd_ratio
  G model inputs: sector, industry_type, operating_margin, gross_margin
 
All inputs are fetched free via Finnhub (profile + metrics) and yfinance.
Carbon score is derived as: round((E * 0.7 + G * 0.3))
"""
def normalize_sector(finnhub_industry):
    """Map Finnhub industry strings to our sector keys."""
    if not finnhub_industry:
        return 'Technology'
    
    s = finnhub_industry.lower()
    
    if any(x in s for x in ['oil', 'gas', 'coal', 'petroleum', 'refin']):
        return 'Oil & Gas'
    if any(x in s for x in ['solar', 'wind', 'renewable', 'clean energy', 'enphase']):
        return 'Clean Energy'
    if any(x in s for x in ['electric util', 'utilities', 'power', 'nuclear', 'water']):
        return 'Energy'
    if any(x in s for x in ['software', 'tech', 'semiconductor', 'hardware', 'internet', 'data', 'cloud', 'it ', 'information']):
        return 'Technology'
    if any(x in s for x in ['auto', 'vehicle', 'motor', 'car', 'truck', 'electric vehicle']):
        return 'Automotive'
    if any(x in s for x in ['bank', 'financ', 'insurance', 'invest', 'asset', 'capital', 'credit', 'payment']):
        return 'Finance'
    if any(x in s for x in ['health', 'pharma', 'biotech', 'medical', 'hospital', 'drug', 'life science']):
        return 'Healthcare'
    if any(x in s for x in ['retail', 'consumer', 'food', 'beverage', 'restaurant', 'apparel', 'household']):
        return 'Consumer'
    if any(x in s for x in ['media', 'entertainment', 'film', 'music', 'broadcast', 'gaming', 'streaming']):
        return 'Entertainment'
    if any(x in s for x in ['aerospace', 'defense', 'military', 'weapon', 'security']):
        return 'Defense'
    if any(x in s for x in ['tobacco', 'cigarette']):
        return 'Tobacco'
    if any(x in s for x in ['real estate', 'reit', 'property']):
        return 'Consumer'
    if any(x in s for x in ['material', 'chemical', 'mining', 'metal', 'steel', 'construction']):
        return 'Consumer'
    
    return 'Technology'  # safe default
SCOPE_DATA = {
    "Oil & Gas":    {"scope1": "Very High", "scope2": "High",     "scope3": "Very High", "net_zero": "2050", "renewables": "Low"},
    "Clean Energy": {"scope1": "Very Low",  "scope2": "Very Low", "scope3": "Low",       "net_zero": "2035", "renewables": "100%"},
    "Energy":       {"scope1": "Low",       "scope2": "Very Low", "scope3": "Low",       "net_zero": "2040", "renewables": "90%"},
    "Technology":   {"scope1": "Low",       "scope2": "Low",      "scope3": "Moderate",  "net_zero": "2030", "renewables": "80%"},
    "Automotive":   {"scope1": "Moderate",  "scope2": "Moderate", "scope3": "High",      "net_zero": "2040", "renewables": "40%"},
    "Finance":      {"scope1": "Very Low",  "scope2": "Low",      "scope3": "High",      "net_zero": "2050", "renewables": "60%"},
    "Healthcare":   {"scope1": "Low",       "scope2": "Moderate", "scope3": "Moderate",  "net_zero": "2045", "renewables": "50%"},
    "Consumer":     {"scope1": "Moderate",  "scope2": "Moderate", "scope3": "High",      "net_zero": "2045", "renewables": "40%"},
    "Entertainment":{"scope1": "Low",       "scope2": "Low",      "scope3": "Moderate",  "net_zero": "2040", "renewables": "70%"},
    "Aerospace":    {"scope1": "High",      "scope2": "Moderate", "scope3": "High",      "net_zero": "2050", "renewables": "20%"},
    "Defense":      {"scope1": "High",      "scope2": "Moderate", "scope3": "High",      "net_zero": "2050", "renewables": "20%"},
    "Tobacco":      {"scope1": "Moderate",  "scope2": "Moderate", "scope3": "High",      "net_zero": "2050", "renewables": "30%"},
}

def get_scope_data(sector):
    return SCOPE_DATA.get(sector, {"scope1": "Moderate", "scope2": "Moderate", "scope3": "Moderate", "net_zero": "2050", "renewables": "N/A"})
import os
import numpy as np
 
# ── load models once at import time ──────────────────────────────────────────
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "esg_model_newest.joblib")
 
try:
    import joblib
    _ARTIFACT = joblib.load(_MODEL_PATH)
    _model_E        = _ARTIFACT["model_E"]
    _model_S        = _ARTIFACT["model_S"]
    _model_G        = _ARTIFACT["model_G"]
    _sector_encoder = _ARTIFACT["sector_encoder"]
    _sector_classes = _ARTIFACT["sector_classes"]
    _industry_map   = _ARTIFACT["industry_type_map"]
    _MODELS_LOADED  = True
except Exception as e:
    print(f"[esg_data] Warning: could not load esg_model.joblib ({e}). Falling back to static scores.")
    _MODELS_LOADED = False
 
# ── stock list ────────────────────────────────────────────────────────────────
STOCKS = [
    {"symbol": "AAPL",  "name": "Apple Inc.",              "sector": "Technology"},
    {"symbol": "MSFT",  "name": "Microsoft Corp.",          "sector": "Technology"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.",            "sector": "Technology"},
    {"symbol": "ADBE",  "name": "Adobe Inc.",               "sector": "Technology"},
    {"symbol": "CRM",   "name": "Salesforce Inc.",          "sector": "Technology"},
    {"symbol": "NVDA",  "name": "NVIDIA Corp.",             "sector": "Technology"},
    {"symbol": "AMD",   "name": "Advanced Micro Devices",   "sector": "Technology"},
    {"symbol": "TSLA",  "name": "Tesla Inc.",               "sector": "Automotive"},
    {"symbol": "NEE",   "name": "NextEra Energy",           "sector": "Energy"},
    {"symbol": "ENPH",  "name": "Enphase Energy",           "sector": "Clean Energy"},
    {"symbol": "AMZN",  "name": "Amazon.com Inc.",          "sector": "Consumer"},
    {"symbol": "META",  "name": "Meta Platforms",           "sector": "Technology"},
    {"symbol": "NFLX",  "name": "Netflix Inc.",             "sector": "Entertainment"},
    {"symbol": "DIS",   "name": "Walt Disney Co.",          "sector": "Entertainment"},
    {"symbol": "JPM",   "name": "JPMorgan Chase",           "sector": "Finance"},
    {"symbol": "V",     "name": "Visa Inc.",                "sector": "Finance"},
    {"symbol": "MA",    "name": "Mastercard Inc.",          "sector": "Finance"},
    {"symbol": "UNH",   "name": "UnitedHealth Group",       "sector": "Healthcare"},
    {"symbol": "XOM",   "name": "ExxonMobil Corp.",         "sector": "Oil & Gas"},
    {"symbol": "CVX",   "name": "Chevron Corp.",            "sector": "Oil & Gas"},
    {"symbol": "BP",    "name": "BP p.l.c.",                "sector": "Oil & Gas"},
    {"symbol": "BA",    "name": "Boeing Co.",               "sector": "Aerospace"},
    {"symbol": "LMT",   "name": "Lockheed Martin",          "sector": "Defense"},
    {"symbol": "MO",    "name": "Altria Group",             "sector": "Tobacco"},
    {"symbol": "F",     "name": "Ford Motor Co.",           "sector": "Automotive"},
    {"symbol": "INTU",  "name": "Intuit Inc.",              "sector": "Technology"},
    {"symbol": "COP",   "name": "ConocoPhillips",           "sector": "Oil & Gas"},
    {"symbol": "NIO",   "name": "NIO Inc.",                 "sector": "Automotive"},
]
 
# ── static scores (ground-truth training labels, always used for known stocks) ─
ESG_SCORES = {
    "AAPL":  {"environmental": 78, "social": 65, "governance": 55, "carbon": 82},
    "MSFT":  {"environmental": 90, "social": 80, "governance": 85, "carbon": 92},
    "GOOGL": {"environmental": 85, "social": 70, "governance": 75, "carbon": 88},
    "ADBE":  {"environmental": 88, "social": 78, "governance": 80, "carbon": 90},
    "CRM":   {"environmental": 92, "social": 85, "governance": 82, "carbon": 94},
    "NVDA":  {"environmental": 70, "social": 68, "governance": 72, "carbon": 74},
    "AMD":   {"environmental": 72, "social": 65, "governance": 70, "carbon": 75},
    "TSLA":  {"environmental": 85, "social": 45, "governance": 40, "carbon": 80},
    "NEE":   {"environmental": 95, "social": 80, "governance": 85, "carbon": 96},
    "ENPH":  {"environmental": 97, "social": 82, "governance": 80, "carbon": 98},
    "AMZN":  {"environmental": 60, "social": 45, "governance": 65, "carbon": 58},
    "META":  {"environmental": 65, "social": 35, "governance": 50, "carbon": 62},
    "NFLX":  {"environmental": 68, "social": 60, "governance": 65, "carbon": 70},
    "DIS":   {"environmental": 70, "social": 65, "governance": 60, "carbon": 68},
    "JPM":   {"environmental": 55, "social": 60, "governance": 70, "carbon": 52},
    "V":     {"environmental": 72, "social": 70, "governance": 78, "carbon": 74},
    "MA":    {"environmental": 74, "social": 72, "governance": 80, "carbon": 76},
    "UNH":   {"environmental": 58, "social": 50, "governance": 65, "carbon": 55},
    "XOM":   {"environmental": 12, "social": 35, "governance": 45, "carbon": 10},
    "CVX":   {"environmental": 15, "social": 38, "governance": 48, "carbon": 13},
    "BP":    {"environmental": 20, "social": 40, "governance": 50, "carbon": 18},
    "BA":    {"environmental": 30, "social": 42, "governance": 40, "carbon": 28},
    "LMT":   {"environmental": 28, "social": 45, "governance": 55, "carbon": 25},
    "MO":    {"environmental": 20, "social": 15, "governance": 45, "carbon": 22},
    "F":     {"environmental": 45, "social": 50, "governance": 48, "carbon": 42},
    "INTU":  {"environmental": 82, "social": 75, "governance": 78, "carbon": 84},
    "COP":   {"environmental": 18, "social": 40, "governance": 52, "carbon": 15},
    "NIO":   {"environmental": 80, "social": 55, "governance": 42, "carbon": 78},
}
 
# ── feature fetching ──────────────────────────────────────────────────────────
 
def _fetch_features(symbol: str, sector: str) -> dict | None:
    """
    Fetch the financial features needed by each model.
 
    Sources:
      - gross_margin, operating_margin: Finnhub /stock/metric (grossMarginTTM, operatingMarginTTM)
      - rd_ratio:   yfinance income statement  (researchAndDevelopment / totalRevenue)
      - capex_ratio: yfinance cash flow statement (capitalExpenditures / totalRevenue)
 
    Returns a dict or None if fetching fails.
    """
    try:
        import requests
        import yfinance as yf
 
        FINNHUB_KEY = "d73gq8pr01qjjol311a0d73gq8pr01qjjol311ag"
        url = f"https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all&token={FINNHUB_KEY}"
        resp = requests.get(url, timeout=8).json()
        m = resp.get("metric", {})
 
        gross_margin     = m.get("grossMarginTTM")    or 0.0
        operating_margin = m.get("operatingMarginTTM") or 0.0
 
        # Convert from percentage (Finnhub returns e.g. 44.1) to ratio (0.441)
        if gross_margin > 1:
            gross_margin /= 100
        if operating_margin > 1:
            operating_margin /= 100
 
        # yfinance for R&D and capex ratios
        ticker = yf.Ticker(symbol)
        income = ticker.financials       # rows: index=metric, cols=dates
        cashflow = ticker.cashflow
 
        rd_ratio    = 0.0
        capex_ratio = 0.0
 
        try:
            revenue = float(income.loc["Total Revenue"].iloc[0])
            if revenue > 0:
                if "Research And Development" in income.index:
                    rd = float(income.loc["Research And Development"].iloc[0])
                    rd_ratio = abs(rd) / revenue
                if "Capital Expenditure" in cashflow.index:
                    capex = float(cashflow.loc["Capital Expenditure"].iloc[0])
                    capex_ratio = abs(capex) / revenue
        except Exception:
            pass
 
        # Clamp ratios to [0, 1]
        gross_margin     = max(0.0, min(1.0, gross_margin))
        operating_margin = max(-0.5, min(1.0, operating_margin))
        rd_ratio         = max(0.0, min(0.5, rd_ratio))
        capex_ratio      = max(0.0, min(0.5, capex_ratio))
 
        return {
            "gross_margin":     gross_margin,
            "operating_margin": operating_margin,
            "rd_ratio":         rd_ratio,
            "capex_ratio":      capex_ratio,
        }
 
    except Exception as e:
        print(f"[esg_data] Feature fetch failed for {symbol}: {e}")
        return None
 
 
def _encode_sector(sector: str) -> int:
    """Encode sector string; unknown sectors map to the closest known class."""
    if sector in _sector_classes:
        return int(_sector_encoder.transform([sector])[0])
    # fallback: use 'Technology' as a neutral default
    fallback = "Technology" if "Technology" in _sector_classes else _sector_classes[0]
    return int(_sector_encoder.transform([fallback])[0])
 
 
def _industry_type(sector: str) -> int:
    return _industry_map.get(sector, 2)   # default to Tech (2) if unknown
 
 
def _clamp(val: float, lo=0, hi=100) -> int:
    return int(max(lo, min(hi, round(val))))
 
 
# ── public API ────────────────────────────────────────────────────────────────
 
def predict_esg(symbol: str, sector: str) -> dict | None:
    """
    Predict ESG scores for a stock using the three trained models.
 
    Inputs fetched automatically:
      E model: sector, industry_type, capex_ratio, operating_margin
      S model: sector, industry_type, gross_margin, rd_ratio
      G model: sector, industry_type, operating_margin, gross_margin
 
    Returns dict with keys: environmental, social, governance, carbon
    or None if the models aren't loaded or features can't be fetched.
    """
    if not _MODELS_LOADED:
        return None
 
    features = _fetch_features(symbol, sector)
    if features is None:
        return None
 
    sec_enc  = _encode_sector(sector)
    ind_type = _industry_type(sector)
 
    gm  = features["gross_margin"]
    om  = features["operating_margin"]
    rd  = features["rd_ratio"]
    cap = features["capex_ratio"]
 
    X_E = np.array([[sec_enc, ind_type, cap, om]])
    X_S = np.array([[sec_enc, ind_type, gm,  rd]])
    X_G = np.array([[sec_enc, ind_type, om,  gm]])
 
    E = _clamp(_model_E.predict(X_E)[0])
    S = _clamp(_model_S.predict(X_S)[0])
    G = _clamp(_model_G.predict(X_G)[0])
    C = _clamp(E * 0.7 + G * 0.3)   # carbon derived from E + G
    print(E)
    return {"environmental": E, "social": S, "governance": G, "carbon": C}
 
 
def get_esg(symbol: str, sector: str = "Technology") -> dict:
    """
    Main entry point. Returns static scores for known stocks,
    model predictions for everything else.
    """
    symbol = symbol.upper()
 
    # Known stock → return ground-truth labels
    if symbol in ESG_SCORES:
        return ESG_SCORES[symbol]
 
    # Unknown stock → predict
    predicted = predict_esg(symbol, sector)
    if predicted:
        return predicted
 
    # Last resort: sector median fallback
    SECTOR_DEFAULTS = {
        "Oil & Gas":    {"environmental": 15, "social": 38, "governance": 48, "carbon": 14},
        "Clean Energy": {"environmental": 96, "social": 81, "governance": 80, "carbon": 91},
        "Energy":       {"environmental": 82, "social": 72, "governance": 80, "carbon": 85},
        "Technology":   {"environmental": 78, "social": 70, "governance": 72, "carbon": 80},
        "Automotive":   {"environmental": 70, "social": 50, "governance": 43, "carbon": 67},
        "Finance":      {"environmental": 67, "social": 67, "governance": 76, "carbon": 67},
        "Healthcare":   {"environmental": 58, "social": 50, "governance": 65, "carbon": 55},
        "Consumer":     {"environmental": 60, "social": 45, "governance": 65, "carbon": 58},
        "Entertainment":{"environmental": 69, "social": 62, "governance": 62, "carbon": 69},
        "Aerospace":    {"environmental": 30, "social": 42, "governance": 40, "carbon": 28},
        "Defense":      {"environmental": 28, "social": 45, "governance": 55, "carbon": 25},
        "Tobacco":      {"environmental": 20, "social": 15, "governance": 45, "carbon": 22},
    }
    return SECTOR_DEFAULTS.get(sector, {"environmental": 50, "social": 50, "governance": 50, "carbon": 50})