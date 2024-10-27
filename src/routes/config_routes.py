import json

from flask import Blueprint, request, jsonify, render_template
from src.utils.simple_io import get_path, read_file, write_file


class ConfigRoutes:
    def __init__(self):
        self.config_routes = Blueprint('config', __name__)

        # Register config-related routes
        self.config_routes.add_url_rule('/authentication', methods=['GET', 'PUT'], view_func=self.config_credentials)
        self.config_routes.add_url_rule('/config_grid', methods=['GET', 'PUT'], view_func=self.config_grid_parameters)

    @staticmethod
    def config_credentials():
        user_credentials_relative_path = '../config/user_key_secret.json'
        if request.method == 'PUT':
            new_user_config = request.json  # Get new config data from the request

            # Check if required parameters are present
            if not new_user_config:
                return jsonify({'error': 'No data provided'}), 400
            elif not new_user_config['exchange_name']:
                return jsonify({'Missing exchange_name!'}), 400
            elif not new_user_config['market_type']:
                return jsonify({'Missing market_type!'}), 400
            elif not new_user_config['api_key']:
                return jsonify({'Missing api_key!'}), 400
            elif not new_user_config['secret']:
                return jsonify({'Missing secret!'}), 400

            # Save the new configuration
            return jsonify({'message': 'User credentials updated successfully!'}), 200

        # If GET request, load the current configuration
        if request.method == 'GET':
            # Load existing configuration or set defaults
            path = get_path(user_credentials_relative_path)
            json_file = read_file(path)

            return render_template('authentication.html', config=json_file)

    @staticmethod
    def config_grid_parameters():
        grid_config_relative_path = '../config/grid_config.json'
        file_path = get_path(grid_config_relative_path)

        if request.method == 'PUT':
            new_config = request.json  # Get new config data from the request

            # Debugging: log headers and body
            # print("Request headers:", request.headers)
            # print("Request data:", request.data)

            # Check if required parameters are present
            if not new_config:
                print("new_config is None")  # Debugging: log the incoming data
                return jsonify({'error': 'No data provided'}), 400

            print("New config received:", new_config)  # Debugging: log the incoming data

            # Save the new configuration
            new_config['min_price'] = float(new_config['min_price'])
            new_config['max_price'] = float(new_config['max_price'])
            new_config['num_grids'] = int(new_config['num_grids'])
            new_config['max_position'] = float(new_config['max_position'])
            new_config['fixed_trade_amount'] = float(new_config['fixed_trade_amount'])
            new_config['starting_price'] = float(new_config['starting_price'])
            new_config['security_deposit'] = float(new_config['security_deposit'])

            write_file(file_path, new_config)
            return jsonify({'message': 'Grid configuration updated successfully', 'config': new_config}), 200

        if request.method == 'GET':
            try:
                config = read_file(file_path)
                return render_template('grid_config.html', config=config)  # Render the HTML template
            except FileNotFoundError:
                return jsonify({'error': 'Configuration file not found'}), 404
            except json.JSONDecodeError:
                return jsonify({'error': 'Failed to decode JSON'}), 500
            except Exception as e:
                return jsonify({'error': str(e)}), 500
