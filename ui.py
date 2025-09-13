import os
import pandas as pd

def display_terminal(state):
    """
    Clears the console and prints the current state of the terminal.
    """
    # Clear the console screen
    os.system('cls' if os.name == 'nt' else 'clear')

    print("--- Nifty VWAP Strategy Terminal ---")
    print("-" * 34)

    # Display latest market data
    if state.get('latest_tick') is not None:
        tick = state['latest_tick']

        # Check for NaN before formatting to avoid errors
        vwap_str = f"{tick.get('VWAP', 0):.2f}" if pd.notna(tick.get('VWAP')) else "N/A"
        upper_str = f"{tick.get('UpperBand', 0):.2f}" if pd.notna(tick.get('UpperBand')) else "N/A"
        lower_str = f"{tick.get('LowerBand', 0):.2f}" if pd.notna(tick.get('LowerBand')) else "N/A"

        print(f"Timestamp: {tick.name.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Price: {tick['close']:.2f} | VWAP: {vwap_str} | Upper: {upper_str} | Lower: {lower_str}")
    else:
        print("Waiting for data...")

    print("-" * 34)

    # Display open position status
    if state.get('position') and state['position']['status'] == 'OPEN':
        pos = state['position']
        pnl = state.get('live_pnl', 0)
        print("--- Open Position ---")
        print(f"Direction: {pos['direction']} | Entry: {pos['entry_price']:.2f} | P&L: {pnl:.2f}")
    else:
        print("No open position.")

    print("-" * 34)

    # Display event log
    print("--- Event Log ---")
    if not state.get('log'):
        print("No events yet.")
    else:
        for event in state['log'][-5:]: # Display last 5 events
            print(event)

    print("-" * 34)
