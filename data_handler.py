import pandas as pd
import config
import time

def load_data_from_csv(filepath=config.CSV_FILE_PATH):
    """
    Loads and prepares data from a CSV file, ignoring commented lines.
    """
    # This function is now just a utility for the main script to call.
    df = pd.read_csv(filepath, comment='#')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df

def replay_data(df):
    """
    A generator function that replays a dataframe row by row to simulate a live data feed.
    """
    print("Starting data replay...")
    for timestamp, row in df.iterrows():
        yield row
        time.sleep(config.SIMULATION_SPEED)
    print("Data replay finished.")
