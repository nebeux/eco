












# sample stocks for now, use an api later :D
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
def ESG_SCORES(symbol):
    try:
        data = yf.Ticker(symbol).sustainability
        if data is None:
            return None
        return {
            'environmental': data.loc['environmentScore'].value * 10,
            'social': data.loc['socialScore'].value * 10,
            'governance': data.loc['governanceScore'].value * 10,
            'carbon': data.loc['totalEsg'].value * 10
        }
    except:
        return None
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