# engine/core/scene_manager.py
import json
import os
import uuid
import sys
import copy

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.utils.vector3 import Vector3
    from engine.utils.color import Color
    # Import mock/fallback for SceneObject/Camera until game_manager is written
    # We will define a minimal internal structure for Scene and SceneObject
    # as dependencies on game_manager are recursive.

except ImportError as e:
    print(f"[SceneManager Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[SM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[SM-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def read_json(path): return {}
        @staticmethod
        def write_json(path, data): pass
        @staticmethod
        def get_project_file_path(path): return path
        
    class Vector2:
        def __init__(self, x, y): self.x, self.y = x, y
        def __add__(self, other): return Vector2(self.x + other.x, self.y + other.y)
    class Vector3:
        def __init__(self, x, y, z): self.x, self.y, self.z = x, y, z
    class Color:
        def __init__(self, r, g, b): self.r, self.g, self.b = r, g, b
        
# --- Core Scene Data Structures ---

class SceneObject:
    """Represents a single GameObject in the scene."""
    def __init__(self, data: dict, is_3d: bool = False):
        self.uid = data.get("uid", str(uuid.uuid4()))
        self.name = data.get("name", "New Object")
        self.is_3d = is_3d
        
        # Transform data
        pos_data = data.get("position", [0, 0, 0] if is_3d else [0, 0])
        rot_data = data.get("rotation", [0, 0, 0] if is_3d else 0)
        scale_data = data.get("scale", [1, 1, 1] if is_3d else [1, 1])
        
        if is_3d:
            self.position = Vector3(*pos_data)
            self.rotation = Vector3(*rot_data)
            self.scale = Vector3(*scale_data)
        else:
            self.position = Vector2(*pos_data[:2])
            self.rotation = rot_data # Single float for 2D Z-rotation
            self.scale = Vector2(*scale_data[:2])
            
        # Component data (e.g., Rigidbody, Script, Renderer)
        self.components = data.get("components", []) 
        
        # Visuals (mock until asset_loader/renderer are fully linked)
        self.sprite = None 
        self.mesh = None

    def add_component(self, component_data: dict):
        """Adds a component dictionary to the object."""
        self.components.append(component_data)

    def get_component(self, component_type: str):
        """Retrieves the first component of a given type, or None."""
        return next((c for c in self.components if c.get('type') == component_type), None)
        
    def to_dict(self):
        """Converts the object state into a serializable dictionary."""
        d = {
            "uid": self.uid,
            "name": self.name,
            "type": "game_object", # Generic type for serialization
            "is_3d": self.is_3d,
            "position": list(self.position) if self.is_3d else self.position.to_tuple(),
            "rotation": list(self.rotation) if self.is_3d else self.rotation,
            "scale": list(self.scale) if self.is_3d else self.scale.to_tuple(),
            "components": copy.deepcopy(self.components)
        }
        return d

class Scene:
    """Represents the entire scene graph and scene-level properties."""
    def __init__(self, name: str, is_3d: bool = False):
        self.name = name
        self.is_3d = is_3d
        self._objects = {} # {uid: SceneObject}
        self.scene_properties = {} # E.g., ambient color, skybox, gravity setting

    def add_object(self, game_object: SceneObject):
        """Adds a SceneObject to the scene."""
        self._objects[game_object.uid] = game_object
        
    def remove_object(self, uid: str):
        """Removes a SceneObject by UID."""
        if uid in self._objects:
            del self._objects[uid]
            return True
        return False

    def get_object(self, uid: str) -> SceneObject | None:
        """Retrieves a SceneObject by UID."""
        return self._objects.get(uid)

    def get_all_objects(self) -> list[SceneObject]:
        """Returns a list of all SceneObjects."""
        return list(self._objects.values())
        
    def to_dict(self):
        """Converts the entire scene into a serializable dictionary."""
        return {
            "name": self.name,
            "is_3d": self.is_3d,
            "scene_properties": self.scene_properties,
            "objects": [obj.to_dict() for obj in self.get_all_objects()]
        }
        
# --- SceneManager Class ---

class SceneManager:
    """
    Manages loading, saving, and the lifecycle of Scene objects. 
    It interacts with FileUtils for disk operations.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.current_scene_file = None # Path to the currently loaded scene JSON

    def create_new_scene(self, name: str, is_3d: bool = False):
        """Creates a new, empty scene and sets it as the current scene."""
        new_scene = Scene(name, is_3d)
        self.state.current_scene = new_scene
        self.current_scene_file = None
        
        # Set default scene properties
        if is_3d:
            new_scene.scene_properties = {"gravity": [0, -9.8, 0], "ambient_light": [50, 50, 50]}
        else:
            new_scene.scene_properties = {"gravity": [0, 980], "background_color": Color(50, 50, 50).to_rgb()}

        # Add a default camera
        self.add_default_camera(new_scene)
        
        FileUtils.log_message(f"Created new scene: {name} (3D: {is_3d})")
        return new_scene

    def add_default_camera(self, scene: Scene):
        """Adds a default camera object to the scene."""
        cam_data = {
            "uid": "CAM_001",
            "name": "Main Camera",
            "type": "camera",
            "position": [0, 0, -10] if scene.is_3d else [0, 0],
            "rotation": [0, 0, 0] if scene.is_3d else 0,
            "components": [{"type": "CameraComponent", "is_active": True, "projection": "perspective" if scene.is_3d else "orthographic"}]
        }
        # Use a generic SceneObject for now, which the renderer/camera_manager will interpret
        default_camera = SceneObject(cam_data, scene.is_3d)
        scene.add_object(default_camera)
        
        # Inform the CameraManager if it exists
        if self.state.camera_manager:
            self.state.camera_manager.add_camera(default_camera)

    def load_scene(self, file_path: str):
        """Loads a scene from a JSON file path and sets it as current."""
        
        full_path = FileUtils.get_project_file_path(file_path, self.state.current_project_path)
        
        if not os.path.exists(full_path):
            FileUtils.log_error(f"Scene file not found: {full_path}")
            return False

        try:
            scene_data = FileUtils.read_json(full_path)
            
            # Basic validation
            if not scene_data or 'name' not in scene_data or 'objects' not in scene_data:
                FileUtils.log_error(f"Invalid scene file format: {full_path}")
                return False

            is_3d = scene_data.get("is_3d", False)
            new_scene = Scene(scene_data['name'], is_3d)
            new_scene.scene_properties = scene_data.get("scene_properties", {})

            # Instantiate objects
            for obj_data in scene_data['objects']:
                new_object = SceneObject(obj_data, is_3d)
                new_scene.add_object(new_object)

            self.state.current_scene = new_scene
            self.current_scene_file = full_path
            
            # Re-initialize camera manager with new cameras in scene
            if self.state.camera_manager:
                self.state.camera_manager.init_cameras(new_scene)
                
            # Re-initialize scripts
            if self.state.script_engine:
                self.state.script_engine.initialize_all_scripts(new_scene)

            FileUtils.log_message(f"Scene loaded successfully from: {full_path}")
            return True

        except Exception as e:
            FileUtils.log_error(f"Error loading scene file {full_path}: {e}")
            return False

    def save_scene(self, file_path: str = None):
        """Saves the current scene to a JSON file."""
        scene = self.state.current_scene
        if not scene:
            FileUtils.log_warning("Cannot save: No scene currently loaded.")
            return False

        save_path = file_path if file_path else self.current_scene_file
        if not save_path:
            # Cannot save if it's a new scene with no default path
            FileUtils.log_error("Cannot save: Scene has no associated file path. Use Save As...")
            return False
            
        full_path = FileUtils.get_project_file_path(save_path, self.state.current_project_path)

        try:
            scene_data = scene.to_dict()
            FileUtils.write_json(full_path, scene_data)
            self.current_scene_file = full_path # Update if Save As... was used
            FileUtils.log_message(f"Scene saved successfully to: {full_path}")
            return True
        except Exception as e:
            FileUtils.log_error(f"Error saving scene file {full_path}: {e}")
            return False
            
    def get_scene_object_schema(self):
        """Returns the schema for a SceneObject (for Inspector/UI validation)."""
        return {
            "uid": {"type": "string", "read_only": True},
            "name": {"type": "string", "label": "Name"},
            "is_3d": {"type": "boolean", "read_only": True},
            "position": {"type": "vector3" if self.state.current_scene and self.state.current_scene.is_3d else "vector2", "label": "Position"},
            "rotation": {"type": "vector3" if self.state.current_scene and self.state.current_scene.is_3d else "float", "label": "Rotation"},
            "scale": {"type": "vector3" if self.state.current_scene and self.state.current_scene.is_3d else "vector2", "label": "Scale"},
            "components": {"type": "list", "label": "Components", "read_only": True}
        }