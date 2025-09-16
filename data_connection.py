import configparser
import logging
from pya3 import *
from datetime import datetime, timedelta
import hashlib
import requests

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
            self.user_id_config = config.get('ALICEBLUE', 'user_id').strip()
            self.api_key = config.get('ALICEBLUE', 'api_key').strip()
            self.api_secret = config.get('ALICEBLUE', 'api_secret').strip()
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logging.error(f"Credentials for Alice Blue not found in config.ini: {e}")
            self.user_id_config = None
            self.api_key = None
            self.api_secret = None

    def get_login_url(self):
        """
        Generates the login URL for the user to authenticate with Alice Blue.
        """
        if not self.api_key:
            return None
        # The appcode parameter should be the user's client ID, not the API key.
        # This seems counter-intuitive but matches some third-party library flows.
        # Let's try with api_key first as per the direct doc link.
        return f"https://ant.aliceblueonline.com/?appcode={self.api_key}"

    def generate_session(self, auth_code, user_id_from_callback):
        """
        Generates a user session by exchanging the auth_code for a session ID.
        This implements the SHA-256 checksum flow.
        """
        if not all([self.api_key, self.api_secret]):
            logging.error("Cannot generate session: Alice Blue API key or secret not loaded.")
            return False

        # 1. Create the checksum
        combined_string = user_id_from_callback + auth_code + self.api_secret
        checksum = hashlib.sha256(combined_string.encode()).hexdigest()

        # 2. Make the POST request to get the session
        url = "https://ant.aliceblueonline.com/open-api/od-rest/v1/vendor/getUserDetails"
        payload = {"checkSum": checksum}

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("stat") == "Ok" and data.get("userSession"):
                self.session_id = data["userSession"]
                # Now that we have a session, we can initialize the pya3 object
                # We use the user_id from the callback, as that's the authenticated one.
                self.alice = Aliceblue(user_id=user_id_from_callback, api_key=self.api_key, session_id=self.session_id)
                logging.info("Successfully generated Alice Blue session.")
                return True
            else:
                logging.error(f"Failed to generate Alice Blue session: {data.get('emsg', 'Unknown error')}")
                return False
        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP error while generating Alice Blue session: {e}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred during Alice Blue session generation: {e}")
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
