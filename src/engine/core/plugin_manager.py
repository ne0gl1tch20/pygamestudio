# engine/core/plugin_manager.py
import os
import sys
import importlib.util
import json

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.core.engine_config import EngineConfig # Used for plugin paths

except ImportError as e:
    print(f"[PluginManager Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class EngineConfig:
        def __init__(self):
            self.editor_settings = {"plugin_dirs": [os.path.join(os.getcwd(), 'plugins')]}
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[PM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[PM-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def log_warning(msg): print(f"[PM-WARN] {msg}")
        @staticmethod
        def read_json(path): return {}


# --- Plugin API Definition ---

class PluginAPI:
    """
    The interface provided to external plugin Python modules.
    Plugins use this API to interact with and extend the engine.
    """
    def __init__(self, state: EngineState):
        self.state = state

    def register_ui_panel(self, panel_name: str, render_func, initial_state: dict = None):
        """Registers a custom UI panel callable by the EditorUI/TopBar."""
        # NOTE: This call will be intercepted by EditorUI in the main loop.
        if self.state.is_editor_mode and hasattr(self.state, 'editor_ui'):
            self.state.editor_ui.register_plugin_panel(panel_name, render_func, initial_state)
            FileUtils.log_message(f"Plugin API: Registered UI Panel '{panel_name}'.")
        else:
            FileUtils.log_warning(f"Plugin API: Cannot register UI Panel '{panel_name}' outside Editor mode.")

    def register_custom_component(self, component_name: str, init_func, update_func, schema: dict = None):
        """Registers a custom component type that can be added to SceneObjects."""
        if self.state.script_engine:
            self.state.script_engine.register_custom_component(component_name, init_func, update_func, schema)
            FileUtils.log_message(f"Plugin API: Registered Custom Component '{component_name}'.")
        else:
            FileUtils.log_warning(f"Plugin API: Cannot register Custom Component '{component_name}' (ScriptEngine not ready).")
            
    def register_menu_command(self, menu_path: str, command_func):
        """Registers a callable function to an Editor TopBar menu path (e.g., 'File/MyCommand')."""
        if self.state.is_editor_mode and hasattr(self.state, 'editor_ui'):
            self.state.editor_ui.register_plugin_menu_command(menu_path, command_func)
            FileUtils.log_message(f"Plugin API: Registered Menu Command '{menu_path}'.")
        else:
            FileUtils.log_warning(f"Plugin API: Cannot register Menu Command '{menu_path}' outside Editor mode.")

    def log(self, message: str, level: str = "INFO"):
        """Logs a message from the plugin to the engine console/log file."""
        FileUtils.log_message(f"[Plugin] {message}", level)
        
    def get_state(self):
        """Returns the central EngineState object for direct manipulation (use with caution)."""
        return self.state


# --- Plugin Manager Core ---

class PluginManager:
    """
    Manages loading, initializing, and unloading of engine plugins (Python files).
    """

    def __init__(self, state: EngineState):
        self.state = state
        self.state.plugin_manager = self
        self.loaded_plugins = {} # {plugin_id: {'module': module, 'metadata': {...}}}
        self.plugin_api = PluginAPI(state)
        
        # Paths to search for plugin files (from EngineConfig)
        self.plugin_directories = state.config.editor_settings.get('plugin_dirs', [])
        
        self.scan_for_plugins() # Initial scan

    def scan_for_plugins(self):
        """Scans the plugin directories for potential plugin files (.py)."""
        all_plugin_files = {} # {filename: path}
        
        for directory in self.plugin_directories:
            if not os.path.isdir(directory):
                FileUtils.log_warning(f"Plugin directory not found: {directory}")
                continue
                
            for filename in os.listdir(directory):
                if filename.endswith(".py") and filename != "__init__.py":
                    plugin_id = os.path.splitext(filename)[0]
                    full_path = os.path.join(directory, filename)
                    # Check for companion JSON metadata file
                    metadata_path = os.path.join(directory, plugin_id + ".json")
                    metadata = FileUtils.read_json(metadata_path) if os.path.exists(metadata_path) else {}
                    
                    all_plugin_files[plugin_id] = {
                        'path': full_path,
                        'filename': filename,
                        'metadata': metadata
                    }

        self.available_plugins = all_plugin_files
        FileUtils.log_message(f"Found {len(self.available_plugins)} available plugins.")
        
        # Auto-load plugins marked for autoload
        for plugin_id, data in self.available_plugins.items():
            if data['metadata'].get('autoload', False) and plugin_id not in self.loaded_plugins:
                self.load_plugin(plugin_id)

    def load_plugin(self, plugin_id: str):
        """Loads and initializes a plugin module by ID."""
        if plugin_id in self.loaded_plugins:
            FileUtils.log_warning(f"Plugin '{plugin_id}' is already loaded.")
            return True

        plugin_info = self.available_plugins.get(plugin_id)
        if not plugin_info:
            FileUtils.log_error(f"Plugin '{plugin_id}' not found in available list.")
            return False

        path = plugin_info['path']
        module_name = f"plugin_{plugin_id}" # Use a unique module name
        
        try:
            # Dynamically load the module
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Check for and run the mandatory 'init' function
            if hasattr(module, 'init') and callable(module.init):
                # Pass the PluginAPI instance to the init function
                module.init(self.plugin_api)
                
                self.loaded_plugins[plugin_id] = {
                    'module': module,
                    'metadata': plugin_info['metadata'],
                    'path': path
                }
                FileUtils.log_message(f"Plugin '{plugin_id}' loaded and initialized successfully.")
                return True
            else:
                FileUtils.log_error(f"Plugin '{plugin_id}' missing mandatory 'init(api)' function.")
                # Unload the module from sys.modules to clean up
                del sys.modules[module_name]
                return False

        except Exception as e:
            FileUtils.log_error(f"Failed to load or initialize plugin '{plugin_id}' from {path}: {e}")
            return False

    def unload_plugin(self, plugin_id: str):
        """Unloads a plugin and cleans up its module."""
        if plugin_id not in self.loaded_plugins:
            FileUtils.log_warning(f"Plugin '{plugin_id}' is not loaded.")
            return False

        plugin_data = self.loaded_plugins[plugin_id]
        module = plugin_data['module']
        module_name = module.__name__
        
        try:
            # 1. Run mandatory 'cleanup' function (if available)
            if hasattr(module, 'cleanup') and callable(module.cleanup):
                module.cleanup(self.plugin_api)
                
            # 2. Unregister components/panels/commands (NOTE: EditorUI/ScriptEngine needs an unregister API)
            # For simplicity here, we rely on the component manager's internal cleanup 
            # or the component being removed from the scene.
            
            # 3. Remove from loaded list and sys.modules
            del self.loaded_plugins[plugin_id]
            if module_name in sys.modules:
                del sys.modules[module_name]
                
            FileUtils.log_message(f"Plugin '{plugin_id}' unloaded successfully.")
            return True
            
        except Exception as e:
            FileUtils.log_error(f"Error during cleanup/unloading of plugin '{plugin_id}': {e}")
            return False
            
    def get_plugin_list(self):
        """Returns a combined list of available and loaded plugins."""
        plugins = copy.deepcopy(self.available_plugins)
        for plugin_id, data in plugins.items():
            data['is_loaded'] = plugin_id in self.loaded_plugins
            data['version'] = data['metadata'].get('version', 'N/A')
            data['author'] = data['metadata'].get('author', 'Unknown')
        return plugins