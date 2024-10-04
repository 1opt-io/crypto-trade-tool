import csv
import os

import pandas as pd

from src.service.exchange import Exchange
from src.strategy.grid_strategy import GridStrategy


def read_original_data_and_filter():
    # Define the file path, expanding the user's home directory
    price_file_path = os.path.expanduser('~/Documents/data_futures_sorted.csv')

    try:
        # Read the CSV file into a DataFrame
        df = pd.read_csv(price_file_path, low_memory=False)  # Prevent DtypeWarning

        # Check if 'timestamp' column exists
        if 'timestamp' not in df.columns:
            raise KeyError("The 'timestamp' column is missing from the CSV file.")

        # Convert the 'timestamp' column to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # Drop rows where conversion failed (if any)
        df.dropna(subset=['timestamp'], inplace=True)

        # Display the row right before '2024-08-13 16:09:12'
        target_time = pd.to_datetime('2024-08-13 16:09:12')
        previous_row = df[df['timestamp'] < target_time].iloc[-1] if not df[df['timestamp'] < target_time].empty else None

        if previous_row is not None:
            print("Row right before '2024-08-13 16:09:12':")
            print(previous_row)
        else:
            print("No row found before the specified timestamp.")

        # Filter the DataFrame based on the specified timestamps
        filtered_df = df[(df['timestamp'] >= '2024-08-13 16:09:12') &
                         (df['timestamp'] <= '2024-09-21 08:50:12')]

        # Save the filtered DataFrame to a new CSV file
        filtered_file_path = os.path.expanduser('~/Documents/data_futures_sorted_filtered.csv')
        filtered_df.to_csv(filtered_file_path, index=False)

        print(f"Filtered data saved to {filtered_file_path}.")

    except FileNotFoundError:
        print(f"Error: The file '{price_file_path}' was not found.")
    except pd.errors.EmptyDataError:
        print("Error: The file is empty.")
    except KeyError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def read_prices():
    temp_exchange = Exchange()
    grid_instance = GridStrategy(temp_exchange)

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
            grid_instance.compare_history_prices_and_trade(float_price, timestamp)
        except Exception as e:
            print(f"Error in compare_history_prices_and_trade: {e}")

    """print("\n---- Buy Orders----")
        for buy_order in grid_instance.buy_orders:
            print(buy_order)
    
        print("\n---- Sell Orders----")
        for sell_order in grid_instance.sell_orders:
            print(sell_order)"""

    print(f"\n\nNumber of un-matched buy-orders: {len(grid_instance.buy_orders)}, "
          f"number of un-matched sell-orders: {len(grid_instance.sell_orders)}.")

    matched_profit = round(grid_instance.matched_profit, 2)
    print(f"Pairs of matched-orders (/2): {len(grid_instance.matched_orders) / 2}, "
          f"matched profit(round to two decimal places): {matched_profit }")

    # print(f"Use fixed profit(1.8360) for each matched order, matched profit(round to two decimal places):
    # {len(grid_instance.matched_orders) / 2 * 1.8360 }")

    # export data
    buy_orders_file_path = os.path.expanduser('~/Documents/buy_orders.csv')
    sell_orders_file_path = os.path.expanduser('~/Documents/sell_orders.csv')
    export_data(buy_orders_file_path, grid_instance.buy_orders)
    export_data(sell_orders_file_path, grid_instance.sell_orders)

    matched_orders_file_path = os.path.expanduser('~/Documents/matched_orders.csv')
    export_data(matched_orders_file_path, grid_instance.matched_orders)

    p1 = (2394.56 - 2355.82) * grid_instance.fixed_trade_amount
    p2 = (2414.16 - 2336.69) * grid_instance.fixed_trade_amount
    p3 = (2433.93 - 2371.71) * grid_instance.fixed_trade_amount
    p4 = (2453.86 - 2298.89) * grid_instance.fixed_trade_amount
    p5 = (2473.95 - 2280.22) * grid_instance.fixed_trade_amount
    p6 = (2494.21 - 2261.70) * grid_instance.fixed_trade_amount
    p7 = (2514.63 - 2243.33) * grid_instance.fixed_trade_amount
    p8 = (2535.22 - 2225.11) * grid_instance.fixed_trade_amount
    p9 = (2555.98 - 2207.04) * grid_instance.fixed_trade_amount

    real_matched_profits = [p1 / 2, p2 / 3, p3 / 4, p4/5, p5/6, p6/7, p7/8, p8/9, p9/10]
    rounded_real_matched_profits = [round(profit, 2) for profit in real_matched_profits]
    print(f"\nrounded_real_matched_profits: {rounded_real_matched_profits}")

    print("\n\n---- Test Completed----")


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


if __name__ == '__main__':
    # read_original_data_and_filter()
    read_prices()
