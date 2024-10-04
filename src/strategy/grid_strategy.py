import bisect
import json
import time

from src.service.exchange import Exchange
from src.strategy.abstract_strategy import AbstractStrategy
from src.util.utils import get_path, read_file


class GridStrategy(AbstractStrategy):
    def __init__(self, exchange: Exchange, dev_config: json = None, grid_levels: list = None):
        super().__init__(exchange)

        print("Initializing Grid Strategy...")
        self.exchange = exchange  # Exchange instance
        self.tracking_symbol = None
        self.min_price = None
        self.max_price = None
        self.num_grids = None
        self.max_position = None
        self.security_deposit = None
        self.fixed_trade_amount = None
        self.previous_price = None  # prev price of tracking symbol on the market

        if dev_config:
            self.set_grid_parameters(dev_config)
        else:
            user_config_path = get_path('../config/grid_config.json')
            user_config = read_file(user_config_path)
            self.set_grid_parameters(user_config)  # Configures parameters by calling the set function
        print("Grid strategy configuration completed!")

        # Grid levels and starting price index setup
        self.curr_eth_position = 0
        self.trade_type = None  # trade side for placing an order
        self.grid_levels = grid_levels if grid_levels else self.generate_grid_levels()
        self.previous_price_idx = bisect.bisect_left(self.grid_levels, self.previous_price)
        print("Grid Strategy initialization completed!")

    def set_grid_parameters(self, config):
        try:
            self.tracking_symbol = config['symbol']
            self.min_price = config['min_price']
            self.max_price = config['max_price']
            self.num_grids = config['num_grids']
            self.max_position = config['max_position']
            self.security_deposit = config['security_deposit']
            self.fixed_trade_amount = config['fixed_trade_amount']
            self.previous_price = config['starting_price']
        except Exception as e:
            print(f"Exception in set_grid_parameters: {e}")

    def generate_grid_levels(self):
        """Generate grid prices using a geometric sequence."""
        ratio = self.max_price / self.min_price
        grid_prices = [self.min_price * (ratio ** (i / (self.num_grids - 1))) for i in range(self.num_grids)]

        # Round each price to 4 decimal places
        grid_prices = [round(price, 4) for price in grid_prices]
        return grid_prices

    def iterate_grids_and_place_limit_order(self, curr_price):
        # TODO: validate security_deposit, curr_eth_position + 0.1 <= max_position before placing orders.
        # TODO: double check if placing order at each grid_prices or the 'end-point'?
        # Price dropped, place 'buy' orders at each grid_level/price until grid_levels lower than curr_price
        if self.trade_type == 'buy':
            for i in range(self.previous_price_idx - 1, -1, -1):
                if self.grid_levels[i] >= curr_price:
                    print(f"CP 1 - buy: prev_price={self.previous_price}, grid_price={self.grid_levels[i]}")
                    print(f" Preparing to {self.trade_type} {self.fixed_trade_amount} ETH at price {curr_price}.")
                    self.exchange.place_order(self.tracking_symbol, 'buy', self.fixed_trade_amount, curr_price, 'limit')
                    self.curr_eth_position += self.fixed_trade_amount
                else:
                    self.previous_price = curr_price  # Update prev_price and index
                    self.previous_price_idx = i + 1
                    break
        else:
            # Price raised, place 'sell' orders at each grid_price until grid_price higher than the current price
            for i in range(self.previous_price_idx + 1, len(self.grid_levels)):
                if self.grid_levels[i] <= curr_price:
                    print(f"CP 2 - sell: prev_price={self.previous_price}, grid_price={self.grid_levels[i]}")
                    print(f" Preparing to {self.trade_type} {self.fixed_trade_amount} ETH at price {curr_price}.")
                    self.exchange.place_order(self.tracking_symbol, 'sell', self.fixed_trade_amount, curr_price,
                                              'limit')
                    self.curr_eth_position -= self.fixed_trade_amount
                else:
                    self.previous_price = curr_price
                    self.previous_price_idx = i - 1
                    break

    def monitor_and_trade(self):
        # Monitor the price and execute trades based on price changes.
        current_price = self.exchange.fetch_ticker(self.tracking_symbol)
        print(f"> Current price: {current_price}")
        if current_price is None:
            print("Failed to retrieve current price.")
            return
        if current_price <= self.min_price or current_price >= self.max_price:  # check within boundaries
            print("Price reached the boundary, stopping Auto-trading...")
            return

        # Trading logic/conditions: determine placing buy or sell order based on previous price change
        if self.previous_price > current_price and self.curr_eth_position < self.max_position:
            self.trade_type = 'buy'
            self.iterate_grids_and_place_limit_order(current_price)
        elif current_price > self.previous_price and self.curr_eth_position > -self.max_position:
            self.trade_type = 'sell'
            self.iterate_grids_and_place_limit_order(current_price)
        # TODO: 下单未成交，需识别后再次确认成交条件再下单

    def execute(self, time_interval):
        print(f"> Executing grid strategy for {self.tracking_symbol}")
        while True:
            try:
                self.monitor_and_trade()
                time.sleep(time_interval)  # Wait for 1 minute
            except Exception as e:
                print(f"Exception in monitor_and_trade: {e}")

    # Realized P&L = (transaction price - average purchase price) x amount held
    # Unrealized P&L = (current price - average purchase price) x amount hold
    def compute_realized_profit_loss(self):
        # Implement logic to calculate realized profit/loss
        realized_profit_loss = 0
        trades = self.exchange.fetch_closed_orders(self.tracking_symbol)

        # Calculate the realized profit/loss from trade history
        for trade in trades:
            # Example calculation, replace with actual logic
            if trade['type'] == 'buy':
                realized_profit_loss -= trade['amount'] * trade['price']
            elif trade['type'] == 'sell':
                realized_profit_loss += trade['amount'] * trade['price']

        return realized_profit_loss

    def calculate_matched_profit(self):
        buy_stack = []  # Stack to keep track of unmatched buy trades
        matched_profits = []

        trades = self.exchange.fetch_closed_orders(self.tracking_symbol)
        # Iterate through trades in chronological order
        for trade in trades:
            # Only process closed trades
            if trade['status'] != 'closed':
                continue

            if trade['type'] == 'buy':
                buy_stack.append(trade)  # Add buy trades to the stack
            elif trade['type'] == 'sell':
                sell_amount = trade['amount']
                sell_price = trade['price']

                # Match sell trades with buy trades in the stack
                while sell_amount > 0 and buy_stack:
                    buy_trade = buy_stack.pop(0)  # Get the earliest buy trade
                    buy_amount = buy_trade['amount']
                    buy_price = buy_trade['price']

                    # Calculate the amount to match
                    matched_amount = min(sell_amount, buy_amount)
                    profit_per_unit = sell_price - buy_price

                    # Calculate the matched profit
                    total_profit = matched_amount * profit_per_unit
                    matched_profits.append({
                        'time': trade['datetime'],
                        'matched profit': total_profit
                    })

                    # Reduce sell and buy amounts accordingly
                    sell_amount -= matched_amount
                    buy_trade['amount'] -= matched_amount

                    # If there is remaining buy amount, put it back in the stack
                    if buy_trade['amount'] > 0:
                        buy_stack.insert(0, buy_trade)

        return matched_profits
