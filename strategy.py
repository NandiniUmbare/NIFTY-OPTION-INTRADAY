import pandas as pd
import numpy as np
import config

class StrategyProcessor:
    """
    Manages the state and logic of the trading strategy on a tick-by-tick basis.
    It is completely decoupled from the broker implementation.
    """
    def __init__(self, broker):
        self.broker = broker
        self.position = None
        self.daily_buffer = pd.DataFrame()
        self.current_day = None
        self.log = []

    def process_tick(self, tick):
        """
        Processes a single row of data (a "tick") and updates the strategy state.
        """
        tick_time = tick.name

        if tick_time.date() != self.current_day:
            self.log.append(f"--- New Trading Day: {tick_time.date()} ---")
            self.current_day = tick_time.date()
            self.daily_buffer = pd.DataFrame()
            if self.position and self.position['status'] == 'OPEN':
                self.log.append("Warning: Position carried overnight, force closing.")
                self.broker.close_spread_order(self.position)
                self.position = None

        self.daily_buffer = pd.concat([self.daily_buffer, tick.to_frame().T])
        self.daily_buffer = calculate_vwap_and_bands(self.daily_buffer)

        self.daily_buffer['status'] = np.where(self.daily_buffer['close'] > self.daily_buffer['UpperBand'], 'Above',
                                             np.where(self.daily_buffer['close'] < self.daily_buffer['LowerBand'], 'Below', 'Inside'))
        self.daily_buffer['prev_status'] = self.daily_buffer['status'].shift(1)

        latest_state = self.daily_buffer.iloc[-1]
        live_pnl = 0

        if tick_time.time() >= config.TRADE_START_TIME:
            if self.position and self.position['status'] == 'OPEN':
                live_pnl = calculate_pnl(self.position, latest_state['close'])
                if live_pnl <= config.STOP_LOSS or live_pnl >= config.TAKE_PROFIT:
                    reason = "Take-Profit" if live_pnl >= config.TAKE_PROFIT else "Stop-Loss"
                    self.log.append(f"EXIT: Closing position due to {reason}.")
                    self.broker.close_spread_order(self.position)
                    self.position = None

            elif self.position is None:
                prev_status, current_status = latest_state['prev_status'], latest_state['status']
                if pd.notna(prev_status):
                    strike = round(latest_state['close'] / config.NEAREST_STRIKE_MULTIPLE) * config.NEAREST_STRIKE_MULTIPLE

                    if prev_status != 'Above' and current_status == 'Above':
                        self.log.append(f"ENTRY: Bullish signal detected at {tick_time.time()}.")
                        if self.broker.place_spread_order(strike, 'PE'):
                            self.position = self.create_position_snapshot(strike, 'PE', latest_state['close'])

                    elif prev_status == 'Above' and current_status == 'Inside':
                        self.log.append(f"ENTRY: Bearish signal detected at {tick_time.time()}.")
                        if self.broker.place_spread_order(strike, 'CE'):
                             self.position = self.create_position_snapshot(strike, 'CE', latest_state['close'])

        return {
            'latest_tick': latest_state, 'position': self.position,
            'live_pnl': live_pnl, 'log': self.log
        }

    def create_position_snapshot(self, base_strike, direction, entry_price):
        """ Creates a dictionary representing the state of an open position. """
        return {
            'order_id': f"sim_{pd.Timestamp.now().timestamp()}", # In real trading, use the ID from the broker
            'direction': direction,
            'entry_price': entry_price,
            'initial_credit': 50, # This should ideally come from the broker order details
            'status': 'OPEN'
        }

# --- P&L Simulation ---
def calculate_pnl(trade, current_price):
    price_change = current_price - trade['entry_price']
    if trade['direction'] == 'PE':
        pnl_points = -price_change * 0.2
    elif trade['direction'] == 'CE':
        pnl_points = price_change * 0.2
    total_pnl = (trade['initial_credit'] + pnl_points) * config.LOT_SIZE
    return total_pnl

def calculate_vwap_and_bands(df):
    anchor_start_time = df.index[0].normalize() + pd.Timedelta(hours=config.ANCHOR_CANDLE_TIME.hour, minutes=config.ANCHOR_CANDLE_TIME.minute)
    anchor_df = df[df.index >= anchor_start_time].copy()
    if anchor_df.empty:
        df['VWAP'], df['UpperBand'], df['LowerBand'] = np.nan, np.nan, np.nan
        return df
    tp = (anchor_df['high'] + anchor_df['low'] + anchor_df['close']) / 3
    tp_vol = tp * anchor_df['volume']
    anchor_df['VWAP'] = tp_vol.cumsum() / anchor_df['volume'].cumsum()
    anchor_df['sq_diff'] = ((anchor_df['close'] - anchor_df['VWAP']) ** 2)
    anchor_df['mean_sq_diff'] = anchor_df['sq_diff'].expanding().mean()
    anchor_df['StdDev'] = np.sqrt(anchor_df['mean_sq_diff'])
    anchor_df['UpperBand'] = anchor_df['VWAP'] + anchor_df['StdDev']
    anchor_df['LowerBand'] = anchor_df['VWAP'] - anchor_df['StdDev']
    df.loc[:, 'VWAP'] = anchor_df['VWAP']
    df.loc[:, 'UpperBand'] = anchor_df['UpperBand']
    df.loc[:, 'LowerBand'] = anchor_df['LowerBand']
    return df
