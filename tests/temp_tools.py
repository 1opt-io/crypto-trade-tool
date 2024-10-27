import pandas as pd

from src.service.exchange import Exchange
from src.strategy.binance_grid_strategy import BinanceGridStrategy


def get_and_process_closed_orders(binance_grid_instance, timestamp_since):
    try:

        # Fetch closed orders since the last timestamp
        closed_orders = binance_grid_instance.exchange.market.\
            fetch_closed_orders(binance_grid_instance.tracking_symbol, timestamp_since)

        # Check if there are any closed orders
        if not closed_orders:
            print(f"No closed orders found.")
            return

        # Sort closed orders by datetime
        closed_orders.sort(key=lambda x: x['datetime'])

        # Process each closed order
        for order in closed_orders:
            found_match = binance_grid_instance.match_orders_and_compute_profit(order)
            if not found_match:
                if order['side'] == 'buy':
                    binance_grid_instance.unmatched_closed_buy_order.append(order)
                else:
                    binance_grid_instance.unmatched_closed_sell_order.append(order)

        print(f"Processed {len(closed_orders)} closed orders since last timestamp.")

        latest_timestamp = closed_orders[-1]['timestamp']  # or 'datetime' depending on your needs
        binance_grid_instance.last_time_stamp = latest_timestamp
        print(f"Updated last timestamp to: {latest_timestamp}")

    except Exception as e:
        print(f"Error fetching closed orders: {e}")


def export_closed_orders(binance_grid_instance):
    try:
        closed_orders = binance_grid_instance.exchange.fetch_closed_orders(binance_grid_instance.tracking_symbol)

        if closed_orders:
            # Convert closed orders to a DataFrame for easier manipulation
            df = pd.DataFrame(closed_orders)

            # Optionally, you can filter specific columns if needed
            df = df[['id', 'symbol', 'side', 'price', 'amount', 'cost', 'status', 'datetime', 'timestamp']]

            df.to_csv('closed_orders.csv', index=False)  # Export to a CSV file
            print("Closed orders exported successfully to closed_orders.csv")
        else:
            print(f"No closed orders for {binance_grid_instance.tracking_symbol}")

    except Exception as e:
        print(f"Failed to export closed orders: {e}")


def export_matched_orders(binance_grid_instance):
    try:
        if not binance_grid_instance.matched_orders or len(binance_grid_instance.matched_orders) == 0:
            print(f"matched_orders is empty.")
        else:
            df = pd.DataFrame(binance_grid_instance.matched_orders)

            # Optionally, you can filter specific columns if needed
            df = df[['id', 'symbol', 'side', 'price', 'amount', 'cost', 'status', 'datetime', 'timestamp']]

            df.to_csv('matched_orders.csv', index=False)  # Export to a CSV file
            print("matched_orders exported successfully to matched_orders.csv")
    except Exception as e:
        print(f"Failed to export matched_orders: {e}")


def clean_up(binance_grid_instance):
    print("> Cancelling open orders...")
    open_orders = binance_grid_instance.exchange.fetch_open_orders(binance_grid_instance.tracking_symbol)
    if open_orders:
        for order in open_orders:
            print(order)
        binance_grid_instance.cancel_all_open_orders()
    else:
        print("No open orders found!")


if __name__ == '__main__':
    exchange = Exchange()
    grid_instance = BinanceGridStrategy(exchange)

    clean_up(grid_instance)  # cancel all open orders

    timestamp = 1730010088577
    get_and_process_closed_orders(grid_instance, timestamp)

    # export data
    export_matched_orders(grid_instance)
    export_closed_orders(grid_instance)

    # print out balance
    balance = grid_instance.exchange.fetch_balance()
    usdt_balance = grid_instance.exchange.fetch_specific_asset_balance('USDT')
    eth_balance = grid_instance.exchange.fetch_specific_asset_balance('ETH')
    print(f"usdt_balance: {usdt_balance}")
    print(f"eth_balance: {eth_balance}")

    # print out matched orders and profit
    print(f"Total matched profit: {grid_instance.total_matched_profit}")
    print(f"# matched orders: {len(grid_instance.matched_orders)}")
    print(f"# Un-matched buy orders: {len(grid_instance.unmatched_closed_buy_order)}")
    print(f"# Un-matched sell orders: {len(grid_instance.unmatched_closed_sell_order)}")
