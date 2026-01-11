import os
import json

CONFIG_FILE = "config.json"

class ConfigManager:
    _instance = None
    _config = {
        "global_output_dir": ""
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """Load config from JSON file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self._config.update(json.load(f))
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        """Save current config to JSON file."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_global_output_dir(self):
        return self._config.get("global_output_dir", "")

    def set_global_output_dir(self, path):
        self._config["global_output_dir"] = path
        self.save_config()
