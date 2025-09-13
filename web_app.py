from flask import Flask, jsonify, render_template
import threading
import time
import data_handler
import strategy

# --- Global State Management ---
# This dictionary holds the shared state between the background thread and Flask requests.
app_state = {
    "is_paused": True,  # Start in a paused state by default
    "latest_strategy_state": None,
    "strategy_processor": strategy.StrategyProcessor(),
}
# A lock to ensure thread-safe access to the app_state dictionary
state_lock = threading.Lock()


# Create the Flask web application
app = Flask(__name__)

def run_simulation_thread():
    """
    This function runs in a background thread and continuously processes the data feed.
    """
    # This function needs access to the global state and lock
    global app_state, state_lock

    market_data = data_handler.load_data_from_csv()
    data_feed = data_handler.replay_data(market_data)

    for tick in data_feed:
        # This loop will effectively pause the thread until 'is_paused' is False
        while True:
            with state_lock:
                if not app_state["is_paused"]:
                    break
            # Sleep for a short duration while paused to avoid busy-waiting
            time.sleep(0.1)

        # Acquire lock to safely update the shared state
        with state_lock:
            processor = app_state["strategy_processor"]
            app_state["latest_strategy_state"] = processor.process_tick(tick)

@app.route('/')
def index():
    """
    Serves the main HTML page for the terminal.
    """
    return render_template('index.html')

def format_state_for_json(state):
    """
    Converts the strategy state, which contains pandas objects, into a JSON-serializable dictionary.
    """
    if not state:
        return {}

    # Convert pandas Series to dict and handle NaNs for JSON conversion
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
            'direction': pos['direction'],
            'entry_price': f"{pos['entry_price']:.2f}",
            'status': pos['status']
        }

    return {
        'latest_tick': latest_tick_dict,
        'position': position_info,
        'live_pnl': f"{state.get('live_pnl', 0):.2f}",
        'log': state.get('log', [])[-5:] # Last 5 log entries
    }

@app.route('/status')
def status():
    """
    Provides the latest strategy state as JSON.
    """
    with state_lock:
        state_json = format_state_for_json(app_state.get('latest_strategy_state'))
    return jsonify(state_json)

@app.route('/pause', methods=['POST'])
def pause():
    """
    Pauses the simulation background thread.
    """
    with state_lock:
        app_state['is_paused'] = True
        if app_state.get('strategy_processor'):
             app_state['strategy_processor'].log.append("SIM: Paused by user.")
    return jsonify({"status": "paused"})

@app.route('/resume', methods=['POST'])
def resume():
    """
    Resumes the simulation background thread.
    """
    with state_lock:
        app_state['is_paused'] = False
        if app_state.get('strategy_processor'):
             app_state['strategy_processor'].log.append("SIM: Resumed by user.")
    return jsonify({"status": "resumed"})

if __name__ == '__main__':
    # Start the background thread for the simulation
    simulation_thread = threading.Thread(target=run_simulation_thread, daemon=True)
    simulation_thread.start()

    # Note: In a real production environment, you would use a proper WSGI server
    # like Gunicorn or uWSGI instead of Flask's built-in development server.
    app.run(debug=False, host='0.0.0.0', port=8080)
