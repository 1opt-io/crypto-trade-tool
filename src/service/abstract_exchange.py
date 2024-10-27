from abc import ABC, abstractmethod
from typing import Literal


class AbstractExchange(ABC):

    @abstractmethod
    def fetch_balance(self):
        pass

    @abstractmethod
    def fetch_ticker(self, symbol):
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: Literal['buy', 'sell'], amount: float, price: float, order_type: str):
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str):
        pass

    @abstractmethod
    def fetch_order(self, order_id: str, symbol: str):
        pass

    @abstractmethod
    def fetch_open_orders(self, symbol: str):
        pass

    @abstractmethod
    def fetch_closed_orders(self, symbol: str):
        pass

    @abstractmethod
    def fetch_ohlcv(self, symbol, timeframe='1h', since=None, limit=100):
        pass
