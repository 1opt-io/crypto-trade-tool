import csv
import os
import unittest

import pandas as pd

from src.service.exchange import Exchange
from src.strategy.binance_grid_strategy import BinanceGridStrategy


def read_prices(binance_grid: BinanceGridStrategy):
    price_file_path = '/Users/yang/Documents/data_futures_sorted_filtered.csv'
    # Read the CSV file into a DataFrame
    df = pd.read_csv(price_file_path)

    # Display the DataFrame to see the data
    print(df.head())  # Display the first few rows of the DataFrame

    # Access specific columns
    for index, row in df.iterrows():
        timestamp = row['timestamp']
        price_str = row['close']  # Access the 'close' price

        # Attempt to convert the price to float
        try:
            float_price = float(price_str)  # Direct conversion
        except ValueError as e:
            print(f"Could not convert price '{price_str}' to float. Error: {e}")
            continue

        try:
            binance_grid.execute_with_history_prices(float_price, timestamp)
        except Exception as e:
            print(f"Error in compare_history_prices_and_trade: {e}")

    # export buy-orders, sell-orders, and matched-orders
    buy_orders_file_path = os.path.expanduser('~/Documents/buy_orders.csv')
    sell_orders_file_path = os.path.expanduser('~/Documents/sell_orders.csv')
    export_data(buy_orders_file_path, binance_grid.open_buy_orders)
    export_data(sell_orders_file_path, binance_grid.open_sell_orders)

    matched_orders_file_path = os.path.expanduser('~/Documents/matched_orders.csv')
    export_data(matched_orders_file_path, binance_grid.matched_orders)
    print("\n\n---- read_prices() Completed----")


def export_data(file_path, orders):
    # Writing to a CSV file
    with open(file_path, 'w', newline='') as csv_file:
        fieldnames = ['side', 'amount', 'price', 'date']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        # Writing headers
        writer.writeheader()

        # Write each dictionary in sell_orders to the CSV file
        for order in orders:
            writer.writerow(order)


def create_order_info(side, price, amount, time_stamp):
    order_info = {
        'side': side,
        'price': price,
        'amount': amount,
        'time_stamp': time_stamp
    }
    return order_info


