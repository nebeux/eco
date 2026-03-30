import os
import requests
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from services.stockdata import get_metrics, get_quote, get_company_profile, get_recommendations
from services.stockdata import search_stocks as do_search
from services.esg_data import STOCKS, ESG_SCORES, get_esg
from dotenv import load_dotenv

app = Flask(__name__)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
load_dotenv()

app.secret_key = os.getenv('SECRET_KEY')
API_KEY = os.getenv('FINNHUB_API_KEY')
# ── database ──────────────────────────────────────────
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ── models ────────────────────────────────────────────
class User(db.Model):
    id                  = db.Column(db.Integer, primary_key=True)
    username            = db.Column(db.String(80), unique=True, nullable=False)
    password            = db.Column(db.String(255), nullable=False)
    balance             = db.Column(db.Float, default=10000.0)
    total_carbon_impact = db.Column(db.Float, default=0.0)

class Holding(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol    = db.Column(db.String(10), nullable=False)
    shares    = db.Column(db.Float, nullable=False)
    avg_price = db.Column(db.Float, nullable=False)

class Transaction(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol        = db.Column(db.String(10), nullable=False)
    shares        = db.Column(db.Float, nullable=False)
    price         = db.Column(db.Float, nullable=False)
    type          = db.Column(db.String(4), nullable=False)  # 'buy' or 'sell'
    carbon_impact = db.Column(db.Float, default=0.0)         # impact of this transaction (0-1000 scale)
    timestamp     = db.Column(db.DateTime, default=db.func.now())

class PortfolioSnapshot(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    value     = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())

with app.app_context():
    db.create_all()
    # migrate existing DBs — add new columns if they don't exist yet
    from sqlalchemy import text
    with db.engine.connect() as conn:
        for col, default in [('total_carbon_impact', '0.0')]:
            try:
                conn.execute(text(f'ALTER TABLE user ADD COLUMN {col} FLOAT DEFAULT {default}'))
                conn.commit()
            except Exception:
                pass
        for col, default in [('carbon_impact', '0.0')]:
            try:
                conn.execute(text(f'ALTER TABLE transaction ADD COLUMN {col} FLOAT DEFAULT {default}'))
                conn.commit()
            except Exception:
                pass

# ── helpers ───────────────────────────────────────────
def get_current_user():
    username = session.get('user')
    if not username:
        return None
    user = User.query.filter_by(username=username).first()
    if not user:
        session.clear()
        return None
    return user

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def calc_carbon_impact(symbol, sector, shares, price):
    """Carbon impact of a single transaction — cumulative, no scale cap.
    impact = shares * (1 - carbon_score/100)
    Buying 10 shares of XOM (carbon=10) → 9.0 impact.
    Buying 10 shares of ENPH (carbon=98) → 0.2 impact.
    """
    esg = get_esg(symbol, sector)
    carbon_score = esg.get('carbon', 50)
    return round(shares * (1 - carbon_score / 100), 4)

def recalc_total_carbon(user):
    """Recalculate total carbon impact from current holdings (dynamic)."""
    holdings = Holding.query.filter_by(user_id=user.id).all()
    total = 0.0
    for h in holdings:
        stock_info = next((s for s in STOCKS if s['symbol'] == h.symbol), None)
        sector = stock_info['sector'] if stock_info else 'Technology'
        esg = get_esg(h.symbol, sector)
        carbon_score = esg.get('carbon', 50)
        total += h.shares * (1 - carbon_score / 100)
    user.total_carbon_impact = round(total, 4)

# ── auth ──────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))
        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        db.session.add(PortfolioSnapshot(user_id=new_user.id, value=10000.0))
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('auth.html', action='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session.clear()
            session['user'] = user.username
            session.permanent = True
            return redirect(url_for('index'))
        flash('Invalid username or password.', 'error')
        return redirect(url_for('login'))
    return render_template('auth.html', action='login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ── pages ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stocks')
def stocks():
    return render_template('stocks.html', stocks=STOCKS, esg_scores=ESG_SCORES)

@app.route('/stock/<symbol>')
def stock(symbol):
    symbol = symbol.upper()
    if '.' in symbol:
        flash('Invalid stock symbol.', 'error')
        return redirect(url_for('stocks'))
    
    try:
        profile = get_company_profile(symbol)
        quote   = get_quote(symbol)
        
        # if quote returns zeros it's an invalid symbol
        if not quote or quote.get('current', 0) == 0:
            flash(f'No data found for {symbol}. It may be delisted or invalid.', 'error')
            return redirect(url_for('stocks'))

        metrics = get_metrics(symbol)
        rec     = get_recommendations(symbol)
        esg     = get_esg(symbol, profile.get('finnhubIndustry', 'Technology'))

        user    = get_current_user()
        holding = None
        if user:
            holding = Holding.query.filter_by(user_id=user.id, symbol=symbol).first()

        return render_template('stock.html',
            symbol=symbol, profile=profile, quote=quote,
            metrics=metrics, rec=rec, esg=esg,
            holding=holding, balance=user.balance if user else None
        )
    except ZeroDivisionError:
        flash(f'{symbol} returned invalid data. Please try another stock.', 'error')
        return redirect(url_for('stocks'))
    except Exception as e:
        flash(f'Could not load {symbol} — {str(e)}', 'error')
        return redirect(url_for('stocks'))

@app.route('/portfolio')
@login_required
def portfolio():
    user     = get_current_user()
    holdings = Holding.query.filter_by(user_id=user.id).all()
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).limit(20).all()
    return render_template('portfolio.html', user=user, holdings=holdings, transactions=transactions)

@app.route('/leaderboard')
def leaderboard():
    users = User.query.all()
    board = []
    for u in users:
        holdings = Holding.query.filter_by(user_id=u.id).all()
        portfolio_value = u.balance
        for h in holdings:
            try:
                q = get_quote(h.symbol)
                portfolio_value += h.shares * q['current']
            except:
                portfolio_value += h.shares * h.avg_price
        gain     = round(portfolio_value - 10000, 2)
        gain_pct = round((gain / 10000) * 100, 2)
        carbon   = round(u.total_carbon_impact or 0, 1)
        board.append({
            'username': u.username,
            'value':    round(portfolio_value, 2),
            'gain':     gain,
            'gain_pct': gain_pct,
            'carbon':   carbon,
        })
    by_value  = sorted(board, key=lambda x: x['value'],  reverse=True)
    by_carbon = sorted(board, key=lambda x: x['carbon'])

    # combined eco_score: 60% returns, 40% carbon (both normalised to 0-100)
    # carbon is inverted: lower impact = higher score
    if board:
        max_carbon = max(e['carbon'] for e in board) or 1
        min_gain   = min(e['gain_pct'] for e in board)
        max_gain   = max(e['gain_pct'] for e in board)
        gain_range = (max_gain - min_gain) or 1
        for e in board:
            returns_norm = ((e['gain_pct'] - min_gain) / gain_range) * 100
            carbon_norm  = (1 - e['carbon'] / max_carbon) * 100
            e['eco_score'] = round(returns_norm * 0.6 + carbon_norm * 0.4, 1)
    by_overall = sorted(board, key=lambda x: x.get('eco_score', 0), reverse=True)

    return render_template('leaderboard.html', by_value=by_value, by_carbon=by_carbon, by_overall=by_overall)

# ── api: portfolio data ───────────────────────────────
@app.route('/api/portfolio')
@login_required
def api_portfolio():
    user     = get_current_user()
    holdings = Holding.query.filter_by(user_id=user.id).all()
    result   = []
    total_invested = 0
    total_value    = 0
    for h in holdings:
        try:
            q   = get_quote(h.symbol)
            cur = q['current']
        except:
            cur = h.avg_price
        value          = h.shares * cur
        cost           = h.shares * h.avg_price
        total_value    += value
        total_invested += cost
        result.append({
            'symbol':    h.symbol,
            'shares':    h.shares,
            'avg_price': round(h.avg_price, 2),
            'cur_price': round(cur, 2),
            'value':     round(value, 2),
            'gain':      round(value - cost, 2),
            'gain_pct':  round(((value - cost) / cost) * 100, 2) if cost else 0
        })
    return jsonify({
        'balance':        round(user.balance, 2),
        'holdings':       result,
        'total_value':    round(total_value + user.balance, 2),
        'total_gain':     round((total_value + user.balance) - 10000, 2),
        'total_gain_pct': round(((total_value + user.balance - 10000) / 10000) * 100, 2)
    })

# ── api: buy ──────────────────────────────────────────
@app.route('/api/buy', methods=['POST'])
@login_required
def buy():
    data   = request.json
    symbol = data['symbol'].upper()
    shares = float(data['shares'])
    price  = float(data['price'])
    sector = data.get('sector', 'Technology')
    total  = shares * price

    user = get_current_user()
    if user.balance < total:
        return jsonify({'error': 'Insufficient funds'}), 400

    user.balance -= total

    # carbon impact for this transaction
    impact = calc_carbon_impact(symbol, sector, shares, price)

    existing = Holding.query.filter_by(user_id=user.id, symbol=symbol).first()
    if existing:
        new_shares         = existing.shares + shares
        new_avg            = ((existing.shares * existing.avg_price) + total) / new_shares
        existing.shares    = new_shares
        existing.avg_price = new_avg
    else:
        db.session.add(Holding(user_id=user.id, symbol=symbol, shares=shares, avg_price=price))

    db.session.flush()  # so recalc sees updated holdings
    recalc_total_carbon(user)

    db.session.add(Transaction(user_id=user.id, symbol=symbol, shares=shares, price=price, type='buy', carbon_impact=impact))
    db.session.commit()
    save_snapshot(user)
    return jsonify({'success': True, 'new_balance': round(user.balance, 2), 'carbon_impact': impact, 'total_carbon_impact': user.total_carbon_impact})

# ── api: sell ─────────────────────────────────────────
@app.route('/api/sell', methods=['POST'])
@login_required
def sell():
    data   = request.json
    symbol = data['symbol'].upper()
    shares = float(data['shares'])
    price  = float(data['price'])
    total  = shares * price

    user     = get_current_user()
    existing = Holding.query.filter_by(user_id=user.id, symbol=symbol).first()

    if not existing or existing.shares < shares:
        return jsonify({'error': 'Not enough shares'}), 400

    user.balance      += total
    existing.shares   -= shares
    if existing.shares == 0:
        db.session.delete(existing)
    db.session.add(Transaction(user_id=user.id, symbol=symbol, shares=shares, price=price, type='sell'))
    db.session.commit()
    save_snapshot(user)
    return jsonify({'success': True, 'new_balance': round(user.balance, 2), 'total_carbon_impact': user.total_carbon_impact})

# ── api: misc ─────────────────────────────────────────
@app.route('/api/esg/<symbol>')
def api_esg(symbol):
    symbol = symbol.upper()
    stock_info = next((s for s in STOCKS if s['symbol'] == symbol), None)
    sector = stock_info['sector'] if stock_info else 'Technology'
    return jsonify(get_esg(symbol, sector))

@app.route('/api/quote/<symbol>')
def quote(symbol):
    return jsonify(get_quote(symbol))

@app.route('/api/search/<query>')
def search_stocks(query):
    return jsonify(do_search(query))

@app.route('/api/candles/<symbol>/<period>')
def candles(symbol, period):
    from services.stockdata import get_candles
    return jsonify(get_candles(symbol, period))

# ── context processor ─────────────────────────────────────────
@app.context_processor
def inject_user():
    user = get_current_user()
    return {
        'current_user': user,
        'nav_balance': f"{user.balance:.2f}" if user else '10,000.00',
        'nav_carbon_impact': round(user.total_carbon_impact or 0, 1) if user else 0
    }

def save_snapshot(user):
    holdings = Holding.query.filter_by(user_id=user.id).all()
    total = user.balance
    for h in holdings:
        try:
            total += h.shares * get_quote(h.symbol)['current']
        except:
            total += h.shares * h.avg_price
    db.session.add(PortfolioSnapshot(user_id=user.id, value=round(total, 2)))
    db.session.commit()

@app.route('/api/portfolio/history')
@login_required
def portfolio_history():
    user = get_current_user()
    snapshots = PortfolioSnapshot.query.filter_by(user_id=user.id).order_by(PortfolioSnapshot.timestamp).all()
    return jsonify([{
        'time': s.timestamp.strftime('%b %d %H:%M'),
        'value': s.value
    } for s in snapshots])

@app.route('/api/news/<symbol>')
def stock_news(symbol):
    import datetime
    to = datetime.date.today().isoformat()
    from_date = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={from_date}&to={to}&token={API_KEY}"
    data = requests.get(url).json()
    return jsonify(data[:6])

@app.route('/api/filings/<symbol>')
def sec_filings(symbol):
    url = f"https://finnhub.io/api/v1/stock/filings?symbol={symbol}&token={API_KEY}"
    data = requests.get(url).json()
    return jsonify(data[:6])

@app.route('/api/portfolio/snapshot', methods=['POST'])
@login_required
def take_snapshot():
    user = get_current_user()
    save_snapshot(user)
    return jsonify({'success': True})
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')