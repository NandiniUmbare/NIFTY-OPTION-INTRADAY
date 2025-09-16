import logging
from broker_connection import Broker
from data_connection import DataFeed

class InstrumentManager:
    def __init__(self):
        """
        Manages instrument lists and mapping between the execution broker (Kite)
        and the data source (Alice Blue).
        """
        self.broker = Broker()
        self.data_feed = DataFeed()
        self.instrument_map = {}
        self.is_initialized = False

    def build_instrument_map(self, exchange='NSE'):
        """
        Fetches instrument lists from both providers and builds a map.
        The map uses (exchange, tradingsymbol) as the key.
        """
        logging.info(f"Building instrument map for {exchange}...")

        # Fetch instruments from Kite (Execution Broker)
        if not self.broker.get_and_cache_instruments(exchange):
            logging.error("Could not fetch instruments from Kite.")
            return False

        # Fetch instruments from Alice Blue (Data Source)
        if not self.data_feed.get_all_instruments(exchange):
            logging.error("Could not fetch instruments from Alice Blue.")
            return False

        # We use Kite's instrument list as the master list of tradable symbols.
        # For each Kite instrument, we find the corresponding Alice Blue instrument.
        kite_instruments = self.broker.instrument_list

        for k_inst in kite_instruments:
            symbol = k_inst.get('tradingsymbol')
            if not symbol or not k_inst.get('instrument_token'):
                continue

            # Find the corresponding instrument in Alice Blue's list
            a_inst = self.data_feed.get_instrument_by_symbol(exchange, symbol)

            if a_inst:
                map_key = (exchange, symbol)
                self.instrument_map[map_key] = {
                    'kite': k_inst,
                    'alice': a_inst
                }

        logging.info(f"Successfully built instrument map with {len(self.instrument_map)} entries.")
        self.is_initialized = True
        return True

    def get_mapped_instrument(self, symbol, exchange='NSE'):
        """
        Retrieves a mapped instrument object containing both Kite and Alice Blue instrument details.
        """
        if not self.is_initialized:
            logging.warning("Instrument map is not initialized. Call build_instrument_map() first.")
            return None

        map_key = (exchange, symbol)
        return self.instrument_map.get(map_key)
