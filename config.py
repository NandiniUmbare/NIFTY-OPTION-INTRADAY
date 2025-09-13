from datetime import time

# --- Strategy Parameters ---
STOP_LOSS = -1500  # As a negative value
TAKE_PROFIT = 3000
SPREAD_WIDTH = 300  # 300 points away for the bought option
TRADE_START_TIME = time(9, 30)
ANCHOR_CANDLE_TIME = time(9, 15)
NEAREST_STRIKE_MULTIPLE = 50
LOT_SIZE = 50 # Nifty lot size for P&L calculation
CSV_FILE_PATH = 'nifty_futures.csv'
SIMULATION_SPEED = 0.5 # Seconds between each data tick
