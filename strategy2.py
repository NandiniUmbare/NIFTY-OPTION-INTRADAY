import configparser
import pandas_ta as pta
from datetime import datetime, timedelta
import pandas as pd

# --- Global State for Strategy 2 ---
open_positions = {}
order_history = []
pnl = 0
ltp = {}
# ---

def _load_nifty500_symbols():
    try:
        with open('nifty500.txt', 'r') as f:
            # Skip header lines that start with #
            return [line.strip() for line in f.readlines() if not line.startswith('#')]
    except FileNotFoundError:
        print("Error: nifty500.txt not found.")
        return []

def _load_config():
    config = configparser.ConfigParser()
    try:
        config.read('config.ini')
    except FileNotFoundError:
        print("Error: config.ini not found.")
    return config

def _calculate_avwap_and_bands(df, std_dev_multiplier=2, avwap_period=20):
    df['avwap'] = pta.vwap(df['high'], df['low'], df['close'], df['volume'], anchor="D")
    df['stdev'] = pta.stdev(df['close'], length=avwap_period)
    df['upper_band'] = df['avwap'] + (std_dev_multiplier * df['stdev'])
    df['lower_band'] = df['avwap'] - (std_dev_multiplier * df['stdev'])
    return df

def select_stocks_for_the_day(broker):
    nifty500_symbols = _load_nifty500_symbols()
    config = _load_config()
    liquidity_threshold = config.getfloat('strategy2', 'LIQUIDITY_THRESHOLD', fallback=10000000)

    if not broker or not nifty500_symbols:
        return []

    quotes = broker.get_quotes(nifty500_symbols)
    if not quotes:
        print("Could not fetch quotes for stock selection.")
        return []

    advances = 0
    declines = 0
    liquid_stocks = []

    for symbol in quotes:
        quote = quotes[symbol]
        traded_value = quote['last_price'] * quote['volume']
        if traded_value >= liquidity_threshold:
            liquid_stocks.append(quote)
            if quote['change'] > 0:
                advances += 1
            elif quote['change'] < 0:
                declines += 1

    if not liquid_stocks:
        return []

    liquid_stocks.sort(key=lambda x: x['change'], reverse=True)

    if advances > declines:
        return liquid_stocks[:2]
    else:
        return liquid_stocks[-2:]

    return []

def run_trade_logic(broker, symbol):
    global pnl

    config = _load_config()
    daily_stop_loss = config.getfloat('strategy2', 'DAILY_STOP_LOSS', fallback=-3000)

    if pnl <= daily_stop_loss:
        print(f"Daily stop loss of {daily_stop_loss} reached. No new trades will be placed.")
        return

    instrument_token = broker.get_instrument_token(symbol)
    if not instrument_token:
        print(f"Could not get instrument token for {symbol}")
        return

    to_date = datetime.now()
    from_date = to_date - timedelta(days=5)
    historical_data = broker.get_historical_data(instrument_token, from_date, to_date, "5minute")

    if not historical_data:
        print(f"Could not fetch historical data for {symbol}")
        return

    df = pd.DataFrame(historical_data)
    df = _calculate_avwap_and_bands(df)
    latest_candle = df.iloc[-1]

    ltp[symbol] = latest_candle['close']

    position = open_positions.get(symbol)

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
        print(f"Could not calculate quantity for {symbol}. Price: {price}")
        return

    order_id = broker.place_order(symbol, quantity, direction)
    if order_id:
        position = {
            "tradingsymbol": symbol,
            "quantity": quantity if direction == 'BUY' else -quantity,
            "average_price": price,
            "last_price": price,
            "pnl": 0,
            "direction": direction,
            "order_id": order_id
        }
        open_positions[symbol] = position
        order_history.append({
            "tradingsymbol": symbol, "transaction_type": direction, "quantity": quantity, "price": price, "status": "OPEN", "order_id": order_id
        })
        print(f"Opened {direction} position for {symbol} at {price}")

def _close_position(broker, symbol, position, price):
    global pnl

    direction = 'SELL' if position['direction'] == 'BUY' else 'BUY'
    order_id = broker.place_order(symbol, abs(position['quantity']), direction)
    if order_id:
        realized_pnl = (price - position['average_price']) * position['quantity']
        pnl += realized_pnl
        del open_positions[symbol]
        for order in order_history:
            if order.get('order_id') == position['order_id']:
                order['status'] = 'CLOSED'
                break
        order_history.append({
            "tradingsymbol": symbol, "transaction_type": direction, "quantity": abs(position['quantity']), "price": price, "status": "CLOSED", "order_id": order_id
        })
        print(f"Closed position for {symbol}. Realized P&L: {realized_pnl}")

def _update_pnl():
    unrealized_pnl = 0
    for symbol, position in open_positions.items():
        current_ltp = ltp.get(symbol, position['average_price'])
        position['last_price'] = current_ltp
        pnl_val = (current_ltp - position['average_price']) * position['quantity']
        position['pnl'] = pnl_val
        unrealized_pnl += pnl_val

def get_strategy2_state():
    open_positions_list = list(open_positions.values())
    total_pnl = pnl + sum(p['pnl'] for p in open_positions_list)
    return {
        "open_positions": open_positions_list,
        "order_history": order_history,
        "pnl": total_pnl,
        "ltp": ltp
    }
