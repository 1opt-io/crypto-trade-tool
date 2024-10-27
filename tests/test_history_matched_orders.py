import csv
import unittest

from src.service.exchange import Exchange
from src.strategy.binance_grid_strategy import BinanceGridStrategy


def create_order_info(side, price, amount, datetime):
    order_info = {
        'side': side,
        'price': price,
        'amount': amount,
        'datetime': datetime
    }
    return order_info


class TestBinanceGridStrategyWithHistoryData(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_exchange = Exchange()
        self.grid_instance = BinanceGridStrategy(self.temp_exchange)

        self.history_paired_orders = self.build_real_history_paired_orders()
        self.matched_orders = []


    def test_matche_order_and_profit(self):
        # test with compute_matched_profit()
        # Separate buy and sell orders
        print(f"\nTotal un-matched order: {len(self.history_paired_orders)}")
        print(f"> Before matching: Un-matched buy orders: {len(self.grid_instance.unmatched_closed_buy_order)}, "
              f"Un-matched sell orders: {len(self.grid_instance.unmatched_closed_sell_order)}")

        # sorts history orders by time
        self.history_paired_orders.sort(key=lambda x: x['datetime'])

        # call match_orders_and_compute_profit() to execute matching
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

        # print out matched/paired orders
        count = 0
        for order in self.grid_instance.matched_orders:
            print(order)
            count += 1
            if count % 2 == 0:
                print("\n")

        self.assertEqual(0, len(self.grid_instance.unmatched_closed_buy_order))
        self.assertEqual(len(self.history_paired_orders), len(self.grid_instance.matched_orders))

        # compare actual matched/paired orders with history matched orders
        actual_paired_orders = self.build_real_history_paired_orders()
        for i in range(len(self.grid_instance.matched_orders)):
            self.assertEqual(actual_paired_orders[i], self.grid_instance.matched_orders[i])

        print(f"\n\n> After matching: Un-matched buy orders: {len(self.grid_instance.unmatched_closed_buy_order)},"
              f"Un-matched sell orders: {len(self.grid_instance.unmatched_closed_sell_order)}")

        print(f"> # of matched orders: {len(self.grid_instance.matched_orders)},"
              f"total matched profit: {self.grid_instance.total_matched_profit}")

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
    unittest.main()
