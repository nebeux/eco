# 🌿 Eco — ESG-Aware Stock Trading Simulator

> Built for **Hackonomics 2026, EcoHack, and EcoHacks** · All trades are simulated · Data from Finnhub & yfinance

Hey there! Welcome to Eco's repository.
Eco is a paper trading app that lets you invest a virtual $10,000 in real stocks — while tracking the environmental cost of your portfolio. Every buy you make adds to your **carbon impact score**, rewarding greener investment decisions.

---

## Features

- **Paper trading** — buy and sell real stocks with $10,000 of virtual money
- **Live stock data** — real-time quotes, price charts (1D / 1M / 1Y / 5Y / ALL), analyst recommendations, and key financial metrics via Finnhub and yfinance
- **ESG scoring** — Environmental, Social, and Governance scores for every stock, powered by three custom-trained ML models.
- **Carbon impact tracking** — every purchase accumulates a carbon impact score based on the stock's carbon rating and the number of shares bought
- **Portfolio dashboard** — holdings table, gain/loss tracking, portfolio value chart over time, and transaction history
- **Leaderboard** — compete against other users by total portfolio value
- **ESG education** — interactive vocab cards on the home page explaining E, S, G, Carbon Score, P/E, Beta, and Dividends
- **Dark mode** — persisted via localStorage

---

## Tech Stack

| Layer | Stack |
|---|---|
| Backend | Python · Flask · SQLAlchemy · Postgre/Supabase |
| Frontend | Jinja2 templates · vanilla JS · Chart.js |
| Stock data | Finnhub API · yfinance |
| ESG model | scikit-learn (Gradient Boosting) · joblib |

---

## Project Structure

```
eco/
├── app.py                  # Flask app — routes, DB models, buy/sell logic
├── models/
│   └── esg_model.joblib    # Trained ESG prediction model (3 separate GBR models)
├── services/
│   ├── esg_data.py         # ESG scores + ML prediction logic
│   └── stockdata.py        # Finnhub + yfinance data fetching
├── templates/
│   ├── base.html           # Nav, dark mode, shared layout
│   ├── index.html          # Landing page + ESG vocab cards
│   ├── stocks.html         # Stock browser with ESG filters
│   ├── stock.html          # Individual stock page
│   ├── portfolio.html      # Portfolio dashboard
│   ├── auth.html           # Login / register
│   └── leaderboard.html    # Leaderboard
├── static/
│   ├── css/style.css
|   ├── js/stock_trade.js
│   └── js/main.js
└── requirements.txt
```
---

## ESG Model

Eco uses three separate **Gradient Boosting Regressor** models to predict E, S, and G scores independently for any stock — including ones not in the static training set.

| Model | Features used |
|---|---|
| **E** (Environmental) | Sector, industry type, capex ratio, operating margin |
| **S** (Social) | Sector, industry type, gross margin, R&D ratio |
| **G** (Governance) | Sector, industry type, operating margin, gross margin |
| **Carbon** | Derived: `E × 0.7 + G × 0.3` |

All features are fetched free via **Finnhub** (margins) and **yfinance** (R&D, capex). The model was trained on 80+ labeled stocks across 24 sectors including airlines, clean energy, mining, pharma, EVs, logistics, and more.

**R² scores:** E = 0.997 · S = 0.990 · G = 0.991

To retrain the model, update `TRAINING_DATA` in the training script and run it — it outputs a new `esg_model.joblib` to drop into `models/`.

---

## Carbon Impact Score

Every time you **buy** a stock, your carbon impact increases:

```
impact = shares × (1 - carbon_score / 100)
```

The score is **static**. Once you make an impact, it stays.

---

## API Keys

The app uses a Finnhub free-tier API key configured in `services/stockdata.py`. 

---

## Notes

- Trades are **simulated** — no real money involved
- Stock data is live but ESG scores are model-predicted (not official ratings)
- The app supports any ticker Finnhub and yfinance can find, not just the 28 in the default stock list
