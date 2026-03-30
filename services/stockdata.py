import requests
import time
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
API_KEY = os.getenv('FINNHUB_API_KEY')
BASE = "https://finnhub.io/api/v1"
def get_company_profile(symbol):
    url = f"{BASE}/stock/profile2?symbol={symbol}&token={API_KEY}"
    return requests.get(url).json()

def get_quote(symbol):
    data = requests.get(f"{BASE}/quote?symbol={symbol}&token={API_KEY}").json()
    return {
        'current': data['c'],
        'high': data['h'],
        'low': data['l'],
        'open': data['o'],
        'prev_close': data['pc'],
        'change': round(data['c'] - data['pc'], 2),
        'change_pct': round(((data['c'] - data['pc']) / data['pc']) * 100, 2)
    }

def get_metrics(symbol):
    data = requests.get(f"{BASE}/stock/metric?symbol={symbol}&metric=all&token={API_KEY}").json()
    m = data.get('metric', {})
    return {
        '52_week_high': m.get('52WeekHigh'),
        '52_week_low': m.get('52WeekLow'),
        'beta': m.get('beta'),
        'avg_volume_10d': m.get('10DayAverageTradingVolume'),
        'pb_ratio': m.get('pbAnnual'),
        'current_ratio': m.get('currentRatioAnnual'),
        'quick_ratio': m.get('quickRatioAnnual'),
        'gross_margin': m.get('grossMarginTTM'),
        'operating_margin': m.get('operatingMarginTTM'),
        'revenue_growth_5y': m.get('revenueGrowth5Y')
    }

def get_recommendations(symbol):
    data = requests.get(f"{BASE}/stock/recommendation?symbol={symbol}&token={API_KEY}").json()
    if not data:
        return None
    latest = data[0]
    total = latest['strongBuy'] + latest['buy'] + latest['hold'] + latest['sell'] + latest['strongSell']
    buy_signals = latest['strongBuy'] + latest['buy']
    sell_signals = latest['sell'] + latest['strongSell']
    return {
        'strong_buy': latest['strongBuy'],
        'buy': latest['buy'],
        'hold': latest['hold'],
        'sell': latest['sell'],
        'strong_sell': latest['strongSell'],
        'total': total,
        'buy_signals': buy_signals,
        'sell_signals': sell_signals,
        'sentiment': 'Bullish' if buy_signals > sell_signals else 'Bearish'
    }

def get_earnings(symbol):
    data = requests.get(f"{BASE}/stock/earnings?symbol={symbol}&token={API_KEY}").json()
    return [{
        'period': e.get('period'),
        'actual': e.get('actual'),
        'estimate': e.get('estimate'),
        'surprise_pct': e.get('surprisePercent')
    } for e in data[:4]]

def get_candles(symbol, period):
    ticker = yf.Ticker(symbol)
    
    # Expanded mapping for all timeline buttons
    mapping = {
        '1D':  {'period': '1d',  'interval': '5m'},
        '1M':  {'period': '1mo', 'interval': '1d'},
        '1Y':  {'period': '1y',  'interval': '1wk'},
        '5Y':  {'period': '5y',  'interval': '1wk'},  # Weekly dots for 5 years
        'ALL': {'period': 'max', 'interval': '1mo'}   # Monthly dots for all history
    }
    
    conf = mapping.get(period, mapping['1M'])
    
    # Fetch data from yfinance
    df = ticker.history(period=conf['period'], interval=conf['interval'])
    
    if df.empty:
        return []

    chart_data = []
    for index, row in df.iterrows():
        chart_data.append({
            'time': int(index.timestamp()),
            'price': round(row['Close'], 2)
        })
        
    return chart_data

def get_company_info(symbol):
    data = requests.get(f"{BASE}/stock/profile2?symbol={symbol}&token={API_KEY}").json()
    return {
        'name': data.get('name'),
        'industry': data.get('finnhubIndustry'),
        'market_cap': data.get('marketCapitalization'),
        'logo': data.get('logo'),
        'website': data.get('weburl')
    }

def search_stocks(query):
    data = requests.get(f"{BASE}/search?q={query}&token={API_KEY}").json()
    results = data.get('result', [])
    filtered = [
        {'symbol': r['symbol'], 'name': r['description']}
        for r in results
        if r.get('type') == 'Common Stock' 
        and '.' not in r['symbol']
        and len(r['symbol']) <= 5
    ]
    return filtered[:10]