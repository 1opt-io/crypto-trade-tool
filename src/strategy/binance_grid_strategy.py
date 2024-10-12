import json
import time
from datetime import datetime

import math
import pandas as pd

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

        # Initialize the dictionary of dictionaries with a fixed size of num_grids
        self.orders = {
            i: {
                'id': None,        # Placeholder for order ID
                'side': None,      # Placeholder for order side('buy' or 'sell')
                'amount': None,    # Placeholder for amount
                'price': None,     # Placeholder for price
                'type': None,      # Placeholder for order type(e.g. 'market', 'limit', etc)
                'datetime': None,  # Placeholder for datetime
                "timestamp": None,
                'status': None
            } for i in range(0, self.num_grids)  # Creating keys from 1 to num_grids
        }

        self.unmatched_closed_buy_order = []
        self.unmatched_closed_sell_order = []
        self.last_time_stamp = None
        self.total_matched_profit = 0
        self.matched_orders = []
        self.active = False
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
            if current_price <= self.grid_levels[i]:
                return i

    def place_fixed_amount_limit_order(self, side, idx):
        order = self.exchange.place_order(self.tracking_symbol, side, self.fixed_trade_amount,
                                          self.grid_levels[idx], 'limit')
        return order

    def initialize_grid_orders(self, break_point):
        for i in range(len(self.grid_levels)):
            if i < break_point:  # Place buy order at grid_levels[i] below break_point
                buy_order = self.place_fixed_amount_limit_order('buy', i)
                self.orders[i] = {  # Use i as the key for the order, 0-based
                    'id': buy_order['id'],  # Store the order details
                    'side': buy_order['side'],
                    'price': buy_order['price'],
                    'amount': buy_order['amount'],
                    'type': buy_order['type'],
                    'datetime': buy_order['datetime'],
                    'status': buy_order['status']
                }

                if self.last_time_stamp is None:
                    self.last_time_stamp = buy_order['timestamp']

            elif i > break_point:  # Place sell order at grid_levels[i] above break_point
                sell_order = self.place_fixed_amount_limit_order('sell', i)

                self.orders[i - 1] = {  # Use i as the key for the order
                    'id': sell_order['id'],  # Store the order details
                    'side': sell_order['side'],
                    'price': sell_order['price'],
                    'amount': sell_order['amount'],
                    'type': sell_order['type'],
                    'datetime': sell_order['datetime'],
                    'status': sell_order['status']
                }
            else:  # skips 'break_point', no order would be placed with this grid_price.
                continue

        self.previous_price_idx = break_point  # update prev_idx
        logger.info(f"Initialized {self.num_grids} grid-orders with starting price {self.starting_price}.")
        logger.info(f"Number of buy-orders: {self.previous_price_idx}, "
                    f"number of sell-order: {self.num_grids - self.previous_price_idx}")

    def update_grid_orders(self, break_point):
        # Check and update buy orders
        for i in range(0, break_point):  # Keys: 0 to break_point
            buy_order = self.orders[i]
            # order_id = buy_order.get('id')

            order_status = self.exchange.fetch_order(buy_order['id'], self.tracking_symbol)['status']

            replaced_order = None
            if order_status == 'closed':
                replaced_order = self.place_fixed_amount_limit_order('buy', i)  # replace the buy order
            elif buy_order['side'] == 'sell':
                self.exchange.cancel_order(buy_order['id'], self.tracking_symbol)
                replaced_order = self.place_fixed_amount_limit_order('buy', i)  # replace the buy order

            if replaced_order is not None:  # update order info in the dictionary
                self.orders[i]['id'] = replaced_order['id']
                self.orders[i]['side'] = replaced_order['side']
                self.orders[i]['price'] = replaced_order['price']
                self.orders[i]['datetime'] = replaced_order['datetime']

        # Check and update sell orders
        for i in range(break_point, self.num_grids):  # Keys: break_point + 1 to len(self.grid_levels)
            sell_order = self.orders[i]
            order_status = self.exchange.fetch_order(sell_order['id'], self.tracking_symbol)['status']

            replaced_order = None
            if order_status == 'closed':
                replaced_order = self.place_fixed_amount_limit_order('sell', i + 1)  # replace the sell order
            elif sell_order['side'] == 'buy':
                self.exchange.cancel_order(sell_order['id'], self.tracking_symbol)
                replaced_order = self.place_fixed_amount_limit_order('sell', i + 1)  # replace the sell order

            if replaced_order is not None:
                self.orders[i]['id'] = replaced_order['id']
                self.orders[i]['side'] = replaced_order['side']
                self.orders[i]['price'] = replaced_order['price']
                self.orders[i]['datetime'] = replaced_order['datetime']

        self.previous_price_idx = break_point  # updates grid index of prev_price
        logger.info(f"Updated grid-orders, # buy-orders: {self.previous_price_idx}, "
                    f"# sell-order: {self.num_grids - self.previous_price_idx}")

    def cancel_all_open_orders(self):
        open_orders = self.exchange.fetch_open_orders(self.tracking_symbol)
        if open_orders:
            count = 0
            for order in open_orders:
                order_id = order['id']
                try:
                    # Cancel the order using its ID
                    self.exchange.cancel_order(order_id, self.tracking_symbol)
                    count += 1
                    logger.info(f"Cancelled order: {order_id}")

                except Exception as e:
                    logger.error(f"Failed to cancel order {order_id}: {e}")

            logger.info(f"Totally cancelled {count} orders.")

        else:
            logger.info(f"No open orders for {self.tracking_symbol}")

    def export_closed_orders(self):
        try:
            closed_orders = self.exchange.fetch_closed_orders(self.tracking_symbol)

            if closed_orders:
                # Convert closed orders to a DataFrame for easier manipulation
                df = pd.DataFrame(closed_orders)

                # Optionally, you can filter specific columns if needed
                df = df[['id', 'symbol', 'side', 'price', 'amount', 'cost', 'status', 'datetime', 'timestamp']]

                df.to_csv('closed_orders.csv', index=False)  # Export to a CSV file
                logger.info("Closed orders exported successfully to closed_orders.csv")
            else:
                logger.info(f"No closed orders for {self.tracking_symbol}")

        except Exception as e:
            logger.error(f"Failed to export closed orders: {e}")

    def export_matched_orders(self):
        try:
            if not self.matched_orders or len(self.matched_orders) == 0:
                logger.info(f"matched_orders is empty.")
            else:
                df = pd.DataFrame(self.matched_orders)

                # Optionally, you can filter specific columns if needed
                df = df[['id', 'symbol', 'side', 'price', 'amount', 'cost', 'status', 'datetime', 'timestamp']]

                df.to_csv('matched_orders.csv', index=False)  # Export to a CSV file
                logger.info("matched_orders exported successfully to matched_orders.csv")
        except Exception as e:
            logger.error(f"Failed to export matched_orders: {e}")

    def process_closed_order_since_last_stamp(self):
        try:
            # Fetch closed orders since the last timestamp
            closed_orders = self.exchange.market.fetch_closed_orders(self.tracking_symbol, self.last_time_stamp)

            # Check if there are any closed orders
            if not closed_orders:
                logger.info(f"No closed orders found since {self.last_time_stamp}.")
                return

            # Sort closed orders by datetime
            closed_orders.sort(key=lambda x: x['datetime'])

            # Process each closed order
            for order in closed_orders:
                found_match = self.match_orders_and_compute_profit(order)
                if not found_match:
                    if order['side'] == 'buy':
                        self.unmatched_closed_buy_order.append(order)
                    else:
                        self.unmatched_closed_sell_order.append(order)

            logger.info(f"Processed {len(closed_orders)} closed orders since last timestamp.")

            latest_timestamp = closed_orders[-1]['timestamp']  # or 'datetime' depending on your needs
            self.last_time_stamp = latest_timestamp
            logger.info(f"Updated last timestamp to: {latest_timestamp}")

        except Exception as e:
            logger.error(f"Error fetching closed orders: {e}")

    def monitor_and_trade(self):
        try:
            ticker = self.exchange.fetch_ticker(self.tracking_symbol)
            new_price = ticker['last']
            logger.info(f"Latest price for {self.tracking_symbol}: {new_price}")
        except Exception as e:
            logger.error(f"Failed to fetch ticker for {self.tracking_symbol}: {e}")
            return

        new_index = self.get_grid_index_with_current_price(new_price)

        if new_index == self.previous_price_idx:
            logger.info("update_grid_orders(): Price fluctuated within the same grid, no need to update any order.")
        else:
            # TODO: validates and updates eth position, security_deposit, ect, if necessary.
            logger.info(f"Current price: {ticker['last']}, new index: {new_index}, "
                        f"prev index: {self.previous_price_idx}")
            self.update_grid_orders(new_index)  # Update/adjust limit orders
            self.process_closed_order_since_last_stamp()

    def execute(self, time_interval=60):
        try:
            logger.info(f"Starting auto-trading with starting price: {self.starting_price}")
            initial_break_point = self.get_grid_index_with_current_price(self.starting_price)
            self.initialize_grid_orders(initial_break_point)

        except Exception as e:
            logger.error(f"Grid orders initialization failed: {e}")
            logger.info("Terminating the program due to initialization error.")
            return  # Exit the function, stopping the program

        self.active = True
        try:
            while self.active:
                try:
                    time.sleep(time_interval)  # Use the passed time interval or default: 60
                    self.monitor_and_trade()
                except KeyboardInterrupt:
                    running = False
                    logger.info("\nTrading process interrupted by user. Exiting...")
                except Exception as e:
                    running = False
                    logger.error(f"\nError during monitoring: {e}")

        except Exception as e:
            logger.critical(f"Critical error in execute(): {e}")
        finally:
            logger.info("Cancels open orders and exports data before terminating program...")
            self.cancel_all_open_orders()  # Cancels all open orders
            self.export_closed_orders()    # export all closed orders
            self.export_matched_orders()   # export matched orders
            logger.info("Auto-trading terminated! Exit.")

    def stop(self):
        self.active = False  # Set the flag to stop the loop

    def match_orders_and_compute_profit(self, new_closed_order):
        self.unmatched_closed_buy_order.sort(key=lambda x: x['datetime'])
        self.unmatched_closed_sell_order.sort(key=lambda x: x['datetime'])

        if new_closed_order['side'] == 'buy':
            for sell_order in self.unmatched_closed_sell_order:
                if sell_order['price'] > new_closed_order['price']:  # simple matched logic
                    # TODO: TBD tax to calculate real profit
                    # tax = 0  # TBD
                    self.total_matched_profit += (sell_order['price'] - new_closed_order['price']) * self.fixed_trade_amount
                    self.matched_orders.append(new_closed_order)
                    self.matched_orders.append(sell_order)

                    self.unmatched_closed_sell_order.remove(sell_order)
                    return True
        else:
            for buy_order in self.unmatched_closed_buy_order:
                if buy_order['price'] < new_closed_order['price']:  # simple matched logic
                    # tax = 0  # TBD
                    self.total_matched_profit += (new_closed_order['price'] - buy_order['price']) * self.fixed_trade_amount
                    self.matched_orders.append(buy_order)
                    self.matched_orders.append(new_closed_order)

                    self.unmatched_closed_buy_order.remove(buy_order)
                    return True

        return False
