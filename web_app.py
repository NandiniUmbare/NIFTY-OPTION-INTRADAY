from flask import Flask, jsonify, render_template, redirect, request
import pandas as pd
import time
import threading
import strategy
from broker_connection import Broker

# --- Global State Management ---
# Initialize the state dictionary first
app_state = {
    "is_paused": True,
    "latest_strategy_state": None,
    "broker": None, # Will be instantiated and added below
    "strategy_processor": None,
}
state_lock = threading.Lock()

# Create the broker instance, passing the state and lock, then add it to the state
broker_instance = Broker(app_state, state_lock)
app_state["broker"] = broker_instance

app = Flask(__name__)

# --- Web App Routes ---

@app.route('/')
def index():
    if app_state.get('strategy_processor') is None:
        return 'Not logged in. Please <a href="/login">login via broker</a> to start the terminal.'
    return render_template('index.html')

@app.route('/login')
def login():
    with state_lock:
        broker = app_state['broker']
    login_url = broker.get_login_url()
    return redirect(login_url)

@app.route('/connect/kite')
def kite_callback():
    request_token = request.args.get("request_token")
    if not request_token:
        return "Error: No request_token found.", 400

    with state_lock:
        broker = app_state['broker']
        if broker.set_access_token(request_token):
            app_state['strategy_processor'] = strategy.StrategyProcessor(broker)
            log_msg = "Broker login successful. Ready to start live data feed."
            app_state['strategy_processor'].log.append(log_msg)
            # Give the broker a reference to the newly created strategy processor
            broker.set_strategy_processor(app_state['strategy_processor'])
            print(log_msg)
            print("NOTE: The user must now manually start the live data feed.")
            return redirect('/')
        else:
            return "Failed to generate access token.", 400

@app.route('/status')
def status():
    with state_lock:
        if app_state.get('latest_strategy_state') is None:
            # Provide a default initial state for the UI
            processor = app_state.get('strategy_processor')
            log = processor.log if processor else ["Please login."]
            return jsonify({"log": log})
        state_json = format_state_for_json(app_state['latest_strategy_state'])
    return jsonify(state_json)

@app.route('/pause', methods=['POST'])
def pause():
    with state_lock:
        app_state['is_paused'] = True
        if app_state.get('strategy_processor'):
             app_state['strategy_processor'].log.append("Request to PAUSE live feed received.")
    return jsonify({"status": "paused"})

@app.route('/resume', methods=['POST'])
def resume():
    with state_lock:
        app_state['is_paused'] = False
        if app_state.get('strategy_processor'):
             app_state['strategy_processor'].log.append("Request to RESUME live feed received.")
    return jsonify({"status": "resumed"})

def format_state_for_json(state):
    # ... (This function remains the same)
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
    # The simulation thread is removed. The app now only serves the UI and API.
    # The live data connection must be initiated by the user after login.
    app.run(debug=False, host='0.0.0.0', port=8080)