class TestBinanceGridStrategyWithHistoryData(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_exchange = Exchange()
        self.grid_instance = BinanceGridStrategy(self.temp_exchange)

        self.history_paired_orders = self.build_real_history_paired_orders()
        self.matched_orders = []

    def test_first(self):
        # test with get_current_grid_price_index()
        pass

    def test_second(self):
        # test with init_place_grid_orders()
        starting_price = 2375
        break_point_1 = self.grid_instance.get_grid_index_with_current_price(starting_price)
        self.assertEqual(34, break_point_1)  # 0-based

        self.grid_instance.init_grid_orders(break_point_1)  # buy=34, sell=51
        print(f"After init_place_grid_orders: #buy-order: {len(self.grid_instance.open_buy_orders)}, "
              f"#sell-order: {len(self.grid_instance.open_sell_orders)}.")
        self.assertEqual(34, len(self.grid_instance.open_buy_orders))
        self.assertEqual(51, len(self.grid_instance.open_sell_orders))

        # update parameters
        self.grid_instance.previous_price_idx = break_point_1

    def test_third(self):
        self.test_second()  # dependent on prev
        # test with adjust_grid_orders()

        new_price = 2571.70
        break_point_2 = self.grid_instance.get_grid_index_with_current_price(new_price)
        self.assertEqual(44, break_point_2)  # 0-based, # buy=44, sell=41

        self.grid_instance.adjust_grid_orders(break_point_2)

        print(f"After adjustment (1): #buy-order: {len(self.grid_instance.open_buy_orders)}, "
              f"#sell-order: {len(self.grid_instance.open_sell_orders)}.")

        self.assertEqual(44, len(self.grid_instance.open_buy_orders))
        self.assertEqual(41, len(self.grid_instance.open_sell_orders))

        # update parameters
        self.grid_instance.previous_price_idx = break_point_2

    def test_fourth(self):
        self.test_third()  # dependent on prev
        # test with adjust_grid_orders() again

        new_price = 2375
        break_point_3 = self.grid_instance.get_grid_index_with_current_price(new_price)
        self.assertEqual(34, break_point_3)  # 0-based,  # buy=34, sell=51

        self.grid_instance.adjust_grid_orders(break_point_3)

        print(f"After adjustment (2): #buy-order: {len(self.grid_instance.open_buy_orders)}, "
              f"#sell-order: {len(self.grid_instance.open_sell_orders)}.")

        self.assertEqual(34, len(self.grid_instance.open_buy_orders))
        self.assertEqual(51, len(self.grid_instance.open_sell_orders))

    def test_fifth(self):
        # test with compute_matched_profit()
        # Separate buy and sell orders
        print(f"\nTotal un-matched order: {len(self.history_paired_orders)}")
        print(f"> Before matching: Un-matched buy orders: {len(self.grid_instance.unmatched_closed_buy_order)}, "
              f"Un-matched sell orders: {len(self.grid_instance.unmatched_closed_sell_order)}")

        self.history_paired_orders.sort(key=lambda x: x['time_stamp'])

        count = 0

        for order in self.history_paired_orders:
            found_match = self.grid_instance.match_orders_and_compute_profit(order)
            if found_match:
                print(f"Matched {count + 1} pair of orders!")
            else:
                if order['side'] == 'buy':
                    self.grid_instance.unmatched_closed_buy_order.append(order)
                else:
                    self.grid_instance.unmatched_closed_sell_order.append(order)

        print(f"> After matching: Un-matched buy orders: {len(self.grid_instance.unmatched_closed_buy_order)},"
              f"Un-matched sell orders: {len(self.grid_instance.unmatched_closed_sell_order)}")

        count = 0
        for order in self.grid_instance.matched_orders:
            print(order)
            count += 1
            if count % 2 == 0:
                print("\n")

        self.assertEqual(0, len(self.grid_instance.unmatched_closed_buy_order))
        self.assertEqual(len(self.history_paired_orders), len(self.grid_instance.matched_orders))

        actual_paired_orders = self.build_real_history_paired_orders()
        for i in range(len(self.grid_instance.matched_orders)):
            self.assertEqual(actual_paired_orders[i], self.grid_instance.matched_orders[i])

    @staticmethod
    def build_real_history_paired_orders():
        buy = 'buy'
        sell = 'sell'
        amount = 0.093

        history_orders = [
            # ---- 1
            create_order_info(buy, 2619.28, amount, '2024-08-13 18:23:11'),  # sell 1 matched with buy 1
            create_order_info(sell, 2640.73, amount, '2024-08-13 19:35:37'),  # buy 1 matched with sell 1

            create_order_info(buy, 2640.73, amount, '2024-08-13 22:31:40'),  # buy 2 matched with sell 2
            create_order_info(sell, 2662.35, amount, '2024-08-13 21:46:27'),  # buy 2 matched with sell 2

            create_order_info(buy, 2706.13, amount, '2024-08-14 01:51:47'),  # buy 3 matched with sell 3
            create_order_info(sell, 2728.28, amount, '2024-08-14 01:46:20'),  # sell 3 matched with buy 3

            # ---- 2
            create_order_info(buy, 2684.15, amount, '2024-08-14 03:16:03'),
            create_order_info(sell, 2706.13, amount, '2024-08-14 00:49:47'),

            create_order_info(buy, 2706.13, amount, '2024-08-14 07:12:10'),
            create_order_info(sell, 2728.28, amount, '2024-08-14 05:58:44'),

            create_order_info(buy, 2684.15, amount, '2024-08-14 10:04:31'),
            create_order_info(sell, 2706.13, amount, '2024-08-14 03:28:17'),

            # ---- 3
            create_order_info(buy, 2728.28, amount, '2024-08-14 19:06:17'),
            create_order_info(sell, 2750.62, amount, '2024-08-14 18:37:14'),

            create_order_info(buy, 2750.62, amount, '2024-08-14 20:30:54'),
            create_order_info(sell, 2773.15, amount, '2024-08-14 20:29:56'),

            create_order_info(buy, 2728.28, amount, '2024-08-14 20:52:11'),
            create_order_info(sell, 2750.62, amount, '2024-08-14 19:40:30'),

            # ---- 4
            create_order_info(buy, 2706.13, amount, '2024-08-14 21:34:52'),
            create_order_info(sell, 2728.28, amount, '2024-08-14 13:10:27'),

            create_order_info(buy, 2684.15, amount, '2024-08-14 21:44:17'),
            create_order_info(sell, 2706.13, amount, '2024-08-14 10:45:39'),

            create_order_info(buy, 2662.35, amount, '2024-08-14 21:51:24'),
            create_order_info(sell, 2684.15, amount, '2024-08-14 00:37:02'),

            # ---- 5
            create_order_info(buy, 2640.73, amount, '2024-08-14 22:11:36'),
            create_order_info(sell, 2662.35, amount, '2024-08-13 22:55:08'),

            create_order_info(buy, 2640.73, amount, '2024-08-14 22:38:04'),
            create_order_info(sell, 2662.35, amount, '2024-08-14 22:26:00'),

            create_order_info(buy, 2640.73, amount, '2024-08-14 23:10:46'),
            create_order_info(sell, 2662.35, amount, '2024-08-14 23:04:12'),

            # ---- 6
            create_order_info(buy, 2662.35, amount, '2024-08-15 00:00:39'),
            create_order_info(sell, 2684.15, amount, '2024-08-14 23:45:37'),

            create_order_info(buy, 2640.73, amount, '2024-08-15 00:25:45'),
            create_order_info(sell, 2662.35, amount, '2024-08-14 23:41:10'),

            create_order_info(buy, 2640.73, amount, '2024-08-15 06:03:46'),
            create_order_info(sell, 2662.35, amount, '2024-08-15 00:46:36'),

            # ---- 7
            create_order_info(buy, 2640.73, amount, '2024-08-15 09:58:26'),
            create_order_info(sell, 2662.35, amount, '2024-08-15 06:19:33'),

            create_order_info(buy, 2640.73, amount, '2024-08-15 13:19:45'),
            create_order_info(sell, 2662.35, amount, '2024-08-15 10:15:35'),

            create_order_info(buy, 2598.01, amount, '2024-08-15 15:29:09'),
            create_order_info(sell, 2619.28, amount, '2024-08-15 16:59:19'),

            # ---- 8
            # create_order_info(buy, 2598.01, amount, '2024-08-15 15:29:09')  # duplicated pair
            # create_order_info(sell, 2619.28, amount, '2024-08-15 16:59:19')

            create_order_info(buy, 2619.28, amount, '2024-08-15 14:22:25'),
            create_order_info(sell, 2640.73, amount, '2024-08-15 19:28:32'),

            create_order_info(buy, 2640.73, amount, '2024-08-15 20:57:36'),
            create_order_info(sell, 2662.35, amount, '2024-08-15 20:40:55'),

            # ---- 9
            create_order_info(buy, 2640.73, amount, '2024-08-16 01:50:29'),
            create_order_info(sell, 2662.35, amount, '2024-08-15 21:35:24'),

            create_order_info(buy, 2555.98, amount, '2024-08-16 02:02:54'),
            create_order_info(sell, 2576.91, amount, '2024-08-16 02:05:28'),

            create_order_info(buy, 2535.22, amount, '2024-08-16 03:09:12'),
            create_order_info(sell, 2555.98, amount, '2024-08-16 03:55:54'),

            # ---- 10
            create_order_info(buy, 2514.63, amount, '2024-08-16 04:56:00'),
            create_order_info(sell, 2535.22, amount, '2024-08-16 04:59:33'),

            create_order_info(buy, 2535.22, amount, '2024-08-16 04:08:15'),
            create_order_info(sell, 2555.98, amount, '2024-08-16 05:38:38'),

            create_order_info(buy, 2555.98, amount, '2024-08-16 02:12:17'),
            create_order_info(sell, 2576.91, amount, '2024-08-16 06:29:33'),

            # ---- 11
            create_order_info(buy, 2555.98, amount, '2024-08-16 09:19:20'),
            create_order_info(sell, 2576.91, amount, '2024-08-16 10:28:53'),

            create_order_info(buy, 2576.91, amount, '2024-08-16 02:02:15'),
            create_order_info(sell, 2598.01, amount, '2024-08-16 10:31:49'),

            create_order_info(buy, 2576.91, amount, '2024-08-16 11:21:22'),
            create_order_info(sell, 2598.01, amount, '2024-08-16 13:02:09'),

            # ---- 12
            create_order_info(buy, 2598.01, amount, '2024-08-16 02:00:22'),
            create_order_info(sell, 2619.28, amount, '2024-08-16 14:47:06'),

            create_order_info(buy, 2576.91, amount, '2024-08-16 20:30:47'),
            create_order_info(sell, 2598.01, amount, '2024-08-16 21:16:40'),

            create_order_info(buy, 2576.91, amount, '2024-08-16 21:53:21'),
            create_order_info(sell, 2598.01, amount, '2024-08-16 22:00:15'),

            # ---- 13
            create_order_info(buy, 2576.91, amount, '2024-08-16 22:12:47'),
            create_order_info(sell, 2598.01, amount, '2024-08-16 22:43:22'),

            create_order_info(buy, 2555.98, amount, '2024-08-16 23:35:12'),
            create_order_info(sell, 2576.91, amount, '2024-08-17 00:14:03'),

            create_order_info(buy, 2576.91, amount, '2024-08-16 22:52:06'),
            create_order_info(sell, 2598.01, amount, '2024-08-17 00:28:59'),
        ]

        return history_orders


if __name__ == '__main__':
    # read_prices()
    unittest.main()
