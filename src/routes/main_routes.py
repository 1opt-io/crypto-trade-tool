import csv
import threading
from datetime import datetime

from flask import Blueprint, render_template, jsonify, current_app

from src.strategy.binance_grid_strategy import BinanceGridStrategy
from src.utils.simple_io import get_path, read_file


class MainRoutes:
    def __init__(self, grid_strategy: BinanceGridStrategy):
        self.grid_strategy = grid_strategy
        self.main_routes = Blueprint('main', __name__)  # Define the Blueprint

        # Register routes
        self.main_routes.add_url_rule('/', methods=['GET'], view_func=self.home)
        self.main_routes.add_url_rule('/routes', methods=['GET'], view_func=self.list_routes)

        self.main_routes.add_url_rule('/current_orders', methods=['GET'], view_func=self.get_current_orders)
        self.main_routes.add_url_rule('/matched_profit', methods=['GET'], view_func=self.get_matched_orders)
        self.main_routes.add_url_rule('/realized_profit_loss', methods=['GET'], view_func=self.get_realized_profit_loss)

        self.main_routes.add_url_rule('/start_trading', methods=['POST'], view_func=self.start_auto_trading)
        self.main_routes.add_url_rule('/stop_trading', methods=['POST'], view_func=self.stop_auto_trading)

        self.main_routes.add_url_rule('/latest_and_average_price', methods=['GET'], view_func=self.get_latest_and_average_price)

    def stop_auto_trading(self):
        try:
            self.grid_strategy.stop()  # unable it to test frontend
            return jsonify({'message': 'Auto-trading stopped successfully'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    def start_auto_trading(self):
        try:
            # Trigger the auto-trading process
            thread = threading.Thread(target=self.grid_strategy.execute)
            thread.start()  # Start the thread

            return jsonify({'message': 'Auto-trading started successfully'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @staticmethod
    def home():
        return render_template('index.html')

    @staticmethod
    def list_routes():
        routes = []
        for rule in current_app.url_map.iter_rules():
            routes.append((rule.endpoint, str(rule)))

        return render_template('list_routes.html', routes=routes)

    def get_current_orders(self):
        """
        Fetch and display the order history, including open and closed orders, sorted into buy and sell lists.
        """
        if self.grid_strategy.active:
            buy_orders = []
            sell_orders = []

            # Separate buy and sell orders, and sort by price
            for i in range(len(self.grid_strategy.orders)):
                order = self.grid_strategy.orders[i]

                # order['datetime'] = self.parse_date_time_to_readable(order['datetime'])

                if order['side'] == 'buy':
                    buy_orders.append(order)
                else:
                    sell_orders.append(order)

            # Sort buy orders by price (decreasing)
            buy_orders.sort(key=lambda x: x['price'], reverse=True)

            # Sort sell orders by price (increasing)
            sell_orders.sort(key=lambda x: x['price'])

            # Render the template with buy and sell orders
            return render_template('current_orders.html', buy_orders=buy_orders, sell_orders=sell_orders)
        else:
            return jsonify({'Note': 'Auto-trading is not active, no open orders!'}), 200

    def get_realized_profit_loss(self):
        # Example function call to get realized profit/loss
        # realized_profit_loss = self.grid_strategy.compute_realized_profit_loss()
        # return render_template('realized_profit_loss.html', profit_loss=realized_profit_loss)
        pass

    def get_matched_orders(self):
        matched_orders = []
        total_matched_profit = 0  # Initialize total matched profit

        if self.grid_strategy.active:
            total_matched_profit = self.grid_strategy.total_matched_profit
            matched_orders = self.grid_strategy.matched_orders
        else:
            # Tell user the Auto-Trading Bot is not active now
            # And give another option: View history matched-orders(import from a file)
            grid_config_relative_path = '../data/matched_orders.csv'
            file_path = get_path(grid_config_relative_path)

            try:
                with open(file_path, mode='r', newline='') as file:
                    reader = csv.DictReader(file)  # Read as dictionaries with header
                    orders = [row for row in reader]  # Convert to a list of dictionaries

                # Calculate profit for each matched pair
                for i in range(0, len(orders), 2):  # Assuming every two rows are a matched pair
                    if i + 1 < len(orders):  # Ensure there's a matching sell order
                        buy_order = orders[i]
                        sell_order = orders[i + 1]

                        # Calculate profit for this matched pair
                        buy_price = float(buy_order['price'])
                        buy_amount = float(buy_order['amount'])
                        sell_price = float(sell_order['price'])
                        sell_amount = float(sell_order['amount'])

                        profit = (sell_price * sell_amount) - (buy_price * buy_amount)
                        rounded_profit = round(profit, 2)

                        total_matched_profit += profit

                        matched_orders.append({
                            'buy_order_id': buy_order['id'],
                            'buy_price': buy_order['price'],
                            'buy_amount': buy_order['amount'],
                            'buy_datetime': buy_order['datetime'],
                            'sell_order_id': sell_order['id'],
                            'sell_price': sell_order['price'],
                            'sell_amount': sell_order['amount'],
                            'sell_datetime': sell_order['datetime'],
                            'matched_profit': rounded_profit
                        })

            except Exception as e:
                # Handle any file reading errors
                print(f"Error reading matched orders from file: {e}")
                matched_orders = []  # Clear matched orders on error

            total_matched_profit = round(total_matched_profit, 2)
        return render_template('matched_orders.html', total_matched_profit=total_matched_profit,
                               matched_orders=matched_orders)

    def get_latest_and_average_price(self):
        try:
            symbol = 'ETH/USDT'
            timeframe = '1h'

            latest_price = self.grid_strategy.exchange.fetch_ticker(symbol)['last']
            ohlcv = self.grid_strategy.exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            if not ohlcv:
                raise ValueError("No OHLCV data returned")

            # Extract the closing prices and calculate the average
            closing_prices = [candle[4] for candle in ohlcv]  # index 4 is the close price
            average_close_price = sum(closing_prices) / len(closing_prices)

            latest_and_average = [latest_price, average_close_price]

            return render_template('latest_and_average.html', values=latest_and_average)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @staticmethod
    def parse_date_time_to_readable(date_time):
        time = date_time.replace("Z", "+00:00")
        dt = date_time.fromisoformat(time)
        readable_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        return readable_time
