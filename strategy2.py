import configparser

class Strategy2:
    def __init__(self, broker):
        self.broker = broker
        self.nifty500_symbols = self._load_nifty500_symbols()
        self.config = self._load_config()
        self.liquidity_threshold = self.config.getfloat('strategy2', 'LIQUIDITY_THRESHOLD', fallback=10000000)

    def _load_nifty500_symbols(self):
        try:
            with open('nifty500.txt', 'r') as f:
                return [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            print("Error: nifty500.txt not found.")
            return []

    def _load_config(self):
        config = configparser.ConfigParser()
        try:
            config.read('config.ini')
        except FileNotFoundError:
            print("Error: config.ini not found.")
        return config

    def select_stocks_for_the_day(self):
        """
        Selects up to 2 stocks to trade for the day based on market sentiment.
        """
        if not self.broker or not self.nifty500_symbols:
            return []

        quotes = self.broker.get_quotes(self.nifty500_symbols)
        if not quotes:
            print("Could not fetch quotes for stock selection.")
            return []

        advances = 0
        declines = 0
        liquid_stocks = []

        for symbol in quotes:
            quote = quotes[symbol]
            traded_value = quote['last_price'] * quote['volume']
            if traded_value >= self.liquidity_threshold:
                liquid_stocks.append(quote)
                if quote['change'] > 0:
                    advances += 1
                elif quote['change'] < 0:
                    declines += 1

        if not liquid_stocks:
            return []

        # Sort stocks by percentage change
        liquid_stocks.sort(key=lambda x: x['change'], reverse=True)

        if advances > declines:
            # Bullish sentiment: select top 2 gainers
            return liquid_stocks[:2]
        else:
            # Bearish sentiment: select top 2 losers
            return liquid_stocks[-2:]

        return []
