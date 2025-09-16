import configparser
import pandas_ta as pta
from datetime import datetime, timedelta
import pandas as pd
import logging

# --- Global State for Strategy 2 ---
# In a real-world application, this state should be persisted in a database or a file.
open_positions = {}
order_history = []
daily_pnl = 0
ltp_cache = {}
# ---

def _load_config():
    config = configparser.ConfigParser()
    try:
        config.read('config.ini')
    except Exception as e:
        logging.error(f"Error reading config.ini: {e}")
    return config

def _calculate_avwap_and_bands(df, std_dev_multiplier=2, avwap_period=20):
    """Calculates Anchored VWAP and standard deviation bands."""
    df['avwap'] = pta.vwap(df['high'], df['low'], df['close'], df['volume'], anchor="D")
    df['stdev'] = pta.stdev(df['close'], length=avwap_period)
    df['upper_band'] = df['avwap'] + (std_dev_multiplier * df['stdev'])
    df['lower_band'] = df['avwap'] - (std_dev_multiplier * df['stdev'])
    return df

def select_stocks_for_the_day(manager):
    """
    Selects up to 2 stocks based on market sentiment (advance/decline) and liquidity.
    Uses Alice Blue historical data to determine this.
    """
    config = _load_config()
    liquidity_threshold = config.getfloat('strategy2', 'LIQUIDITY_THRESHOLD', fallback=10000000)

    if not manager or not manager.is_initialized:
        logging.warning("Strategy2: Instrument manager not ready for stock selection.")
        return []

    # Get all NSE equity instruments from the map
    all_nse_symbols = [key[1] for key in manager.instrument_map.keys() if key[0] == 'NSE' and '-EQ' in key[1]]

    advances = 0
    declines = 0
    liquid_stocks = []

    to_date = datetime.now()
    from_date = to_date - timedelta(days=3) # Get last 3 days to ensure we have at least 2 data points

    # Note: Fetching historical data for all ~2000 NSE symbols can be very slow and may hit API rate limits.
    # In a production environment, you might want to:
    # 1. Run this selection process on a powerful server with a fast connection.
    # 2. Use a pre-filtered list of liquid stocks instead of all NSE symbols.
    # 3. Introduce a delay between API calls to manage rate limits.
    for symbol in all_nse_symbols:
        mapped_inst = manager.get_mapped_instrument(symbol, 'NSE')
        if not mapped_inst or not mapped_inst.get('alice'):
            continue

        hist_data = manager.data_feed.get_historical_data(mapped_inst['alice'], from_date, to_date, 'D')

        if hist_data and len(hist_data) >= 2:
            df = pd.DataFrame(hist_data)
            df['change'] = df['close'].diff()
            latest = df.iloc[-1]

            traded_value = latest['close'] * latest['volume']
            if traded_value >= liquidity_threshold:
                stock_info = {
                    'tradingsymbol': symbol,
                    'change': latest['change'],
                    'last_price': latest['close']
                }
                liquid_stocks.append(stock_info)
                if latest['change'] > 0:
                    advances += 1
                elif latest['change'] < 0:
                    declines += 1

    if not liquid_stocks:
        logging.warning("Strategy2: No liquid stocks found matching criteria.")
        return []

    liquid_stocks.sort(key=lambda x: x['change'], reverse=True)

    if advances > declines:
        logging.info("Market sentiment is Bullish. Selecting top 2 gainers.")
        return liquid_stocks[:2]
    else:
        logging.info("Market sentiment is Bearish. Selecting top 2 losers for shorting.")
        return liquid_stocks[-2:]

