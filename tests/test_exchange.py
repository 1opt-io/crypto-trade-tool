import unittest
from unittest.mock import MagicMock

from src.service.exchange import Exchange


class TestExchange(unittest.TestCase):

    def setUp(self):
        # Set up test configuration
        self.future_testnet_exchange = Exchange()

    def test_create_exchange_instance_with_none_parameter(self):
        exchange = Exchange(None)
        self.assertEqual(self.future_testnet_exchange.exchange_name, exchange.exchange_name)
        self.assertEqual(self.future_testnet_exchange.market_type, exchange.market_type)
        self.assertEqual(self.future_testnet_exchange.real_eth_position, exchange.real_eth_position)

    def test_create_future_testnet_instance(self):
        self.assertEqual(self.future_testnet_exchange.exchange_name, 'binance')
        self.assertEqual(self.future_testnet_exchange.market_type, 'future')

    def test_fetch_balance_with_mock(self):
        self.future_testnet_exchange.fetch_balance = MagicMock(return_value={'total': {'ETH': 10}})
        balance = self.future_testnet_exchange.fetch_balance('future')
        self.assertEqual(balance['total']['ETH'], 10)

    def test_fetch_balance(self):
        balance = self.future_testnet_exchange.fetch_balance()
        print(f"Really balance: {balance['total']['ETH'], 10}")
        self.assertNotEqual(balance['total']['ETH'], 10)

    def test_fetch_ticker(self):
        self.future_testnet_exchange.fetch_ticker = MagicMock(return_value={'last': 2000})
        ticker = self.future_testnet_exchange.fetch_ticker('ETH/USDT')
        self.assertEqual(ticker['last'], 2000)

    def test_place_order(self):
        self.future_testnet_exchange.place_order = MagicMock(return_value={'order_id': '1234'})
        order = self.future_testnet_exchange.place_order('ETH/USDT', 'buy', 1, 2000, 'limit')
        self.assertEqual(order['order_id'], '1234')

    def test_cancel_order(self):
        self.future_testnet_exchange.cancel_order = MagicMock(return_value={'status': 'canceled'})
        response = self.future_testnet_exchange.cancel_order('1234', 'ETH/USDT')
        self.assertEqual(response['status'], 'canceled')

    def test_fetch_order(self):
        self.future_testnet_exchange.fetch_order = MagicMock(return_value={'id': '1234'})
        order = self.future_testnet_exchange.fetch_order('1234', 'ETH/USDT')
        self.assertEqual(order['id'], '1234')

    def test_fetch_open_orders(self):
        self.future_testnet_exchange.fetch_open_orders = MagicMock(return_value=[{'id': '1234'}])
        orders = self.future_testnet_exchange.fetch_open_orders('ETH/USDT')
        self.assertEqual(orders[0]['id'], '1234')

    def test_fetch_closed_orders(self):
        self.future_testnet_exchange.fetch_closed_orders = MagicMock(return_value=[{'id': '1234'}])
        orders = self.future_testnet_exchange.fetch_closed_orders('ETH/USDT')
        self.assertEqual(orders[0]['id'], '1234')


if __name__ == '__main__':
    unittest.main()
