import json
import time
import datetime

import math
import pandas as pd

from src.service.exchange import Exchange
from src.strategy.abstract_strategy import AbstractStrategy
from src.utils.logger import Logger
from src.utils.simple_io import get_path, read_file

logger = Logger().get_logger()


class BinanceGridStrategy(AbstractStrategy):
    def __init__(self, exchange: Exchange, dev_config: json = None, grid_levels: list = None):
        super().__init__(exchange)

        logger.info("Initializing Binance Grid Strategy...")
        self.exchange = exchange  # Exchange instance
        self.tracking_symbol: str = ''
        self.min_price: float = 0
        self.max_price: float = 0
        self.num_grids: int = 0
        self.max_position: float = 0
        self.fixed_trade_amount: float = 0
        self.starting_price: float = 0

        self.security_deposit = None

        if dev_config:
            self.set_grid_parameters(dev_config)
        else:
            user_config_path = get_path('../config/grid_config.json')
            user_config = read_file(user_config_path)
            self.set_grid_parameters(user_config)  # Configures parameters by calling the set function

        logger.info("Binance Grid strategy configuration completed!")

        # Sets up Grid levels and starting price
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
                'timestamp': None,
                'cost': None,
                'trading_fee': None
            } for i in range(0, self.num_grids)  # Creating keys from 1 to num_grids
        }

        self.unmatched_closed_buy_order = []
        self.unmatched_closed_sell_order = []
        self.matched_orders = []
        self.total_matched_profit = 0

        self.last_time_stamp = None
        self.active = False
        self.update_count = 0
        logger.info("Binance Grid Strategy initialization completed!")

    def set_grid_parameters(self, config):
        try:
            self.tracking_symbol = config['symbol'] if config['symbol'] else 'ETH/USDT'
            self.min_price = config['min_price'] if config['min_price'] else 1800
            self.max_price = config['max_price'] if config['max_price'] else 3600
            self.num_grids = config['num_grids'] if config['num_grids'] else 85
            self.max_position = config['max_position'] if config['max_position'] else 10
            self.fixed_trade_amount = config['fixed_trade_amount'] if config['fixed_trade_amount'] else 0.02
            self.starting_price = config['starting_price'] if config['starting_price'] else 2500
            self.security_deposit = config['security_deposit'] if config['security_deposit'] else 0
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
        order = self.exchange.place_order(self.tracking_symbol, 'limit', side, self.fixed_trade_amount,
                                          self.grid_levels[idx])
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
                    'timestamp': buy_order['timestamp']
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
                    'timestamp': sell_order['timestamp']
                }
            else:  # skips 'break_point', no order would be placed with this grid_price.
                continue

        self.previous_price_idx = break_point  # update prev_idx
        logger.info(f"Initialized {self.num_grids} grid-orders with starting price {self.starting_price}.")
        logger.info(f"Number of buy-orders: {self.previous_price_idx}, "
                    f"number of sell-order: {self.num_grids - self.previous_price_idx}")

    def update_grid_orders(self, break_point):
        logger.info("Updating grids-orders...")
        closed_orders = []  # return closed orders for later processing

        # Check existed orders status, replacing with buy-orders if necessary: 'closed', 'sell'.
        for i in range(0, break_point):  # Keys: 0 to break_point
            buy_order = self.orders[i]
            order_status = self.exchange.fetch_order(buy_order['id'], self.tracking_symbol)['status']

            replaced_order = None
            if order_status == 'closed':
                replaced_order = self.place_fixed_amount_limit_order('buy', i)  # replace the buy order
                closed_orders.append(buy_order)
                logger.info(f"Order {buy_order['id']} is closed, replaced with new order: {replaced_order}")

            elif buy_order['side'] == 'sell':
                self.exchange.cancel_order(buy_order['id'], self.tracking_symbol)
                replaced_order = self.place_fixed_amount_limit_order('buy', i)  # replace the buy order
                logger.info(f"Order {buy_order['id']} side: sell, replaced with order {replaced_order}")

            if replaced_order is not None:  # update order info into the orders dictionary
                self.orders[i]['id'] = replaced_order['id']
                self.orders[i]['side'] = replaced_order['side']
                self.orders[i]['price'] = replaced_order['price']
                self.orders[i]['datetime'] = replaced_order['datetime']
                self.orders[i]['timestamp'] = replaced_order['timestamp']

        # Check existed orders status, replacing with sell-orders if necessary: 'closed', 'buy'.
        for i in range(break_point, self.num_grids):  # Keys: break_point + 1 to len(self.grid_levels)
            sell_order = self.orders[i]
            order_status = self.exchange.fetch_order(sell_order['id'], self.tracking_symbol)['status']

            replaced_order = None
            if order_status == 'closed':
                replaced_order = self.place_fixed_amount_limit_order('sell', i + 1)  # replace the sell order
                closed_orders.append(sell_order)
                logger.info(f"Order {sell_order['id']} is closed, replaced with new order: {replaced_order}")

            elif sell_order['side'] == 'buy':
                self.exchange.cancel_order(sell_order['id'], self.tracking_symbol)
                replaced_order = self.place_fixed_amount_limit_order('sell', i + 1)  # replace the sell order
                logger.info(f"Order {sell_order['id']} side: buy, replaced with order {replaced_order}")

            if replaced_order is not None:
                self.orders[i]['id'] = replaced_order['id']
                self.orders[i]['side'] = replaced_order['side']
                self.orders[i]['price'] = replaced_order['price']
                self.orders[i]['datetime'] = replaced_order['datetime']
                self.orders[i]['timestamp'] = replaced_order['timestamp']

        self.previous_price_idx = break_point  # updates grid index of prev_price
        logger.info(f"Updated grid-orders, # buy-orders: {self.previous_price_idx}, "
                    f"# sell-order: {self.num_grids - self.previous_price_idx}")

        return closed_orders

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

    def process_closed_order(self, closed_orders):
        # Check if there are any closed orders
        if len(closed_orders) > 0:
            closed_orders.sort(key=lambda x: x['datetime'])

            # Process each closed order
            for order in closed_orders:
                found_match = self.match_orders_and_compute_profit(order)
                if not found_match:
                    if order['side'] == 'buy':
                        self.unmatched_closed_buy_order.append(order)
                    else:
                        self.unmatched_closed_sell_order.append(order)

            logger.info(f"Processed {len(closed_orders)} closed orders.")

    def monitor_and_trade(self):
        try:
            ticker = self.exchange.fetch_ticker(self.tracking_symbol)
            new_price = ticker['last']
            logger.info(f"Latest price for {self.tracking_symbol}: {new_price}")
        except Exception as e:
            logger.error(f"Failed to fetch ticker for {self.tracking_symbol}: {e}")
            return  # throw the exception for now

        try:
            new_index = self.get_grid_index_with_current_price(new_price)
        except Exception as e:
            raise e

        # TODO: validates and updates eth position, security_deposit, ect, if necessary.
        logger.info(f"Current price: {ticker['last']}, new index: {new_index}, "
                    f"prev index: {self.previous_price_idx}")

        closed_orders = self.update_grid_orders(new_index)  # Update/adjust limit orders
        self.process_closed_order(closed_orders)

        # below code for exporting data to test
        timestamp_ms = ticker['timestamp']
        timestamp_sec = timestamp_ms / 1000  # Convert milliseconds to seconds
        dt_object = datetime.datetime.fromtimestamp(timestamp_sec)
        formatted_date = dt_object.strftime("%Y-%m-%d %H:%M:%S")

        self.update_count += 1  # code for exporting data to test
        description = f"Datetime: {formatted_date}, current price: {ticker['last']}, break point: {new_index}"
        self.export_orders(self.orders, f'active_orders_{self.update_count}.csv', description)

    def execute(self, time_interval=30):
        try:
            # below code for exporting data to test
            ticker = self.exchange.fetch_ticker(self.tracking_symbol)
            timestamp_ms = ticker['timestamp']
            timestamp_sec = timestamp_ms / 1000  # Convert milliseconds to seconds
            dt_object = datetime.datetime.fromtimestamp(timestamp_sec)
            formatted_date = dt_object.strftime("%Y-%m-%d %H:%M:%S")

            logger.info(f"Starting auto-trading with starting price: {self.starting_price}")
            initial_break_point = self.get_grid_index_with_current_price(self.starting_price)
            self.initialize_grid_orders(initial_break_point)

            description = f"Datetime: {formatted_date}, starting price: {self.starting_price}, break point: {initial_break_point})"
            self.export_orders(self.orders, 'init_orders.csv', description)

        except Exception as e:
            logger.error(f"Grid orders initialization failed: {e}")
            logger.info("Terminating the program due to initialization error.")
            self.active = False
            return  # Exit the function, stopping the program

        self.active = True
        try:
            while self.active:
                time.sleep(time_interval)  # Use the passed time interval or default: 60
                self.monitor_and_trade()
        except KeyboardInterrupt:
            logger.info("\nTrading process interrupted by user.")
            self.active = False
        except Exception as e:
            logger.critical(f"\nUnexpected Error during monitoring: {e}")
            self.active = False

    def clean_up(self):
        self.cancel_all_open_orders()  # Cancels all open orders

        closed_orders = self.exchange.fetch_closed_orders(self.tracking_symbol)
        self.export_orders(closed_orders, 'closed_orders.csv', "Closed Orders", False)

        self.export_orders(self.matched_orders, 'matched_orders.csv', "Matched Orders", False)

    def stop(self):
        self.active = False  # Set the flag to stop the loop

        logger.info("Cancels open orders and exports data before terminating program...")
        self.clean_up()
        logger.info("Auto-trading terminated! Exit.")

    def match_orders_and_compute_profit(self, new_closed_order):
        self.unmatched_closed_buy_order.sort(key=lambda x: x['datetime'])
        self.unmatched_closed_sell_order.sort(key=lambda x: x['datetime'])

        if new_closed_order['side'] == 'buy':
            for sell_order in self.unmatched_closed_sell_order:
                if sell_order['price'] > new_closed_order['price']:  # simple matched logic
                    # TODO: TBD tax to calculate real profit
                    # fee_rate = 0.0002
                    # transaction_fee = 'price' * 'amount' * fee_rate = 'cost' * fee_rate
                    # trading_fee = order['fee']['cost']
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

    @staticmethod
    def export_orders(orders, file_name, description="File description", is_dictionary=True):
        if not orders or len(orders) == 0:
            logger.info(f"No orders to export to {file_name}, orders-dictionary is empty.")
            return

        if is_dictionary:
            orders = list(orders.values())

        try:
            file_name = str(file_name)
            logger.info(f"Exporting to {file_name}, orders type: {type(orders)}, orders length: {len(orders)}")

            df = pd.DataFrame(orders)

            # Log the DataFrame columns for debugging
            # logger.info(f"DataFrame columns before filtering: {df.columns.tolist()}")

            required_columns = ['id', 'side', 'price', 'amount', 'type', 'datetime', 'timestamp']
            # existing_columns = df.columns.intersection(required_columns).tolist()

            # if len(existing_columns) < len(required_columns):
            #     logger.warning(f"Missing columns in DataFrame: {set(required_columns) - set(existing_columns)}")

            df = df[required_columns]

            relative_file_path = f'../data/{file_name}'
            file_path = get_path(relative_file_path)

            with open(file_path, 'w') as f:
                f.write(f"# {description}\n")  # Add the description as a comment at the top
                df.to_csv(f, index=True)  # Export the DataFrame below the description

            logger.info(f"{file_name} exported successfully.")
        except Exception as e:
            logger.error(f"Failed to export {file_name}: {e}")
