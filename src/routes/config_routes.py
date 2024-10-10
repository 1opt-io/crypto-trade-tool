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

            # Check if required parameters are present
            if not new_config:
                return jsonify({'error': 'No data provided'}), 400

            # Save the new configuration
            write_file(file_path, new_config)
            return jsonify({'message': 'Grid configuration updated successfully', 'config': new_config}), 200

        # If GET request, load the current configuration
        if request.method == 'GET':
            config = read_file(file_path)
            if config is None:
                return "Configuration file not found", 404
            return render_template('grid_config.html', config=config)
