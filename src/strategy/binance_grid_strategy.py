import json
import time
from datetime import datetime

import math

from src.service.exchange import Exchange
from src.strategy.abstract_strategy import AbstractStrategy
from src.utils.logger import Logger
from src.utils.simple_io import get_path, read_file

logger = Logger().get_logger()


def get_current_time():
    current_time = datetime.now()
    date_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
    return date_time


class BinanceGridStrategy(AbstractStrategy):
    def __init__(self, exchange: Exchange, dev_config: json = None, grid_levels: list = None):
        super().__init__(exchange)

        print("Initializing Grid Strategy...")
        self.exchange = exchange  # Exchange instance
        self.tracking_symbol: str = ''
        self.min_price: float = 0
        self.max_price: float = 0
        self.num_grids: int = 0
        self.max_position: float = 0
        self.fixed_trade_amount: float = 0
        self.starting_price: float = 0

        self.security_deposit = None
        self.curr_eth_position = None

        if dev_config:
            self.set_grid_parameters(dev_config)
        else:
            user_config_path = get_path('../config/grid_config.json')
            user_config = read_file(user_config_path)
            self.set_grid_parameters(user_config)  # Configures parameters by calling the set function
        print("Binance Grid strategy configuration completed!")

        # Grid levels and starting price index setup
        # self.trade_type = None  # trade side for placing an order
        self.grid_levels = grid_levels if grid_levels else self.generate_grid_levels()
        self.previous_price_idx = self.get_grid_index_with_current_price(self.starting_price)

        self.open_buy_orders = []
        self.open_sell_orders = []
        self.unmatched_closed_buy_order = []
        self.unmatched_closed_sell_order = []

        self.total_matched_profit = 0
        self.matched_orders = []
        print("Binance Grid Strategy initialization completed!")

    def set_grid_parameters(self, config):
        try:
            self.tracking_symbol = config['symbol']
            self.min_price = config['min_price']
            self.max_price = config['max_price']
            self.num_grids = config['num_grids']
            self.max_position = config['max_position']
            self.fixed_trade_amount = config['fixed_trade_amount']
            self.starting_price = config['starting_price']
            self.security_deposit = config['security_deposit']
        except Exception as e:
            print(f"Exception in set_grid_parameters: {e}")

    def generate_grid_levels(self):
        ratio = (self.max_price / self.min_price) ** (1 / self.num_grids)
        grid_levels = [round(self.min_price * (ratio ** i), 4) for i in range(self.num_grids + 1)]
        grid_levels = [math.floor(price * 100) / 100 for price in grid_levels]

        return grid_levels

    def get_grid_index_with_current_price(self, current_price):
        if current_price <= self.min_price or current_price >= self.max_price:  # check within boundaries
            raise Exception("Starting price reaches Grid boundaries!")

        for i in range(1, len(self.grid_levels)):
            if self.grid_levels[i - 1] < current_price < self.grid_levels[i]:
                return i

    def initialize_grid_orders(self, break_point):
        for i in range(len(self.grid_levels)):
            if i < break_point:  # Place buy order at levels below current price
                buy_order = self.exchange.place_order(self.tracking_symbol, 'buy', self.fixed_trade_amount,
                                                      self.grid_levels[i], 'limit')
                self.open_buy_orders.append(buy_order)
            elif i > break_point:  # Place sell order at levels above current price
                sell_order = self.exchange.place_order(self.tracking_symbol, 'sell', self.fixed_trade_amount,
                                                       self.grid_levels[i], 'limit')
                self.open_sell_orders.append(sell_order)

            else:  # skips 'break_point', no order would be placed with this grid_price.
                continue

    def update_grid_orders(self, break_point):
        # TODO: check orders status, re-place FILLED orders, sorts orders by price to secure indices
        # TODO: handle if order was not placed successfully.
        # Logic to compare and manage orders (keep track of existing orders and only update the necessary ones:
        # cancel old orders, place new ones).
        if break_point > self.previous_price_idx:
            # price raised -> index shifts to right -> more buy, less sell.
            # Cancels sell-orders where order 'price' <= grids[break_point]
            orders_to_remove = []
            for sell_order in self.open_sell_orders:
                if sell_order['price'] <= self.grid_levels[break_point]:
                    self.exchange.cancel_order(sell_order['id'], sell_order['symbol'])
                    orders_to_remove.append(sell_order)

            # Second pass to remove orders
            for order in orders_to_remove:
                self.open_sell_orders.remove(order)

            # Places buy-order with prices from grids[prev_idx] to [break_point] (excluded)
            for i in range(self.previous_price_idx, break_point):
                new_buy_order = self.exchange.place_order(self.tracking_symbol, 'buy', self.fixed_trade_amount,
                                                          self.grid_levels[i], 'limit')
                self.open_buy_orders.append(new_buy_order)

        elif break_point < self.previous_price_idx:
            # Price dropped -> break_point shifts to left -> less buy, more sell.
            # Cancels buy-orders which order 'price' >= grids[break_point]
            # Iterate backward to safely remove items
            for i in range(len(self.open_buy_orders) - 1, -1, -1):
                buy_order = self.open_buy_orders[i]
                if buy_order['price'] >= self.grid_levels[break_point]:
                    self.exchange.cancel_order(buy_order['id'], buy_order['symbol'])
                    del self.open_buy_orders[i]  # Use del for safer removal

            # Adds sell-order with prices from grids[break_point-1] to [prev_idx]
            for i in range(break_point + 1, self.previous_price_idx + 1):
                new_sell_order = self.exchange.place_order(self.tracking_symbol, 'sell', self.fixed_trade_amount,
                                                           self.grid_levels[i], 'limit')
                self.open_sell_orders.append(new_sell_order)
        else:
            logger.info("update_grid_orders(): Price fluctuated within the same grid, no need to update any order.")

    def monitor_and_trade(self):
        ticker = self.exchange.fetch_ticker(self.tracking_symbol)
        new_index = self.get_grid_index_with_current_price(ticker['last'])

        if new_index != self.previous_price_idx:
            self.update_grid_orders(new_index)  # Update/adjust limit orders based on the new current price

            # self.compute_matched_profit()  # calculate matching profit
            self.previous_price_idx = new_index
            # TODO: update eth position, security_deposit, ect, if necessary.

    def execute(self, time_interval):
        try:
            initial_break_point = self.get_grid_index_with_current_price(self.starting_price)

            logger.info(f"Starting auto-trading with starting price: {self.starting_price}")
            self.init_grid_orders(initial_break_point)

        except Exception as e:
            logger.error(f"Grid orders initialization failed: {e}")
            logger.info("Terminating the program due to initialization error.")
            return  # Exit the function, stopping the program

        running = True
        while running:
            try:
                time.sleep(time_interval)  # Use the passed time interval
                self.monitor_and_trade()

            except KeyboardInterrupt:
                running = False
                logger.info("\nTrading process interrupted by user. Exiting...")
            except Exception as e:
                running = False
                logger.error(f"\nError during monitoring: {e}")

            finally:
                # Ensure any necessary cleanup is done here
                logger.info("Cancelling all open orders...")
                if self.open_buy_orders:
                    for buy_order in self.open_buy_orders:
                        self.exchange.cancel_order(buy_order['id'], self.tracking_symbol)

                if self.open_sell_orders:
                    for sell_order in self.open_sell_orders:
                        self.exchange.cancel_order(sell_order['id'], self.tracking_symbol)

                logger.info("Auto-trading terminated! Exit.")

    def execute_with_history_prices(self, curr_price: float, date_time: str):
        pass

    def match_orders_and_compute_profit(self, new_order):
        self.unmatched_closed_buy_order.sort(key=lambda x: x['time_stamp'])
        self.unmatched_closed_sell_order.sort(key=lambda x: x['time_stamp'])

        if new_order['side'] == 'buy':
            for sell_order in self.unmatched_closed_sell_order:
                if sell_order['price'] > new_order['price']:  # simple matched logic
                    # TODO: TBD tax to calculate real profit
                    # tax = 0  # TBD
                    self.total_matched_profit += (sell_order['price'] - new_order['price']) * self.fixed_trade_amount
                    self.matched_orders.append(new_order)
                    self.matched_orders.append(sell_order)

                    self.unmatched_closed_sell_order.remove(sell_order)
                    return True
        else:
            for buy_order in self.unmatched_closed_buy_order:
                if buy_order['price'] < new_order['price']:  # simple matched logic
                    # tax = 0  # TBD
                    self.total_matched_profit += (new_order['price'] - buy_order['price']) * self.fixed_trade_amount
                    self.matched_orders.append(buy_order)
                    self.matched_orders.append(new_order)

                    self.unmatched_closed_buy_order.remove(buy_order)
                    return True

        return False

    """Below functions for TDD purpose"""

    def init_grid_orders(self, break_point):
        for i in range(len(self.grid_levels)):

            if i == break_point:
                continue
            elif i < break_point:  # Place buy order at levels below current price
                self.open_buy_orders.append({
                    'side': 'buy',
                    'amount': self.fixed_trade_amount,
                    'price': self.grid_levels[i],
                    'date': get_current_time()
                })
            elif i > break_point:  # Place sell order at levels above current price
                self.open_sell_orders.append({
                    'side': 'sell',
                    'amount': self.fixed_trade_amount,
                    'price': self.grid_levels[i],
                    'date': get_current_time()
                })

    def adjust_grid_orders(self, new_break_point):
        if new_break_point > self.previous_price_idx:
            # price raised -> index shifts to right -> more buy, less sell.
            for i in range(0, new_break_point - self.previous_price_idx):
                sell_order = self.open_sell_orders[i]
                self.open_sell_orders.remove(sell_order)

            for i in range(self.previous_price_idx, new_break_point):
                self.open_buy_orders.append({'side': 'buy',
                                             'amount': self.fixed_trade_amount,
                                             'price': self.grid_levels[i],
                                             'datetime': get_current_time()})

        elif new_break_point < self.previous_price_idx:
            # price dropped -> index of grid level shifts to left -> less buy, more sell.
            for i in range(self.previous_price_idx - 1, new_break_point - 1, -1):
                if i < len(self.open_buy_orders):
                    buy_order = self.open_buy_orders[i]
                    self.open_buy_orders.remove(buy_order)
                    # print(f"Removed buy order: {buy_order}")
                else:
                    print(f"Index {i} is out of bounds for buy orders.")

            # Place new sell orders
            for i in range(new_break_point - 1, self.previous_price_idx - 1):
                new_sell_order = {
                    'side': 'sell',
                    'amount': self.fixed_trade_amount,
                    'price': self.grid_levels[i],
                    'datetime': get_current_time()
                }
                self.open_sell_orders.append(new_sell_order)
