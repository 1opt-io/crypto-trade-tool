from src.utils.simple_io import get_path, read_file, check_file_info
import unittest


class TestGridStrategy(unittest.TestCase):
    def setUp(self):
        self.testnet_future_path = None

    def test_with_utils_get_path(self=None):
        # Using get_path to construct the path to the config file
        self.testnet_future_path = get_path('../config/testnet_future.json')
        self.assertIsNotNone(self.testnet_future_path)

    def test_with_utils_read_file(self=None):
        # Reading the testnet_future by calling read_config()
        testnet_future_config = None
        try:
            self.testnet_future_path = get_path('../config/testnet_future.json')
            print(f"testnet_future_path: {self.testnet_future_path}")
            testnet_future_config = read_file(self.testnet_future_path)
            for e in testnet_future_config:
                print(f" {e} : {testnet_future_config[e]}")
        except FileNotFoundError:
            print("Config file not found.")
        self.assertEqual(True, testnet_future_config['isTestnet'])

    def test_with_utils_check_file_info(self):
        self.testnet_future_path = get_path('../config/testnet_future.json')
        check_file_info(self.testnet_future_path)


if __name__ == '__main__':
    unittest.main()
