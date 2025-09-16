from kiteconnect import KiteConnect
import configparser
import logging

class Broker:
    def __init__(self):
        """
        Initializes the Broker class, which handles the connection to the Kite API for order placement.
        """
        self.kite = None
        self.api_key = None
        self.api_secret = None
        self.access_token = None
        self.instrument_list = None
        self._load_credentials()
        if self.api_key:
            self.kite = KiteConnect(api_key=self.api_key)

    def _load_credentials(self):
        """
        Loads Kite credentials from the config.ini file.
        """
        config = configparser.ConfigParser()
        config.read('config.ini')
        try:
            self.api_key = config.get('KITE', 'api_key')
            self.api_secret = config.get('KITE', 'api_secret')
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logging.error(f"Credentials for Kite not found in config.ini: {e}")
            self.api_key = None
            self.api_secret = None

    def get_login_url(self):
        """
        Generates the login URL for the user to authenticate with Kite.
        """
        if not self.kite:
            logging.error("Cannot get login URL: Kite client not initialized. Check credentials.")
            return None
        return self.kite.login_url()

    def set_access_token(self, request_token):
        """
        Generates an access token using the request token and the stored API secret.
        """
        if not self.kite or not self.api_secret:
            logging.error("Cannot set access token: Kite client or API secret not available.")
            return False
        try:
            user_data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = user_data["access_token"]
            self.kite.set_access_token(self.access_token)
            logging.info("Kite access token generated successfully.")
            return True
        except Exception as e:
            logging.error(f"Error generating Kite access token: {e}")
            return False

    def get_and_cache_instruments(self, exchange='NSE'):
        """
        Fetches the complete list of instruments for an exchange and caches it.
        """
        if not self.kite or not self.access_token:
            logging.error("Cannot fetch instruments: Kite client not initialized or not logged in.")
            return False
        if self.instrument_list is None:
            try:
                self.instrument_list = self.kite.instruments(exchange)
                logging.info(f"Successfully fetched and cached {len(self.instrument_list)} instruments for {exchange}.")
            except Exception as e:
                logging.error(f"Error fetching instruments from Kite: {e}")
                return False
        return True

    def get_instrument_by_symbol(self, symbol, exchange='NSE'):
        """
        Finds an instrument from the cached list by its trading symbol.
        """
        if self.instrument_list is None:
            if not self.get_and_cache_instruments(exchange):
                return None

        for instrument in self.instrument_list:
            if instrument['tradingsymbol'] == symbol:
                return instrument
        return None

    def place_order(self, symbol, quantity, direction, order_type='MARKET', exchange='NSE', product='MIS'):
        """Places a generic order."""
        if not self.kite or not self.access_token:
            logging.error("Cannot place order: Not connected to Kite.")
            return None
        try:
            order_id = self.kite.place_order(
                tradingsymbol=symbol,
                exchange=exchange,
                transaction_type=direction,
                quantity=quantity,
                order_type=order_type,
                product=product,
                variety=self.kite.VARIETY_REGULAR
            )
            logging.info(f"Placed order for {symbol}: {direction} {quantity} @ {order_type}. Order ID: {order_id}")
            return order_id
        except Exception as e:
            logging.error(f"Error placing order for {symbol}: {e}")
            return None
