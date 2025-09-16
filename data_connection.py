import configparser
import logging
from pya3 import *
from datetime import datetime, timedelta

class DataFeed:
    def __init__(self):
        """
        Initializes the DataFeed object, which handles the connection to the Alice Blue API for market data.
        """
        self.alice = None
        self.session_id = None
        self.socket_opened = False
        self._load_credentials()

    def _load_credentials(self):
        """
        Loads Alice Blue credentials from the config.ini file.
        """
        config = configparser.ConfigParser()
        config.read('config.ini')
        try:
            self.user_id = config.get('ALICEBLUE', 'user_id')
            self.api_key = config.get('ALICEBLUE', 'api_key')
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logging.error(f"Credentials for Alice Blue not found in config.ini: {e}")
            self.user_id = None
            self.api_key = None

    def connect(self):
        """
        Connects to the Alice Blue API and establishes a session.
        NOTE: The user must have logged into the Alice Blue web terminal (ant.aliceblueonline.com)
        at least once on the current day for this to work.
        """
        if not self.user_id or not self.api_key:
            logging.error("Cannot connect: Alice Blue credentials are not loaded.")
            return False

        try:
            self.alice = Aliceblue(user_id=self.user_id, api_key=self.api_key)
            session_info = self.alice.get_session_id()

            if session_info.get('stat') == 'Ok' and session_info.get('sessionID'):
                self.session_id = session_info['sessionID']
                logging.info("Successfully connected to Alice Blue and got session ID.")
                return True
            else:
                logging.error(f"Failed to get Alice Blue session ID: {session_info.get('emsg', 'Unknown error')}")
                self.session_id = None
                return False
        except Exception as e:
            logging.error(f"An exception occurred during Alice Blue connection: {e}")
            return False

    def get_historical_data(self, instrument, from_date, to_date, interval, is_index=False):
        """
        Fetches historical data for a given instrument.
        """
        if not self.alice or not self.session_id:
            logging.error("Cannot fetch historical data: Not connected to Alice Blue.")
            return None

        try:
            return self.alice.get_historical(instrument, from_date, to_date, interval, is_index)
        except Exception as e:
            logging.error(f"Failed to fetch historical data for {instrument.symbol}: {e}")
            return None

    def start_websocket(self, on_feed, on_open=None, on_close=None, on_error=None):
        """
        Starts the websocket connection for live data feeds.
        """
        if not self.alice or not self.session_id:
            logging.error("Cannot start websocket: Not connected to Alice Blue.")
            return

        def default_on_open():
            self.socket_opened = True
            logging.info("Alice Blue websocket connected.")
            if on_open:
                on_open()

        def default_on_close():
            self.socket_opened = False
            logging.info("Alice Blue websocket disconnected.")
            if on_close:
                on_close()

        self.alice.start_websocket(
            socket_open_callback=default_on_open,
            socket_close_callback=default_on_close,
            socket_error_callback=on_error or (lambda e: logging.error(f"Websocket error: {e}")),
            subscription_callback=on_feed,
            run_in_background=True
        )

    def subscribe(self, instruments):
        """
        Subscribes to a list of instruments on the websocket.
        """
        if self.alice and self.socket_opened:
            self.alice.subscribe(instruments)
            logging.info(f"Subscribed to {[inst.symbol for inst in instruments]}")

    def get_instrument_by_symbol(self, exchange, symbol):
        """
        Gets an instrument object by its symbol.
        """
        if not self.alice:
            logging.error("Cannot get instrument: Not connected to Alice Blue.")
            return None
        return self.alice.get_instrument_by_symbol(exchange, symbol)

    def get_all_instruments(self, exchange):
        """
        Downloads and loads the master contract for a given exchange.
        """
        if not self.alice:
            logging.error("Cannot get instruments: Not connected to Alice Blue.")
            return False
        try:
            self.alice.get_contract_master(exchange)
            logging.info(f"Successfully loaded master contract for {exchange}.")
            return True
        except Exception as e:
            logging.error(f"Failed to load master contract for {exchange}: {e}")
            return False
