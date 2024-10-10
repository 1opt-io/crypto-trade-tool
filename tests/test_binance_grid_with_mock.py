import unittest
from unittest.mock import MagicMock

from src.strategy.binance_grid_strategy import BinanceGridStrategy


class TestBinanceGridStrategyWithMock(unittest.TestCase):

    def setUp(self):
        # Create a mock exchange instance
        mock_exchange = MagicMock()

        # Initialize BinanceGridStrategy with mock exchange
        self.grid_strategy = BinanceGridStrategy(mock_exchange)

        # Set up the side effect for place_order with dynamic prices based on grid levels
        self.place_order_call_count = 0  # To track the number of calls
        self.grid_strategy.exchange.place_order.side_effect = self.place_order_side_effect

    # Use side_effect to generate dynamic prices based on the grid levels
    def place_order_side_effect(self, symbol, side, amount, price, order_type):
        self.place_order_call_count += 1
        return {
            'id': f'test_order_{self.place_order_call_count}',
            'side': side,
            'amount': amount,
            'price': price,
            'symbol': symbol,
            'order_type': order_type,
            'status': 'open',
        }

    def test_initialize_grid_orders_simple(self):
        # Set some necessary attributes
        self.grid_strategy.tracking_symbol = 'ETH/USDT'
        self.grid_strategy.fixed_trade_amount = 0.1
        self.grid_strategy.grid_levels = [1800, 2000, 2200, 2400, 2600, 2800]

        break_point = 2  # Suppose the price is between grid_levels[2] and grid_levels[3]

        # Call the function being tested
        self.grid_strategy.initialize_grid_orders(break_point)

        # Assertions to check if place_order is called correctly
        # For buy orders (below break_point)
        self.grid_strategy.exchange.place_order.assert_any_call('ETH/USDT', 'buy', 0.1, 1800, 'limit')
        self.grid_strategy.exchange.place_order.assert_any_call('ETH/USDT', 'buy', 0.1, 2000, 'limit')

        # For sell-orders (above break_point)
        self.grid_strategy.exchange.place_order.assert_any_call('ETH/USDT', 'sell', 0.1, 2400, 'limit')
        self.grid_strategy.exchange.place_order.assert_any_call('ETH/USDT', 'sell', 0.1, 2600, 'limit')
        self.grid_strategy.exchange.place_order.assert_any_call('ETH/USDT', 'sell', 0.1, 2800, 'limit')

        # Check the number of times place_order was called
        self.assertEqual(self.grid_strategy.exchange.place_order.call_count, 5)  # 2 buys, 3 sells

    def helper_compare_order_by_order(self, break_point):
        for i in range(break_point):
            self.grid_strategy.exchange.place_order.assert_any_call(
                'ETH/USDT', 'buy', self.grid_strategy.fixed_trade_amount, self.grid_strategy.grid_levels[i], 'limit')

        for i in range(break_point + 1, len(self.grid_strategy.grid_levels)):
            self.grid_strategy.exchange.place_order.assert_any_call(
                'ETH/USDT', 'sell', self.grid_strategy.fixed_trade_amount, self.grid_strategy.grid_levels[i], 'limit')

    def test_initialize_grid_orders(self, starting_price=None, actual_break_point=None):
        starting_price = starting_price if starting_price else self.grid_strategy.starting_price
        actual_break_point = actual_break_point if actual_break_point else self.grid_strategy.previous_price_idx

        break_point = self.grid_strategy.get_grid_index_with_current_price(starting_price)

        self.assertEqual(actual_break_point, break_point)
        self.grid_strategy.initialize_grid_orders(break_point)

        self.assertEqual(actual_break_point, len(self.grid_strategy.open_buy_orders))
        self.assertEqual(self.grid_strategy.num_grids - actual_break_point, len(self.grid_strategy.open_sell_orders))

        self.helper_compare_order_by_order(break_point)  # call helper function to compare order detail

    def test_update_grid_orders_with_drop_price(self):
        self.test_initialize_grid_orders(2645.78, 48)  # starting_price = 2645.78, actual_break_point = 48
        self.grid_strategy.previous_price_idx = 48  # updates prev idx

        new_price = 2375  # new price 2375 (actual_break_point = 34)
        break_point = self.grid_strategy.get_grid_index_with_current_price(new_price)
        self.assertEqual(34, break_point)

        self.grid_strategy.update_grid_orders(break_point)

        # check if number of buy-orders and sell-orders updated correctly.
        self.assertEqual(break_point, len(self.grid_strategy.open_buy_orders))
        self.assertEqual(self.grid_strategy.num_grids - break_point, len(self.grid_strategy.open_sell_orders))

        self.helper_compare_order_by_order(break_point)  # call helper function to compare orders detail

    def test_update_grid_orders_with_drop_then_raise_prices(self):
        # test scenario: prices drops then raises.
        # starting_price = 2645.78, actual_break_point = 48
        # new price = 2375, actual_break_point = 34,
        self.test_update_grid_orders_with_drop_price()
        self.grid_strategy.previous_price_idx = 34  # updates prev idx

        new_price = 2565.39  # grid_levels[43] = 2555.98, grid_levels[44] = 2576.91
        actual_break_point = 44
        break_point = self.grid_strategy.get_grid_index_with_current_price(new_price)
        self.assertEqual(actual_break_point, break_point)

        self.grid_strategy.update_grid_orders(break_point)

        # check if number of buy-orders and sell-orders updated correctly.
        self.assertEqual(break_point, len(self.grid_strategy.open_buy_orders))
        self.assertEqual(self.grid_strategy.num_grids - break_point, len(self.grid_strategy.open_sell_orders))

        self.helper_compare_order_by_order(break_point)  # call helper function to compare orders detail

    def test_update_grid_orders_with_same_grid_level_prices_simple(self):
        starting_price = 2565.39
        actual_break_point = self.grid_strategy.get_grid_index_with_current_price(starting_price)
        self.assertEqual(44, actual_break_point)

        self.test_initialize_grid_orders(starting_price, actual_break_point)
        self.assertEqual(actual_break_point, len(self.grid_strategy.open_buy_orders))
        self.assertEqual(self.grid_strategy.num_grids - actual_break_point, len(self.grid_strategy.open_sell_orders))
        self.grid_strategy.previous_price_idx = actual_break_point  # update prev idx

        new_price = 2571.70  # new price = 2571.70, same grid level as previous price
        new_break_point = self.grid_strategy.get_grid_index_with_current_price(new_price)
        self.assertEqual(actual_break_point, new_break_point)

        self.grid_strategy.update_grid_orders(new_break_point)

        # check if number of buy-orders and sell-orders updated correctly.
        self.assertEqual(new_break_point, len(self.grid_strategy.open_buy_orders))
        self.assertEqual(self.grid_strategy.num_grids - new_break_point, len(self.grid_strategy.open_sell_orders))

        self.helper_compare_order_by_order(new_break_point)  # call helper function to compare orders detail

    def test_update_grid_orders_with_same_grid_level_prices_complex(self):
        self.test_update_grid_orders_with_drop_then_raise_prices()   # price changed: 2645.78 -> 2375 -> 2565.39
        last_idx = self.grid_strategy.get_grid_index_with_current_price(2565.39)
        self.grid_strategy.previous_price_idx = last_idx  # update prev idx

        new_price = 2571.70  # new price = 2571.70, same grid level as previous price 2565.39
        new_break_point = self.grid_strategy.get_grid_index_with_current_price(new_price)
        self.assertEqual(last_idx, new_break_point)

        self.grid_strategy.update_grid_orders(new_break_point)

        # check if number of buy-orders and sell-orders updated correctly.
        self.assertEqual(new_break_point, len(self.grid_strategy.open_buy_orders))
        self.assertEqual(self.grid_strategy.num_grids - new_break_point, len(self.grid_strategy.open_sell_orders))

        self.helper_compare_order_by_order(new_break_point)  # call helper function to compare orders detail


if __name__ == '__main__':
    unittest.main()
