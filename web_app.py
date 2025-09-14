from flask import Flask, jsonify, render_template, redirect, request
from functools import wraps
import threading
import time
import pandas as pd
import schedule
import data_handler
import strategy
import strategy2
from broker_connection import Broker

# --- Global State Management ---
app_state = {
    "is_paused": True,
    "latest_strategy_state": None,
    "broker": Broker(),
    "strategy_processor": None, # Will be created after successful login
    "strategy2_selected_stocks": [],
}
state_lock = threading.Lock()
app = Flask(__name__)

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app_state.get('strategy_processor') is None:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def run_simulation_thread():
    """
    This function runs in a background thread. In our simulation, it provides the data feed.
    In a live setup, this thread would be replaced by the broker's websocket listener.
    """
    global app_state, state_lock

    while app_state.get('strategy_processor') is None:
        time.sleep(1)

    market_data = data_handler.load_data_from_csv()
    data_feed = data_handler.replay_data(market_data)

    for tick in data_feed:
        while True:
            with state_lock:
                if not app_state["is_paused"]:
                    break
            time.sleep(0.1)

        with state_lock:
            processor = app_state["strategy_processor"]
            if processor:
                app_state["latest_strategy_state"] = processor.process_tick(tick)

def run_strategy2_trader():
    """
    This function runs in a background thread and executes the trading logic
    for Strategy 2 every 5 minutes.
    """
    while True:
        with state_lock:
            selected_stocks = app_state.get('strategy2_selected_stocks', [])
            broker = app_state['broker']
            if not broker or not broker.access_token:
                time.sleep(60)
                continue

        if selected_stocks:
            print("Trader: Running trade logic for Strategy 2...")
            for stock in selected_stocks:
                strategy2.run_trade_logic(broker, stock['tradingsymbol'])

        time.sleep(300)

def run_strategy2_scheduler():
    """
    This function runs in a background thread and schedules the stock selection
    for Strategy 2 to run once a day.
    """
    def select_stocks_job():
        print("Scheduler: Running daily stock selection for Strategy 2...")
        with state_lock:
            broker = app_state['broker']
            if not broker or not broker.access_token:
                print("Scheduler: User not logged in. Skipping stock selection.")
                return

        selected_stocks = strategy2.select_stocks_for_the_day(broker)

        with state_lock:
            app_state['strategy2_selected_stocks'] = selected_stocks

        print(f"Scheduler: Selected stocks for today: {[s['tradingsymbol'] for s in selected_stocks]}")

    schedule.every().day.at("09:30").do(select_stocks_job)

    while True:
        schedule.run_pending()
        time.sleep(1)

# --- Web App Routes ---
@app.route('/')
@login_required
def index():
    return render_template('home.html')

@app.route('/strategy')
@login_required
def strategy_page():
    return render_template('strategy.html')

@app.route('/strategy2')
@login_required
def strategy2_page():
    with state_lock:
        selected_stocks = app_state.get('strategy2_selected_stocks', [])
    return render_template('strategy2.html', selected_stocks=selected_stocks)

@app.route('/backtesting')
@login_required
def backtesting_page():
    return render_template('backtesting.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        api_secret = request.form.get('api_secret')
        if not api_key or not api_secret:
            return render_template('login.html', error="API Key and Secret are required.")

        with state_lock:
            broker = app_state['broker']
            broker.set_credentials(api_key, api_secret)
            login_url = broker.get_login_url()

        if login_url:
            return redirect(login_url)
        else:
            return render_template('login.html', error="Could not generate login URL.")

    return render_template('login.html', error=request.args.get('error'))

@app.route('/connect/kite')
def kite_callback():
    request_token = request.args.get("request_token")
    if not request_token:
        return "Error: No request_token found.", 400

    with state_lock:
        broker = app_state['broker']
        if broker.set_access_token(request_token):
            app_state['strategy_processor'] = strategy.StrategyProcessor(broker)
            app_state['strategy_processor'].log.append("Broker connection successful.")
            return redirect('/')
        else:
            return "Failed to generate access token.", 400

@app.route('/status')
def status():
    with state_lock:
        broker = app_state['broker']
        strategy_state = app_state.get('latest_strategy_state')
        strategy2_state = strategy2.get_strategy2_state()

        response_data = {
            "strategy_state": format_state_for_json(strategy_state) if strategy_state else {},
            "account": {},
            "strategy2": strategy2_state
        }

        if broker and broker.access_token:
            margins = broker.get_margins()
            if margins:
                response_data["account"]["funds"] = margins.get('equity', {}).get('available', {}).get('cash', 'N/A')

            positions = broker.get_positions()
            if positions:
                response_data["account"]["positions"] = positions.get('net', [])

            holdings = broker.get_holdings()
            if holdings:
                response_data["account"]["holdings"] = holdings

            orders = broker.get_orders()
            if orders:
                response_data["account"]["orders"] = [o for o in orders if o.get('status') in ['OPEN', 'TRIGGER PENDING']]

    return jsonify(response_data)

@app.route('/pause', methods=['POST'])
def pause():
    with state_lock:
        app_state['is_paused'] = True
        if app_state.get('strategy_processor'):
             app_state['strategy_processor'].log.append("SIM: Paused by user.")
    return jsonify({"status": "paused"})

@app.route('/resume', methods=['POST'])
def resume():
    with state_lock:
        app_state['is_paused'] = False
        if app_state.get('strategy_processor'):
             app_state['strategy_processor'].log.append("SIM: Resumed by user.")
    return jsonify({"status": "resumed"})

def format_state_for_json(state):
    if not state: return {}
    tick = state['latest_tick']
    latest_tick_dict = {
        'timestamp': tick.name.strftime('%Y-%m-%d %H:%M:%S'),
        'close': f"{tick.get('close', 0):.2f}",
        'VWAP': f"{tick.get('VWAP', 0):.2f}" if pd.notna(tick.get('VWAP')) else "N/A",
        'UpperBand': f"{tick.get('UpperBand', 0):.2f}" if pd.notna(tick.get('UpperBand')) else "N/A",
        'LowerBand': f"{tick.get('LowerBand', 0):.2f}" if pd.notna(tick.get('LowerBand')) else "N/A",
    }
    position_info = None
    if state.get('position'):
        pos = state['position']
        position_info = {
            'direction': pos['direction'], 'entry_price': f"{pos['entry_price']:.2f}", 'status': pos['status']
        }
    return {
        'latest_tick': latest_tick_dict, 'position': position_info,
        'live_pnl': f"{state.get('live_pnl', 0):.2f}",
        'log': state.get('log', [])[-5:]
    }

if __name__ == '__main__':
    simulation_thread = threading.Thread(target=run_simulation_thread, daemon=True)
    simulation_thread.start()
    strategy2_scheduler_thread = threading.Thread(target=run_strategy2_scheduler, daemon=True)
    strategy2_scheduler_thread.start()
    strategy2_trader_thread = threading.Thread(target=run_strategy2_trader, daemon=True)
    strategy2_trader_thread.start()
    app.run(debug=False, host='0.0.0.0', port=8080)
