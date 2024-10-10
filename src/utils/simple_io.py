import os
import json


def get_path(relative_path, base_dir=None):
    """Get the absolute path from a relative path."""
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base_dir, relative_path))


def read_file(file_path):
    """Read JSON configuration from the specified file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file '{file_path}' not found.")

    with open(file_path, 'r') as file:
        return json.load(file)


def write_file(file_path, data):
    """Write JSON configuration to the specified file."""
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def check_file_info(file_path):

    try:
        with open(file_path, 'r') as file:
            data = json.load(file)

        # Check the size (number of keys if it's a dictionary, or length if it's a list)
        if isinstance(data, dict):
            size = len(data)
            print(f"Size (number of keys): {size}")
        elif isinstance(data, list):
            size = len(data)
            print(f"Size (number of items): {size}")

        # Check the content
        print("Content of the JSON data:")
        print(json.dumps(data, indent=4))  # Pretty-print the JSON content

        # Other information
        print("\nOther Information:")
        print(f"Type of data: {type(data)}")
        if isinstance(data, dict):
            for key, value in data.items():
                print(f"Key: {key}, Value Type: {type(value)}, Value: {value}")
        elif isinstance(data, list):
            for index, item in enumerate(data):
                print(f"Index: {index}, Item Type: {type(item)}, Item: {item}")

    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except json.JSONDecodeError:
        print("Error decoding JSON data.")

