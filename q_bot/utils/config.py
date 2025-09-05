import json
from typing import Dict, Any

def load_config(config_path: str = 'q_bot/config/settings.json') -> Dict[str, Any]:
    """
    Loads the JSON configuration file.

    :param config_path: The path to the configuration file.
    :return: A dictionary containing the configuration.
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {config_path}")
        return {}
