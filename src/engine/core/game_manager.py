# engine/core/game_manager.py
import pygame
import os
import sys
import importlib.util
import json

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from ..engine.core.engine_state import EngineState
    from ..engine.core.engine_runtime import EngineRuntime
    from ..engine.core.scene_manager import Scene
    from ..engine.managers.save_load_manager import SaveLoadManager
    from ..engine.utils.file_utils import FileUtils
    from ..engine.utils.vector2 import Vector2
    from ..engine.utils.vector3 import Vector3
except ImportError as e:
    print(f"[GameManager Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class EngineRuntime:
        def __init__(self, *args): pass
        def run(self, *args): pass
        def cleanup(self): pass
    class Scene: pass
    class SaveLoadManager:
        def __init__(self, *args): pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[GM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[GM-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def read_json(path): return {}
        @staticmethod
        def get_project_file_path(path, root): return os.path.join(root, path)

    class Vector2: pass
    class Vector3: pass


class GameManager:
    """
    Manages the overall project lifecycle, including loading the project,
    starting the game runtime, and handling project-level data persistence.
    
    This class acts as the main interface between the Editor (EditorMain) 
    and the Game Runtime (EngineRuntime).
    """

    def __init__(self, state: EngineState):
        self.state = state
        # Link the manager back to the state
        self.state.game_manager = self 
        self.is_game_running = False
        self.runtime_instance = None
        self.project_data = {} # Loaded data from project.json
        self.game_main_module = None # Reference to the project's main script module

    def load_project(self, project_path: str):
        """
        Loads a project from a specified directory path.
        This updates the engine state and project configuration.
        """
        if not project_path or not os.path.isdir(project_path):
            FileUtils.log_error(f"Invalid project path: {project_path}")
            return False

        project_json_path = os.path.join(project_path, 'project.json')
        if not os.path.exists(project_json_path):
            FileUtils.log_error(f"Project configuration file not found: {project_json_path}")
            return False

        try:
            self.project_data = FileUtils.read_json(project_json_path)
            
            # 1. Update Engine State
            self.state.current_project_path = project_path
            self.state.config.set_setting('editor_settings', 'last_opened_project', project_path)
            
            # 2. Update Project Settings in Config (for runtime)
            project_settings = self.project_data.get('settings', {})
            # Merge project settings into EngineConfig's project_settings
            current_proj_settings = self.state.config.project_settings
            current_proj_settings.update(project_settings)
            
            # Update 3D mode flag
            is_3d = self.project_data.get('is_3d', False)
            self.state.config.set_setting('project_settings', 'is_3d_mode', is_3d)

            # 3. Load Project's Main Script
            if 'startup_script' in self.project_data:
                script_path = os.path.join(project_path, self.project_data['startup_script'])
                self.game_main_module = self._load_script_module(script_path, "project_main_script")
            else:
                self.game_main_module = None
            
            # 4. Load Main Scene (if specified)
            if 'main_scene' in self.project_data and self.state.scene_manager:
                scene_file = os.path.join(project_path, self.project_data['main_scene'])
                if not self.state.scene_manager.load_scene(scene_file):
                    FileUtils.log_warning(f"Could not load main scene: {self.project_data['main_scene']}. Creating new empty scene.")
                    self.state.scene_manager.create_new_scene("Default Scene", is_3d)
            
            self.state.config.save_config() # Save last opened project
            FileUtils.log_message(f"Project '{self.project_data.get('name', 'Unnamed')}' loaded successfully.")
            return True

        except Exception as e:
            FileUtils.log_error(f"Error loading project from {project_path}: {e}")
            return False

    def _load_script_module(self, script_path, module_name):
        """Dynamically loads a Python file as a module."""
        if not os.path.exists(script_path):
            FileUtils.log_error(f"Project script not found: {script_path}")
            return None
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            FileUtils.log_message(f"Loaded project script module: {module_name}")
            return module
        except Exception as e:
            FileUtils.log_error(f"Failed to load project script {script_path}: {e}")
            return None

    def start_game(self, surface: pygame.Surface):
        """
        Initializes and runs the EngineRuntime loop.
        Used by the editor when the user presses 'Play'.
        """
        if self.is_game_running:
            FileUtils.log_warning("Game is already running.")
            return

        FileUtils.log_message("Starting Game Runtime...")
        self.is_game_running = True
        self.state.is_editor_mode = False
        self.state.is_running = True # Set state flag for runtime loop
        
        try:
            # 1. Instantiate and Configure Runtime
            self.runtime_instance = EngineRuntime(surface, self.state)

            # 2. Call Project's start_game function (if available)
            if self.game_main_module and hasattr(self.game_main_module, 'start_game'):
                scene_data = self.game_main_module.start_game(self)
                # If the project's start_game returns scene data, load it 
                # (overwriting the editor scene if necessary for game start)
                if isinstance(scene_data, dict) and self.state.scene_manager:
                    # In a real game build, the scene would be loaded directly from the build package.
                    # In the editor, this re-loads the scene based on the script's output.
                    # Simple load of scene data (must be converted to a proper Scene object by SceneManager)
                    # NOTE: SceneManager does not have a direct 'load_from_dict' function, so we bypass 
                    # by re-implementing scene creation on the fly, similar to scene_manager's code.
                    is_3d = self.state.config.project_settings.get("is_3d_mode", False)
                    from engine.core.scene_manager import Scene, SceneObject 
                    new_scene = Scene(scene_data.get('name', 'Runtime Scene'), is_3d)
                    for obj_data in scene_data.get('objects', []):
                        new_scene.add_object(SceneObject(obj_data, is_3d))
                    self.state.current_scene = new_scene
                    self.state.scene_manager.current_scene_file = None # Runtime scene is transient
                    
                    # Re-initialize cameras and scripts for the new scene
                    if self.state.camera_manager: self.state.camera_manager.init_cameras(new_scene)
                    if self.state.script_engine: self.state.script_engine.initialize_all_scripts(new_scene)
                
            # 3. Start the main game loop
            self.runtime_instance.run(self.game_main_module)

        except Exception as e:
            FileUtils.log_error(f"Critical error during Game Runtime execution: {e}")
            # Ensure runtime cleanup is called on crash
        finally:
            self._cleanup_runtime()

    def stop_game(self):
        """Stops the currently running EngineRuntime loop."""
        if not self.is_game_running:
            FileUtils.log_warning("Game is not running.")
            return

        FileUtils.log_message("Stopping Game Runtime...")
        self.state.is_running = False # Signal the runtime loop to exit

    def _cleanup_runtime(self):
        """Internal function to handle post-runtime cleanup."""
        if self.runtime_instance:
            self.runtime_instance.cleanup()
            self.runtime_instance = None
        
        self.is_game_running = False
        self.state.is_editor_mode = True # Return control to editor environment
        FileUtils.log_message("Game Runtime cleanup complete. Returning to Editor.")
        
    # --- Persistence Helpers (Delegates to SaveLoadManager) ---
    
    def save_project(self):
        """Saves current project state via SaveLoadManager."""
        if self.state.save_load_manager:
            return self.state.save_load_manager.save_full_project(self.state.current_project_path)
        FileUtils.log_error("SaveLoadManager not initialized.")
        return False
        
    def save_project_as(self, new_path):
        """Saves project to a new location via SaveLoadManager."""
        if self.state.save_load_manager:
            return self.state.save_load_manager.save_full_project(new_path, is_save_as=True)
        FileUtils.log_error("SaveLoadManager not initialized.")
        return False