def run_trade_logic(manager, symbol):
    """
    Runs the AVWAP breakout logic for a single stock.
    """
    global daily_pnl

    config = _load_config()
    daily_stop_loss = config.getfloat('strategy2', 'DAILY_STOP_LOSS', fallback=-3000)

    if daily_pnl <= daily_stop_loss:
        logging.warning(f"Daily stop loss of {daily_stop_loss} reached. No new trades for {symbol}.")
        return

    mapped_inst = manager.get_mapped_instrument(symbol, 'NSE')
    if not mapped_inst or not mapped_inst.get('alice') or not mapped_inst.get('kite'):
        logging.error(f"Could not find mapped instrument for {symbol}")
        return

    to_date = datetime.now()
    from_date = to_date - timedelta(days=5) # Fetch enough data for AVWAP calculation
    historical_data = manager.data_feed.get_historical_data(mapped_inst['alice'], from_date, to_date, "1")

    if not historical_data:
        logging.warning(f"Could not fetch historical data for {symbol} from Alice Blue.")
        return

    df = pd.DataFrame(historical_data)
    df['date'] = pd.to_datetime(df['time'])
    df.set_index('date', inplace=True)
    df_5min = df.resample('5T').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()

    if df_5min.empty:
        logging.warning(f"Not enough data to calculate AVWAP for {symbol}")
        return

    df_5min = _calculate_avwap_and_bands(df_5min)
    latest_candle = df_5min.iloc[-1]
    ltp_cache[symbol] = latest_candle['close']
    position = open_positions.get(symbol)
    broker = manager.broker

    if position:
        if position['direction'] == 'BUY' and latest_candle['close'] < latest_candle['lower_band']:
            _close_position(broker, symbol, position, latest_candle['close'])
        elif position['direction'] == 'SELL' and latest_candle['close'] > latest_candle['upper_band']:
            _close_position(broker, symbol, position, latest_candle['close'])
    else:
        if latest_candle['close'] > latest_candle['upper_band']:
            _open_position(broker, symbol, 'BUY', latest_candle['close'])
        elif latest_candle['close'] < latest_candle['lower_band']:
            _open_position(broker, symbol, 'SELL', latest_candle['close'])

    _update_pnl()

def _open_position(broker, symbol, direction, price):
    config = _load_config()
    capital_per_trade = config.getfloat('strategy2', 'CAPITAL_PER_TRADE', fallback=10000)
    quantity = int(capital_per_trade / price)
    if quantity == 0:
        logging.warning(f"Could not open position for {symbol}. Calculated quantity is 0.")
        return

    order_id = broker.place_order(symbol, quantity, direction, exchange='NSE', product='MIS')
    if order_id:
        position = {
            "tradingsymbol": symbol, "quantity": quantity if direction == 'BUY' else -quantity,
            "average_price": price, "last_price": price, "pnl": 0, "direction": direction, "order_id": order_id
        }
        open_positions[symbol] = position
        order_history.append({
            "tradingsymbol": symbol, "transaction_type": direction, "quantity": quantity, "price": price,
            "status": "OPEN", "order_id": order_id
        })
        logging.info(f"Opened {direction} position for {symbol} at {price}")

def _close_position(broker, symbol, position, price):
    global daily_pnl

    direction = 'SELL' if position['direction'] == 'BUY' else 'BUY'
    order_id = broker.place_order(symbol, abs(position['quantity']), direction, exchange='NSE', product='MIS')
    if order_id:
        realized_pnl = (price - position['average_price']) * position['quantity']
        daily_pnl += realized_pnl
        del open_positions[symbol]
        for order in order_history:
            if order.get('order_id') == position['order_id']:
                order['status'] = 'CLOSED'
                break
        order_history.append({
            "tradingsymbol": symbol, "transaction_type": direction, "quantity": abs(position['quantity']),
            "price": price, "status": "CLOSED", "order_id": order_id
        })
        logging.info(f"Closed position for {symbol}. Realized P&L: {realized_pnl:.2f}")

def _update_pnl():
    for symbol, position in open_positions.items():
        current_ltp = ltp_cache.get(symbol, position['average_price'])
        position['last_price'] = current_ltp
        pnl_val = (current_ltp - position['average_price']) * position['quantity']
        position['pnl'] = pnl_val

def get_strategy2_state():
    """Returns the current state of Strategy 2 for the UI."""
    unrealized_pnl = sum(p['pnl'] for p in open_positions.values())
    total_pnl = daily_pnl + unrealized_pnl
    return {
        "open_positions": list(open_positions.values()),
        "order_history": order_history,
        "pnl": total_pnl
    }
