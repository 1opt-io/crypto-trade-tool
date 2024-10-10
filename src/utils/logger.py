import logging


class Logger:
    def __init__(self, log_file='app.log'):
        # Configure the logger
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,  # Set logging level
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger()

        # Add console handler if you want to see logs in console as well
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger
