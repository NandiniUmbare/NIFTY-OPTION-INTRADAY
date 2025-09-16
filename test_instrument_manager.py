import unittest
from unittest.mock import MagicMock, patch
from instrument_manager import InstrumentManager

class TestInstrumentManager(unittest.TestCase):

    def setUp(self):
        """Set up a mock environment for testing the InstrumentManager."""
        # Mock the Broker (Kite) and DataFeed (Alice Blue) classes
        self.mock_broker = MagicMock()
        self.mock_data_feed = MagicMock()

        # Sample instrument lists
        self.kite_instruments = [
            {'tradingsymbol': 'INFY-EQ', 'instrument_token': '408065', 'exchange': 'NSE'},
            {'tradingsymbol': 'RELIANCE-EQ', 'instrument_token': '738561', 'exchange': 'NSE'},
            {'tradingsymbol': 'TCS-EQ', 'instrument_token': '2953217', 'exchange': 'NSE'}, # Exists only in Kite
        ]

        # For pya3, the instrument object is not a simple dict, so we mock its structure
        mock_alice_infy = MagicMock()
        mock_alice_infy.symbol = 'INFY-EQ'
        mock_alice_reliance = MagicMock()
        mock_alice_reliance.symbol = 'RELIANCE-EQ'
        mock_alice_hdfc = MagicMock()
        mock_alice_hdfc.symbol = 'HDFCBANK-EQ' # Exists only in Alice

        self.alice_instruments = [mock_alice_infy, mock_alice_reliance, mock_alice_hdfc]

        # Configure the mocks' behavior
        self.mock_broker.get_and_cache_instruments.return_value = True
        self.mock_broker.instrument_list = self.kite_instruments

        self.mock_data_feed.get_all_instruments.return_value = True

        # This side effect function simulates the behavior of get_instrument_by_symbol
        def mock_get_inst_by_symbol(exchange, symbol):
            for inst in self.alice_instruments:
                if inst.symbol == symbol:
                    return inst
            return None
        self.mock_data_feed.get_instrument_by_symbol.side_effect = mock_get_inst_by_symbol

    @patch('instrument_manager.Broker')
    @patch('instrument_manager.DataFeed')
    def test_build_instrument_map_success(self, MockDataFeed, MockBroker):
        """Test that the instrument map is built successfully with matching instruments."""
        # Arrange
        MockBroker.return_value = self.mock_broker
        MockDataFeed.return_value = self.mock_data_feed

        manager = InstrumentManager()

        # Act
        success = manager.build_instrument_map(exchange='NSE')

        # Assert
        self.assertTrue(success)
        self.assertEqual(len(manager.instrument_map), 2) # INFY and RELIANCE should match

        # Check INFY mapping
        self.assertIn(('NSE', 'INFY-EQ'), manager.instrument_map)
        self.assertEqual(manager.instrument_map[('NSE', 'INFY-EQ')]['kite'], self.kite_instruments[0])
        self.assertEqual(manager.instrument_map[('NSE', 'INFY-EQ')]['alice'].symbol, 'INFY-EQ')

        # Check RELIANCE mapping
        self.assertIn(('NSE', 'RELIANCE-EQ'), manager.instrument_map)
        self.assertEqual(manager.instrument_map[('NSE', 'RELIANCE-EQ')]['kite'], self.kite_instruments[1])
        self.assertEqual(manager.instrument_map[('NSE', 'RELIANCE-EQ')]['alice'].symbol, 'RELIANCE-EQ')

        # Check that symbols that don't exist in both lists are not in the map
        self.assertNotIn(('NSE', 'TCS-EQ'), manager.instrument_map)
        self.assertNotIn(('NSE', 'HDFCBANK-EQ'), manager.instrument_map)

if __name__ == '__main__':
    unittest.main()
