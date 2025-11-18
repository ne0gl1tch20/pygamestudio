# engine/core/engine_config.py
import json
import os
import sys

# Assume engine/utils/file_utils.py is available. We must define a minimal
# fallback if it's not (though the generator assumes it will be requested/exists).
try:
    from engine.utils.file_utils import FileUtils
except ImportError:
    # Minimal fallback logging to prevent crash if FileUtils hasn't been generated yet
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[Config-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[Config-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def log_warning(msg): print(f"[Config-WARN] {msg}")
        @staticmethod
        def create_dirs_if_not_exist(path): os.makedirs(path, exist_ok=True)


class EngineConfig:
    """
    Manages the persistent editor and project settings, loading them from
    settings.json and providing centralized access.
    
    The engine relies on the 'config' directory being one level up from 'core' 
    (i.e., at the root of the project).
    """
    
    # Define default file path and structure (matching startup.py)
    # Get to project root: PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
    CONFIG_FILE = os.path.join(CONFIG_DIR, 'settings.json')
    PROJECTS_DIR = os.path.join(PROJECT_ROOT, 'projects')
    PLUGINS_DIR = os.path.join(PROJECT_ROOT, 'plugins')
    
    def __init__(self):
        """Loads the configuration file, or initializes with defaults."""
        self._config_data = {}
        self.load_config()

    def _get_default_config(self):
        """Returns the default configuration structure."""
        return {
            "engine_version": "V4.0.0",
            "editor_settings": {
                "screen_width": 1280,
                "screen_height": 720,
                "theme": "dark", # light/dark, used by editor_ui.py
                "autosave_interval_minutes": 5,
                "default_project_path": self.PROJECTS_DIR,
                "last_opened_project": os.path.join(self.PROJECTS_DIR, 'example_project'), # Default to example
                "show_fps": True,
                "grid_snap": True,
                "plugin_dirs": [self.PLUGINS_DIR] # Where to look for plugins
            },
            "project_settings": {
                "game_title": "New Pygame Godmode Project",
                "resolution_x": 800,
                "resolution_y": 600,
                "target_fps": 60,
                "network_port": 5555,
                "max_players": 4,
                "is_3d_mode": False
            },
            "network_settings": {
                "default_port": 5555,
                "default_host": "127.0.0.1",
                "max_connections": 10
            }
        }
    
    def load_config(self):
        """Loads configuration from the settings.json file."""
        FileUtils.create_dirs_if_not_exist(self.CONFIG_DIR)
            
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    default_data = self._get_default_config()
                    
                    # Merge loaded data with defaults (deep merge for nested dicts)
                    self._config_data = default_data.copy()
                    for key, value in loaded_data.items():
                        if isinstance(value, dict) and key in self._config_data and isinstance(self._config_data[key], dict):
                            self._config_data[key].update(value)
                        else:
                            self._config_data[key] = value
                            
                    FileUtils.log_message(f"Loaded configuration from {self.CONFIG_FILE}")
            except json.JSONDecodeError as e:
                FileUtils.log_error(f"Corrupted settings.json ({e}). Using default config.")
                self._config_data = self._get_default_config()
            except Exception as e:
                FileUtils.log_error(f"Error reading config file: {e}. Using default config.")
                self._config_data = self._get_default_config()
        else:
            self._config_data = self._get_default_config()
            self.save_config() # Save the default config
            FileUtils.log_message(f"Created default configuration file: {self.CONFIG_FILE}")

    def save_config(self):
        """Saves the current configuration data back to the settings.json file."""
        try:
            FileUtils.create_dirs_if_not_exist(self.CONFIG_DIR)
            
            # Use a temporary file for atomic save
            temp_file = self.CONFIG_FILE + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._config_data, f, indent=4)
            
            # Atomically rename
            os.replace(temp_file, self.CONFIG_FILE)
            FileUtils.log_message(f"Configuration saved to {self.CONFIG_FILE}")
        except Exception as e:
            FileUtils.log_error(f"ERROR: Could not write configuration file: {e}")

    # --- Property Accessors (read-only for settings dicts) ---
    
    @property
    def editor_settings(self):
        """Returns the editor settings dictionary."""
        return self._config_data.get("editor_settings", {})
        
    @property
    def project_settings(self):
        """Returns the current project settings dictionary."""
        return self._config_data.get("project_settings", {})
        
    @property
    def network_settings(self):
        """Returns the network settings dictionary."""
        return self._config_data.get("network_settings", {})

    def get_setting(self, category, key, default=None):
        """Generic method to retrieve a setting."""
        return self._config_data.get(category, {}).get(key, default)

    def set_setting(self, category, key, value):
        """
        Generic method to set a setting. 
        Note: Caller must explicitly call save_config() to persist changes.
        """
        if category in self._config_data:
            self._config_data[category][key] = value
        else:
            FileUtils.log_error(f"Attempted to set setting in unknown category: {category}")