import pandas as pd
import numpy as np
from datetime import time

# --- Strategy Parameters ---
STOP_LOSS = -1500  # As a negative value
TAKE_PROFIT = 3000
SPREAD_WIDTH = 300  # 300 points away for the bought option
TRADE_START_TIME = time(9, 30)
ANCHOR_CANDLE_TIME = time(9, 15)
NEAREST_STRIKE_MULTIPLE = 50
LOT_SIZE = 50 # Nifty lot size for P&L calculation

# --- Broker Placeholder Functions ---
# Note: These functions are placeholders. You need to replace them with your actual broker API calls.

def get_market_data_from_broker(instrument_token):
    """
    Placeholder to get live market data.
    Replace this with your broker's API call.
    For now, this will not be used as we are reading from a CSV.
    """
    print("Getting market data from broker (placeholder)...")
    # Example: return kite.quote(instrument_token)
    return None

def place_credit_spread_order(base_strike, direction, entry_price):
    """
    Placeholder to place a credit spread order.
    'direction' can be 'PE' (for bullish) or 'CE' (for bearish).
    """
    print("\n--- Placing New Trade ---")
    if direction == 'PE':
        # Bullish view: Sell PE, Buy farther PE
        sell_strike = base_strike
        buy_strike = base_strike - SPREAD_WIDTH
        print(f"Strategy: Bull Put Spread")
        print(f"Action: SELL NIFTY {sell_strike} PE")
        print(f"Action: BUY NIFTY {buy_strike} PE")
    elif direction == 'CE':
        # Bearish view: Sell CE, Buy farther CE
        sell_strike = base_strike
        buy_strike = base_strike + SPREAD_WIDTH
        print(f"Strategy: Bear Call Spread")
        print(f"Action: SELL NIFTY {sell_strike} CE")
        print(f"Action: BUY NIFTY {buy_strike} CE")
    else:
        print("Invalid direction. Must be 'PE' or 'CE'.")
        return None

    # In a real scenario, this function would return an order_id
    # For simulation, we create a unique ID and store trade info
    order_id = pd.Timestamp.now().timestamp()
    print(f"Order placed at future price: {entry_price:.2f}. Order ID: {order_id}")

    # For P&L simulation, we need to make an assumption about the initial credit.
    # Let's assume a credit of 50 points for simplicity. This is a key assumption.
    initial_credit = 50
    print(f"Assumed Initial Credit Received: {initial_credit * LOT_SIZE}")

    trade_details = {
        'order_id': order_id,
        'direction': direction,
        'entry_price': entry_price,
        'initial_credit': initial_credit,
        'status': 'OPEN'
    }
    return trade_details


def close_position_by_id(trade, exit_price, reason=""):
    """
    Placeholder to close an open position using its ID.
    This function now returns the final P&L of the trade.
    """
    print(f"\n--- Closing Position ---")
    print(f"Action: Closing position with Order ID: {trade['order_id']}")
    if reason:
        print(f"Reason: {reason}")
    # Add your broker's API call to close the position here.

    # P&L Calculation (Simplified)
    pnl = calculate_pnl(trade, exit_price)
    print(f"Exit Price: {exit_price:.2f}, Final P&L: {pnl:.2f}")

    return pnl

# --- P&L Simulation ---
def calculate_pnl(trade, current_price):
    """
    Simulates the P&L of the spread.
    This is a simplified model. A real implementation would need live option prices.
    Assumption: The spread's value changes by a fraction of the underlying's move.
    Let's assume a net delta of 0.2 for the spread.
    """
    price_change = current_price - trade['entry_price']

    # If it's a bull put spread, we profit if the price goes up (or stays same).
    # The value of the spread decreases, so our P&L (from selling) increases.
    if trade['direction'] == 'PE':
        # We sold a put spread. If market goes up, we make money.
        pnl_points = -price_change * 0.2
    # If it's a bear call spread, we profit if the price goes down.
    elif trade['direction'] == 'CE':
        # We sold a call spread. If market goes down, we make money.
        pnl_points = price_change * 0.2

    # Total P&L is the initial credit plus the change in value.
    total_pnl = (trade['initial_credit'] + pnl_points) * LOT_SIZE
    return total_pnl


# --- Core Logic Functions (to be implemented in next steps) ---

