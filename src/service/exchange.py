import os
import time

import ccxt

from src.utils.logger import Logger
from src.utils.simple_io import get_path, read_file
from src.service.abstract_exchange import AbstractExchange

logger = Logger().get_logger()


class Exchange(AbstractExchange):

    def __init__(self, user_credentials_file_path: str = None):
        logger.info("Initializing Exchange instance...")
        self.exchange_name = None
        self.market_type = None
        self.market = None

        if user_credentials_file_path:
            self.market = self.validate_user_credentials(user_credentials_file_path)
        else:
            self.market = self.create_future_testnet_instance()

        # Fetch market data
        # balance = self.fetch_balance()
        # free_usdt = balance['total'].get('USDT', 0)
        # eth_position = balance['total'].get('ETH', 0)
        # self.free_usdt_balance = free_usdt
        # self.real_eth_position = eth_position

        logger.info("Exchange instance initialization completed!")

    def validate_user_credentials(self, user_credentials_file_path):
        # Check for user credentials file
        if os.path.exists(user_credentials_file_path):
            credentials = read_file(user_credentials_file_path)
            api_key = credentials.get('api_key')
            secret = credentials.get('secret')

            if api_key and secret:
                return self.create_instance_with_credentials(credentials)
            else:
                logger.warning("Missing User api_key or secret! Falling back to future Testnet configuration.")
        else:
            logger.error(f"User credentials file does not exists at: {user_credentials_file_path}!")

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

    def place_order(self, symbol, order_type, side, amount, price=None):
        if order_type == 'limit':
            return self.safe_api_call(self.market.create_limit_order, symbol, side, amount, price)
        elif order_type == 'market':
            return self.safe_api_call(self.market.create_market_order, symbol, side, amount)
        else:
            raise ValueError(f"Unknown order type: {order_type}")

    def fetch_balance(self):
        return self.safe_api_call(self.market.fetch_balance)

    def fetch_ticker(self, symbol):
        return self.safe_api_call(self.market.fetch_ticker, symbol)

    def fetch_order(self, order_id: str, symbol: str):
        return self.safe_api_call(self.market.fetch_order, order_id, symbol)

    def fetch_open_orders(self, symbol: str):
        return self.safe_api_call(self.market.fetch_open_orders, symbol)

    def fetch_closed_orders(self, symbol: str):
        self.safe_api_call(self.market.fetch_closed_orders, symbol)

    def cancel_order(self, order_id: str, symbol: str):
        return self.safe_api_call(self.market.cancel_order, order_id, symbol)

    def fetch_ohlcv(self, symbol, timeframe='1h', since=None, limit=10):
        return self.safe_api_call(self.market.fetch_ohlcv, symbol, timeframe, since, limit)

    def fetch_specific_asset_balance(self, asset_symbol: str):
        balance = self.safe_api_call(self.market.fetch_balance)

        if asset_symbol in balance['total']:
            return {
                'total_balance': balance['total'][asset_symbol],
                'free_balance': balance['free'][asset_symbol],
                'locked_balance': balance['used'][asset_symbol]
            }
        else:  # If the asset doesn't exist, return zero values for the balances
            return {
                'total_balance': 0,
                'free_balance': 0,
                'locked_balance': 0
            }

    @staticmethod
    def safe_api_call(api_function, *args, max_retries=3, backoff_factor=1, **kwargs):
        """
        Helper method to safely make API calls with exception handling and retry logic.
        Retries on both ccxt.ExchangeError and ccxt.NetworkError.
        """
        attempts = 0

        while attempts < max_retries:
            try:
                return api_function(*args, **kwargs)

            except ccxt.AuthenticationError as e:
                logger.error(f"Authentication error: {e}")
                raise Exception("Authentication error. Please check your API keys.")

            except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                logger.error(f"Error on attempt {attempts + 1}: {e}")  # Log the error

                attempts += 1  # Increment the attempts counter
                # Retry logic:
                if attempts < max_retries:
                    delay = backoff_factor * (2 ** (attempts - 1))  # Exponential backoff
                    logger.info(f"Retry calling {api_function} in {delay} seconds...")
                    time.sleep(delay)  # Wait before retrying
                else:
                    if isinstance(e, ccxt.NetworkError):
                        logger.error(f"{api_function} Max retries reached due to ccxt.NetworkError: {e}")
                        return  # TODO: TBD, throw exception for now
                        # raise Exception("Max retries reached due to network error.")
                    elif isinstance(e, ccxt.ExchangeError):
                        logger.error(f"{api_function} Max retries reached due to ccxt.ExchangeError: {e}")
                        return  # TODO: TBD, throw exception for now
                        # raise Exception(f"Max retries reached due to exchange error: {str(e)}")
                    else:
                        logger.error(f"{api_function} Max retries reached for an unexpected error: {str(e)}")
                        return  # TODO: TBD, throw exception for now
                        # raise Exception(f"Max retries reached for an unexpected error: {str(e)}")

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise Exception(f"An unexpected error occurred: {str(e)}")
