import os
import ccxt

from typing import Literal
from src.utils.simple_io import get_path, read_file
from src.service.abstract_exchange import AbstractExchange


class Exchange(AbstractExchange):

    def __init__(self, user_credentials_file_path: str = None):
        print("Initializing Exchange instance...")
        self.exchange_name = None
        self.market_type = None

        self.market = None
        if user_credentials_file_path:
            self.market = self.validate_user_credentials(user_credentials_file_path)
        else:
            self.market = self.create_future_testnet_instance()

        # Fetch market data
        balance = self.fetch_balance()
        free_usdt = balance['total'].get('USDT', 0)
        eth_position = balance['total'].get('ETH', 0)
        self.free_usdt_balance = free_usdt
        self.real_eth_position = eth_position
        print("Exchange instance initialization completed!")

    def validate_user_credentials(self, user_credentials_file_path):
        # Check for user credentials file
        if os.path.exists(user_credentials_file_path):
            credentials = read_file(user_credentials_file_path)
            api_key = credentials.get('api_key')
            secret = credentials.get('secret')
            if api_key and secret:
                return self.create_instance_with_credentials(credentials)
            else:
                print("Missing User api_key or secret! Falling back to future Testnet configuration.")
        else:
            print(f"User credentials file does not exists at: {user_credentials_file_path}!")

        return None

    def create_future_testnet_instance(self):
        testnet_future_path = get_path('../config/testnet_future.json')
        credentials = read_file(testnet_future_path)

        return self.create_instance_with_credentials(credentials)

    def create_instance_with_credentials(self, credentials):
        self.exchange_name = credentials['exchange_name']
        self.market_type = credentials['market_type']

        exchange_class = getattr(ccxt, credentials['exchange_name'])
        market = exchange_class({
            'api_key': credentials['api_key'],
            'secret': credentials['secret'],
            'enableRateLimit': True,
            'options': {
                'defaultType': credentials['market_type'],  # Specify if you're using futures
            }
        })
        market.set_sandbox_mode(credentials['isTestnet'])  # Enable testnet mode

        return market

    def fetch_balance(self):
        try:
            return self.market.fetch_balance()
        except Exception as e:
            raise Exception(f"Failed to fetch balance on {self.market_type} market: {e}")

    def fetch_specific_balance(self, asset_symbol: str):
        try:
            balance = self.market.fetch_balance()
            if asset_symbol in balance['total']:
                return {
                    'total_balance': balance['total'][asset_symbol],
                    'free_balance': balance['free'][asset_symbol],
                    'locked_balance': balance['used'][asset_symbol]
                }
            else:
                print(f"Asset {asset_symbol} not found in your {self.market_type} account.")
                return None
        except ccxt.ExchangeError as e:
            print(f"Exchange error: {str(e)}")

    def fetch_ticker(self, symbol):
        try:
            ticker = self.market.fetch_ticker(symbol)
            return ticker['last']
        except ccxt.ExchangeError as e:
            print(f"Exchange error: {str(e)}")

    def place_order(self, symbol: str, side: Literal['buy', 'sell'], amount: float, price: float, order_type: str):
        try:
            if order_type == 'limit':
                return self.market.create_limit_order(symbol, side, amount, price)
            elif order_type == 'market':
                return self.market.create_market_order(symbol, side, amount)
            else:
                raise ValueError(f"Unknown order type: {order_type}")
        except Exception as e:
            raise Exception(f"Failed to place order on {self.market_type} market: {e}")

    def cancel_order(self, order_id: str, symbol: str):
        try:
            return self.market.cancel_order(order_id, symbol)
        except Exception as e:
            raise Exception(f"Failed to cancel order {order_id} on {self.market_type} market: {e}")

    def fetch_order(self, order_id: str, symbol: str):
        try:
            return self.market.fetch_order(order_id, symbol)
        except Exception as e:
            raise Exception(f"Failed to fetch order {order_id} for {symbol} on {self.market_type} market: {e}")

    def fetch_open_orders(self, symbol: str):
        try:
            return self.market.fetch_open_orders(symbol)
        except Exception as e:
            raise Exception(f"Failed to fetch open orders for {symbol} on {self.market_type} market: {e}")

    def fetch_closed_orders(self, symbol: str):
        try:
            return self.market.fetch_closed_orders(symbol)
        except Exception as e:
            raise Exception(f"Failed to fetch closed orders for {symbol} on {self.market_type} market: {e}")

    def fetch_recent_ohlcv(self, symbol, timeframe='1h', since=None, limit=100):
        try:
            # Fetch OHLCV data
            ohlcv = self.market.fetch_ohlcv(symbol, timeframe, since, limit)
            return ohlcv
        except Exception as e:
            raise Exception(f"Failed to fetch OHLCV data for {symbol} on {self.market_type} market: {e}")