def calculate_vwap_and_bands(df):
    """
    Calculates anchored VWAP and bands based on the first 5-minute candle.
    The anchor is set to the candle at ANCHOR_CANDLE_TIME (9:15).
    """
    print("Calculating Anchored VWAP and Bands...")

    # Find the start time for the anchor calculation
    try:
        # Get the date from the first index entry and combine with the anchor time
        anchor_start_time = df.index[0].normalize() + pd.Timedelta(hours=ANCHOR_CANDLE_TIME.hour, minutes=ANCHOR_CANDLE_TIME.minute)
    except IndexError:
        print("Warning: DataFrame is empty. Cannot calculate VWAP.")
        return df

    # Filter the DataFrame to include data from the anchor time onwards
    anchor_df = df[df.index >= anchor_start_time].copy()

    if anchor_df.empty:
        print(f"Warning: No data found on or after the anchor time ({anchor_start_time}). Cannot calculate VWAP.")
        df['VWAP'] = np.nan
        df['UpperBand'] = np.nan
        df['LowerBand'] = np.nan
        return df

    # Calculate typical price, which is used for VWAP
    tp = (anchor_df['high'] + anchor_df['low'] + anchor_df['close']) / 3
    tp_vol = tp * anchor_df['volume']

    # Calculate anchored VWAP
    anchor_df['VWAP'] = tp_vol.cumsum() / anchor_df['volume'].cumsum()

    # Calculate cumulative standard deviation of the close price from the VWAP
    # This gives us the deviation of all prices from the VWAP up to that point in time
    anchor_df['sq_diff'] = ((anchor_df['close'] - anchor_df['VWAP']) ** 2)
    anchor_df['mean_sq_diff'] = anchor_df['sq_diff'].expanding().mean()
    anchor_df['StdDev'] = np.sqrt(anchor_df['mean_sq_diff'])

    # Calculate the bands
    anchor_df['UpperBand'] = anchor_df['VWAP'] + anchor_df['StdDev']
    anchor_df['LowerBand'] = anchor_df['VWAP'] - anchor_df['StdDev']

    # Merge the calculated columns back into the original DataFrame
    # We use .loc to avoid potential SettingWithCopyWarning
    df.loc[:, 'VWAP'] = anchor_df['VWAP']
    df.loc[:, 'UpperBand'] = anchor_df['UpperBand']
    df.loc[:, 'LowerBand'] = anchor_df['LowerBand']

    print("VWAP and Bands calculated successfully.")
    return df

def run_strategy(day_df):
    """
    Runs the trading strategy for a single day of data.
    """
    position = None
    daily_pnl = 0
    trade_count = 0

    # Determine the position of the close relative to the bands for robust crossover detection
    day_df['status'] = np.where(day_df['close'] > day_df['UpperBand'], 'Above',
                                np.where(day_df['close'] < day_df['LowerBand'], 'Below', 'Inside'))
    day_df['prev_status'] = day_df['status'].shift(1)

    for timestamp, row in day_df.iterrows():
        if timestamp.time() < TRADE_START_TIME:
            continue

        # --- Position Management ---
        if position and position['status'] == 'OPEN':
            current_pnl = calculate_pnl(position, row['close'])
            print(f"  -> P&L Check at {timestamp}: Current P&L: {current_pnl:.2f}")

            if current_pnl <= STOP_LOSS or current_pnl >= TAKE_PROFIT:
                reason = "Take-Profit" if current_pnl >= TAKE_PROFIT else "Stop-Loss"
                trade_pnl = close_position_by_id(position, row['close'], reason=f"{reason} triggered at {current_pnl:.2f}")
                daily_pnl += trade_pnl
                position = None  # Reset position to allow new trades
                continue
            else:
                continue # Hold position

        # --- Entry Signal Checks (only if no position is open) ---
        if pd.isna(row['prev_status']):
            continue

        # Bullish Signal
        if row['prev_status'] != 'Above' and row['status'] == 'Above':
            print(f"\n[!] BULLISH SIGNAL at {timestamp}")
            nearest_strike = round(row['close'] / NEAREST_STRIKE_MULTIPLE) * NEAREST_STRIKE_MULTIPLE
            position = place_credit_spread_order(nearest_strike, 'PE', row['close'])
            trade_count += 1
            continue

        # Bearish Signal
        if row['prev_status'] == 'Above' and row['status'] == 'Inside':
            print(f"\n[!] BEARISH SIGNAL at {timestamp}")
            nearest_strike = round(row['close'] / NEAREST_STRIKE_MULTIPLE) * NEAREST_STRIKE_MULTIPLE
            position = place_credit_spread_order(nearest_strike, 'CE', row['close'])
            trade_count += 1
            continue

    return daily_pnl, trade_count

def run_backtest(df):
    """
    Orchestrates the backtest over a multi-day dataframe.
    """
    print("--- Starting Backtest ---")
    all_daily_pnl = []
    total_trades = 0

    # Group data by day
    daily_data_groups = df.groupby(df.index.date)

    for date, day_df in daily_data_groups:
        print(f"\n--- Processing Date: {date} ---")
        if day_df.empty:
            continue

        # Calculate indicators for the day
        day_df_with_indicators = calculate_vwap_and_bands(day_df.copy())

        # Run strategy for the day
        daily_pnl, num_trades = run_strategy(day_df_with_indicators)

        if num_trades > 0:
            all_daily_pnl.append(daily_pnl)
            total_trades += num_trades

    # --- Aggregate and report results ---
    print("\n--- Backtest Summary ---")
    print(f"Total Trading Days: {len(daily_data_groups)}")
    print(f"Total Trades Executed: {total_trades}")

    if all_daily_pnl:
        total_pnl = sum(all_daily_pnl)
        print(f"Total P&L: {total_pnl:.2f}")
        # More stats can be added here, e.g., win/loss ratio, avg pnl per trade
    else:
        print("No trades were executed during the backtest period.")

# --- Main Execution ---

def load_data_from_csv(filepath='nifty_futures.csv'):
    """
    Loads and prepares data from a CSV file, ignoring commented lines.
    """
    print("Loading data from CSV...")
    # Use the 'comment' parameter to ignore lines starting with '#'
    df = pd.read_csv(filepath, comment='#')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    print("Data loaded successfully.")
    return df

if __name__ == "__main__":
    market_data = load_data_from_csv()
    run_backtest(market_data)
    print("\nBacktest finished.")
