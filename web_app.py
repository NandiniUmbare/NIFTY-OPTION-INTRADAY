from flask import Flask, jsonify, render_template, redirect, request
from functools import wraps
import threading
import time
import pandas as pd
import configparser
import os
import schedule
import logging
import data_handler
import strategy
import strategy2
from instrument_manager import InstrumentManager

# --- Global State Management ---
app_state = {
    "instrument_manager": InstrumentManager(),
    "strategy2_selected_stocks": [],
}
state_lock = threading.Lock()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        manager = app_state.get('instrument_manager')
        if not manager or not manager.is_initialized:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


def run_strategy2_scheduler():
    """
    This function runs in a background thread and schedules the stock selection for Strategy 2.
    """
    def select_stocks_job():
        logging.info("Scheduler: Running daily stock selection for Strategy 2...")
        with state_lock:
            manager = app_state.get('instrument_manager')
            if not manager or not manager.is_initialized:
                logging.warning("Scheduler: Instrument manager not ready. Skipping stock selection.")
                return
        selected_stocks = strategy2.select_stocks_for_the_day(manager)
        with state_lock:
            app_state['strategy2_selected_stocks'] = selected_stocks
        logging.info(f"Scheduler: Selected stocks for today: {[s['tradingsymbol'] for s in selected_stocks]}")
    schedule.every().day.at("09:30").do(select_stocks_job)
    while True:
        schedule.run_pending()
        time.sleep(60)

def run_strategy2_trader():
    """
    This function runs in a background thread and executes the trading logic for Strategy 2.
    """
    while True:
        with state_lock:
            manager = app_state.get('instrument_manager')
            if not manager or not manager.is_initialized:
                time.sleep(60)
                continue
            selected_stocks = app_state.get('strategy2_selected_stocks', [])
        if selected_stocks:
            logging.info("Trader: Running trade logic for Strategy 2...")
            for stock in selected_stocks:
                strategy2.run_trade_logic(manager, stock['tradingsymbol'])
        time.sleep(300) # Run every 5 minutes

# --- Web App Routes ---

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/strategy2')
@login_required
def strategy2_page():
    with state_lock:
        selected_stocks = app_state.get('strategy2_selected_stocks', [])
    return render_template('strategy2.html', selected_stocks=selected_stocks)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # The user must have already filled in their credentials in config.ini
    if request.method == 'POST':
        # Re-initialize the manager to ensure it loads credentials from config.ini
        with state_lock:
            app_state['instrument_manager'] = InstrumentManager()
            manager = app_state['instrument_manager']

        login_url = manager.broker.get_login_url()
        if login_url:
            return redirect(login_url)
        else:
            # This error typically means the API keys in config.ini are missing or invalid
            return render_template('login.html', error="Could not generate Kite login URL. Please check your credentials in config.ini.")

    return render_template('login.html', error=request.args.get('error'))

@app.route('/connect/kite')
def kite_callback():
    request_token = request.args.get("request_token")
    if not request_token:
        return redirect('/login?error=Kite_authentication_failed')
    with state_lock:
        manager = app_state['instrument_manager']
        if not manager.initialize_connections(kite_request_token=request_token):
            return redirect('/login?error=Failed_to_initialize_connections')
        if not manager.build_instrument_map():
            return redirect('/login?error=Failed_to_build_instrument_map')
        logging.info("Connections successful. Redirecting to dashboard.")
    return redirect('/')

@app.route('/status')
def status():
    with state_lock:
        manager = app_state['instrument_manager']
        strategy2_state = strategy2.get_strategy2_state()

        # Add selected stocks to the response for the UI
        strategy2_state['selected_stocks'] = app_state.get('strategy2_selected_stocks', [])

        response_data = {
            "account": {},
            "strategy2": strategy2_state
        }
        if manager and manager.broker and manager.broker.access_token:
            broker = manager.broker
            try:
                margins = broker.kite.margins()
                response_data["account"]["funds"] = margins.get('equity', {}).get('available', {}).get('cash', 'N/A')
                positions = broker.kite.positions().get('net', [])

                # Update P&L for open positions
                if positions:
                    quotes = broker.kite.quote([f"NSE:{p['tradingsymbol']}" for p in positions])
                    for p in positions:
                        ltp = quotes.get(f"NSE:{p['tradingsymbol']}", {}).get('last_price', p['average_price'])
                        p['pnl'] = (ltp - p['average_price']) * p['quantity']

                response_data["account"]["positions"] = positions
                response_data["account"]["holdings"] = broker.kite.holdings()
                all_orders = broker.kite.orders()
                response_data["account"]["orders"] = [o for o in all_orders if o.get('status') in ['OPEN', 'TRIGGER PENDING']]
            except Exception as e:
                logging.error(f"Error fetching account status from Kite: {e}")
    return jsonify(response_data)


if __name__ == '__main__':
    strategy2_scheduler_thread = threading.Thread(target=run_strategy2_scheduler, daemon=True)
    strategy2_trader_thread = threading.Thread(target=run_strategy2_trader, daemon=True)

    strategy2_scheduler_thread.start()
    strategy2_trader_thread.start()

    app.run(debug=False, host='0.0.0.0', port=8080)
