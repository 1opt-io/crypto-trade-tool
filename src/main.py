from src.routes.config_routes import ConfigRoutes
from src.routes.main_routes import MainRoutes
from flask import Flask

from src.service.exchange import Exchange
from src.strategy.binance_grid_strategy import BinanceGridStrategy
from src.utils.logger import Logger

logger = Logger().get_logger()


def create_app():
    app = Flask(__name__)

    # Initialize exchange manager and grid strategy
    exchange = Exchange()
    # default__grid_strategy = GridStrategy(exchange)  # use default grid strategy
    binance_grid = BinanceGridStrategy(exchange)

    logger.info("Creating instance of MainRoutes...")  # Create an instance of MainRoutes
    main_routes_instance = MainRoutes(binance_grid)
    config_routes = ConfigRoutes()

    logger.info("Registering the blueprints...")  # Register blueprints
    app.register_blueprint(main_routes_instance.main_routes)
    app.register_blueprint(config_routes.config_routes)

    # return app, binance_grid  # Return both app and binance_grid
    return app  # No need to return binance_grid


def run_grid_strategy(binance_grid):
    """Run the grid strategy in a separate thread."""
    try:
        binance_grid.execute()  # No outer loop; rely on internal looping
    except Exception as e:
        print(f"An error occurred in the grid strategy: {e}")


def main():
    try:
        # app, binance_grid = create_app()  # Get both app and binance_grid
        app = create_app()

        # Start the grid strategy in a separate thread
        # grid_strategy_thread = threading.Thread(target=run_grid_strategy, args=(binance_grid,))
        # grid_strategy_thread.daemon = True  # Allow thread to exit when the main program exits
        # grid_strategy_thread.start()

        app.run(debug=True)

    except KeyboardInterrupt:
        logger.info("\n\nProgram interrupted by user. Exiting...")

    except Exception as e:
        logger.info(f"An unexpected error occurred(main): {e}")

    finally:
        # Ensure any necessary cleanup is done here
        logger.info("Exiting program.")


if __name__ == "__main__":
    main()
