# engine/scripting/script_engine.py
import pygame
import sys
import os
import importlib.util
from typing import Dict, Any, Callable, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.scene_manager import Scene, SceneObject
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.utils.vector3 import Vector3
    from engine.utils.timer import Timer
    from engine.utils.math_utils import MathUtils
    from engine.utils.color import Color
except ImportError as e:
    print(f"[ScriptEngine Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class Scene: 
        def get_all_objects(self): return []
    class SceneObject:
        def __init__(self, uid): self.uid = uid
        def get_component(self, type): return None
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[SE-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[SE-ERROR] {msg}", file=sys.stderr)
    class Vector2: pass
    class Vector3: pass
    class Timer: pass
    class MathUtils: pass
    class Color: pass


# --- Sandbox Context Injection ---

class ScriptSandbox:
    """
    A class that represents the environment available to user scripts.
    It links the script object (self) to the engine state and utility functions.
    """
    def __init__(self, scene_object: SceneObject, state: EngineState):
        
        # Public properties copied from SceneObject
        self.uid = scene_object.uid
        self.name = scene_object.name
        self.is_3d = scene_object.is_3d
        self.position = scene_object.position
        self.rotation = scene_object.rotation
        self.scale = scene_object.scale
        self.components = scene_object.components # Full list for advanced access

        # Read-only access to engine state and utilities
        self._state = state
        self.utils = state.utils # References the populated utility dict (Vector2, Timer, etc.)

        # Direct access to Managers (for convenience)
        self.input_manager = state.input_manager
        self.audio_manager = state.audio_manager
        self.particle_manager = state.particle_manager
        self.game_manager = state.game_manager
        
    @property
    def state(self):
        """Read-only access to the full EngineState (use with caution)."""
        return self._state

    def get_component(self, component_type: str) -> dict | None:
        """Helper to get a component dictionary from the SceneObject."""
        # Find the actual SceneObject to call its method
        obj = self.state.get_object_by_uid(self.uid)
        return obj.get_component(component_type) if obj else None
        
    def find_object(self, name_or_uid: str) -> ['ScriptSandbox']:
        """Finds another object in the scene and returns its ScriptSandbox instance."""
        target_obj = self.state.get_object_by_uid(name_or_uid) # Assumes UID search first
        if not target_obj and self.state.current_scene:
            # Simple linear search by name (inefficient but simple)
            for obj in self.state.current_scene.get_all_objects():
                if obj.name == name_or_uid:
                    target_obj = obj
                    break

        if target_obj:
            # NOTE: This creates a new sandbox instance; actual ScriptEngine manages cached execution instances
            # We return a lightweight wrapper that exposes only essential properties/methods
            return ScriptSandbox(target_obj, self.state) 
        return None

# --- Custom Component System Definition ---
class CustomComponent:
    def __init__(self, name: str, init_func: Callable, update_func: Callable, schema: Dict):
        self.name = name
        self.init = init_func
        self.update = update_func
        self.schema = schema
        
# --- Script Engine Core ---

class ScriptEngine:
    """
    Manages the loading, execution, and sandboxing of Python script components.
    """
    
    # Cache for loaded script modules and instantiated class objects
    _module_cache: Dict[str, Any] = {}          # {file_path: module_object}
    _instance_cache: Dict[str, ScriptSandbox] = {} # {scene_object_uid: script_sandbox_instance}
    _component_registry: Dict[str, CustomComponent] = {} # {type: CustomComponent}

    def __init__(self, state: EngineState):
        self.state = state
        self.state.script_engine = self
        
        self._populate_utility_references()
        self._register_default_components()
        
        FileUtils.log_message("ScriptEngine initialized.")

    def _populate_utility_references(self):
        """Populates the state's utility dictionary for script access."""
        self.state.utils['Vector2'] = Vector2
        self.state.utils['Vector3'] = Vector3
        self.state.utils['Timer'] = Timer
        self.state.utils['MathUtils'] = MathUtils
        self.state.utils['Color'] = Color
        # Add a reference to the script engine itself (for advanced scripts)
        self.state.utils['ScriptEngine'] = self

    def _register_default_components(self):
        """Registers all built-in components (Rigidbody, Renderer, etc.) for schema lookup."""
        # Note: Actual definition of these is in their respective files, we just register them here
        from engine.physics.rigidbody2d import Rigidbody2D
        from engine.physics.rigidbody3d import Rigidbody3D
        
        # Mock registration for the built-in ones (they don't need init/update functions here)
        self._component_registry["Rigidbody2D"] = CustomComponent("Rigidbody2D", None, None, Rigidbody2D.get_schema())
        self._component_registry["Rigidbody3D"] = CustomComponent("Rigidbody3D", None, None, Rigidbody3D.get_schema())
        # We need a proper Script component schema for ScriptEngine to work.
        self._component_registry["Script"] = CustomComponent("Script", None, None, self._get_script_component_schema())
        # Add other built-in components as needed...

    def _get_script_component_schema(self):
        """Schema for the built-in Script component."""
        return {
             "file": {"type": "asset_selector", "asset_type": "script", "label": "Script File"},
             "enabled": {"type": "boolean", "label": "Enabled", "default": True}
        }
        
    def register_custom_component(self, name: str, init_func: Callable, update_func: Callable, schema: Dict):
        """Called by plugins to register new component types."""
        if name in self._component_registry:
            FileUtils.log_warning(f"Component '{name}' already registered. Overwriting.")
        
        self._component_registry[name] = CustomComponent(name, init_func, update_func, schema)
        FileUtils.log_message(f"Registered custom component: {name}")

    def load_script_module(self, script_file_path: str):
        """
        Loads a Python file as a module into the cache.
        The file path is relative to the project root.
        """
        full_path = FileUtils.get_project_file_path(script_file_path, self.state.current_project_path)
        
        if full_path in self._module_cache:
            return self._module_cache[full_path]

        if not os.path.exists(full_path):
            FileUtils.log_error(f"Script file not found: {full_path}")
            return None

        # Use a unique module name based on path to prevent conflicts
        module_name = f"script_{os.path.basename(full_path).replace('.', '_')}_{hash(full_path)}"
        
        try:
            # Dynamically load the module
            spec = importlib.util.spec_from_file_location(module_name, full_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            self._module_cache[full_path] = module
            return module
            
        except Exception as e:
            FileUtils.log_error(f"Failed to load script module {full_path}: {e}")
            return None

    def initialize_all_scripts(self, scene: Scene):
        """Initializes all scripts attached to objects in the scene."""
        self._instance_cache.clear() # Clear old instances
        
        for obj in scene.get_all_objects():
            script_comp = obj.get_component("Script")
            if script_comp and script_comp.get("enabled", True):
                script_file = script_comp.get("file")
                if script_file:
                    self._initialize_script_instance(obj, script_file)

    def _initialize_script_instance(self, obj: SceneObject, script_file: str):
        """Loads the module, instantiates the sandbox, and calls the 'init' function."""
        
        module = self.load_script_module(script_file)
        if not module: return
        
        # 1. Create Sandbox (Script Context)
        sandbox = ScriptSandbox(obj, self.state)
        
        # 2. Add Sandbox to Cache
        self._instance_cache[obj.uid] = sandbox
        
        # 3. Call the mandatory 'init' function in the module, passing the sandbox as 'self'
        if hasattr(module, 'init') and callable(module.init):
            try:
                module.init(sandbox)
            except Exception as e:
                FileUtils.log_error(f"Error in init() for script {script_file} on object {obj.name}: {e}")


    def execute_script_update(self, obj: SceneObject, script_file: str, dt: float):
        """Executes the 'update' function for a script instance."""
        
        script_comp = obj.get_component("Script")
        if not script_comp or not script_comp.get("enabled", True):
            return

        # Ensure instance is initialized
        sandbox = self._instance_cache.get(obj.uid)
        if not sandbox:
            self._initialize_script_instance(obj, script_file)
            sandbox = self._instance_cache.get(obj.uid)
            if not sandbox: return

        # Load the module (from cache)
        full_path = FileUtils.get_project_file_path(script_file, self.state.current_project_path)
        module = self._module_cache.get(full_path)
        if not module: return
        
        # Call the mandatory 'update' function
        if hasattr(module, 'update') and callable(module.update):
            try:
                # Update the sandbox properties from the SceneObject before execution
                sandbox.position = obj.position
                sandbox.rotation = obj.rotation
                sandbox.scale = obj.scale
                
                module.update(sandbox, dt)
                
                # Update SceneObject state from Sandbox (allows script to change transform)
                obj.position = sandbox.position
                obj.rotation = sandbox.rotation
                obj.scale = sandbox.scale

            except Exception as e:
                FileUtils.log_error(f"Error in update() for script {script_file} on object {obj.name}: {e}")
                # Disable script to prevent continuous crashing
                script_comp["enabled"] = False
                FileUtils.log_message(f"Script {script_file} disabled due to critical error.")


    def cleanup_all_scripts(self, scene: Scene):
        """Calls the optional 'cleanup' function on all script instances."""
        for uid, sandbox in self._instance_cache.items():
            # Get the module path from the original component
            obj = scene.get_object(uid)
            if obj:
                script_comp = obj.get_component("Script")
                if script_comp:
                    script_file = script_comp.get("file")
                    full_path = FileUtils.get_project_file_path(script_file, self.state.current_project_path)
                    module = self._module_cache.get(full_path)
                    
                    if module and hasattr(module, 'cleanup') and callable(module.cleanup):
                        try:
                            module.cleanup(sandbox)
                        except Exception as e:
                            FileUtils.log_error(f"Error in cleanup() for script {script_file} on object {obj.name}: {e}")

        self._instance_cache.clear()
        # NOTE: Modules are intentionally *not* removed from sys.modules or _module_cache
        # to allow quick restart/hot-reloading in the editor.