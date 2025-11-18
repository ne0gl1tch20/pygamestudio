# editor/editor_scene.py
import pygame
import sys
import os
import json
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.scene_manager import Scene, SceneObject, SceneManager
    from engine.managers.camera_manager import CameraManager
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.utils.vector3 import Vector3
    from engine.utils.color import Color
except ImportError as e:
    print(f"[EditorScene Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def __init__(self): self.current_scene = self; self.scene_manager = self
    class Scene:
        def __init__(self, name): self.name = name; self.is_3d = False
        def get_all_objects(self): return []
    class SceneObject:
        def __init__(self, uid): self.uid = uid; self.name = "MockObj"
    class SceneManager:
        def create_new_scene(self, name, is_3d): return Scene(name)
        def load_scene(self, path): return True
        def save_scene(self, path): return True
    class CameraManager:
        def __init__(self, state): pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[ES-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[ES-ERROR] {msg}", file=sys.stderr)
    class Vector2:
        def __init__(self, x, y): self.x, self.y = x, y
    class Vector3:
        def __init__(self, x, y, z): self.x, self.y, self.z = x, y, z
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)


class EditorScene:
    """
    Acts as the bridge between the Editor UI/Viewports and the core SceneManager/EngineState.
    Handles high-level scene operations within the editor context.
    """

    def __init__(self, state: EngineState):
        self.state = state
        self.scene_manager: SceneManager = self.state.scene_manager
        
        FileUtils.log_message("EditorScene bridge initialized.")

    # --- Scene Lifecycle Operations ---
    
    def new_scene(self, name: str, is_3d: bool = False):
        """Creates a new, empty scene, handling all necessary manager resets."""
        
        if self.state.current_scene and self.state.current_scene.get_all_objects():
            # NOTE: In a real app, this should prompt the user to save changes.
            FileUtils.log_warning("Creating new scene without saving current one.")

        new_scene = self.scene_manager.create_new_scene(name, is_3d)
        
        # Reset editor-specific state
        self.state.selected_object_uid = None
        self.state.ui_state['active_viewport'] = '3D' if is_3d else '2D'
        
        return new_scene

    def load_scene(self, file_path: str):
        """Loads a scene from a specified file path."""
        
        if self.scene_manager.load_scene(file_path):
            # Update viewport to match scene type
            self.state.ui_state['active_viewport'] = '3D' if self.state.current_scene.is_3d else '2D'
            return True
        return False
        
    def save_scene(self, file_path: str = None):
        """Saves the current scene. Uses current file path if none is provided (Quick Save)."""
        return self.scene_manager.save_scene(file_path)

    # --- Object Manipulation (via Inspector/Viewport) ---

    def create_object(self, object_type: str, name: str = "New Object") -> SceneObject | None:
        """Adds a new object to the current scene based on a type/template."""
        if not self.state.current_scene:
            FileUtils.log_error("Cannot create object: No scene currently loaded.")
            return None
            
        is_3d = self.state.current_scene.is_3d
        
        # Simple default object data structure
        new_uid = str(uuid.uuid4())
        initial_pos = [0.0, 0.0, 0.0] if is_3d else [0.0, 0.0]
        initial_scale = [1.0, 1.0, 1.0] if is_3d else [1.0, 1.0]
        
        new_obj_data = {
            "uid": new_uid,
            "name": name,
            "type": object_type,
            "position": initial_pos,
            "rotation": [0.0, 0.0, 0.0] if is_3d else 0.0,
            "scale": initial_scale,
            "components": []
        }
        
        # Add default components based on type
        if object_type == "sprite" and not is_3d:
            new_obj_data["components"].append({"type": "SpriteRenderer", "asset": "default_sprite.png", "layer": 0})
            new_obj_data["components"].append({"type": "BoxCollider2D", "width": 32, "height": 32})
        elif object_type == "mesh" and is_3d:
            new_obj_data["components"].append({"type": "MeshRenderer", "mesh_asset": "default_cube", "material_asset": "default_lit"})
            new_obj_data["components"].append({"type": "BoxCollider3D", "half_extents": [0.5, 0.5, 0.5]})
            
        new_object = SceneObject(new_obj_data, is_3d)
        self.state.current_scene.add_object(new_object)
        self.state.selected_object_uid = new_uid
        
        # If it's a camera, register it with the CameraManager
        if object_type == "camera" and self.state.camera_manager:
            self.state.camera_manager.add_camera(new_object)

        FileUtils.log_message(f"Created new object: {name} ({object_type})")
        return new_object
        
    def delete_selected_object(self):
        """Deletes the currently selected object."""
        if self.state.selected_object_uid and self.state.current_scene:
            name = self.state.get_object_by_uid(self.state.selected_object_uid).name
            if self.state.current_scene.remove_object(self.state.selected_object_uid):
                FileUtils.log_message(f"Deleted object: {name}")
                self.state.selected_object_uid = None
                return True
        return False
        
    def duplicate_selected_object(self):
        """Creates a deep copy of the currently selected object."""
        selected_obj = self.state.get_object_by_uid(self.state.selected_object_uid)
        if not selected_obj or not self.state.current_scene: return None

        # Create a dictionary copy (deep copy is necessary for component data)
        obj_data = selected_obj.to_dict()
        
        # Modify unique properties
        new_uid = str(uuid.uuid4())
        obj_data["uid"] = new_uid
        obj_data["name"] = f"{selected_obj.name}_Copy"
        
        # Slightly offset position for visual confirmation
        offset_vec = Vector3(1, 1, 1) if selected_obj.is_3d else Vector2(10, 10)
        
        if selected_obj.is_3d:
            obj_data["position"][0] += offset_vec.x
            obj_data["position"][1] += offset_vec.y
            obj_data["position"][2] += offset_vec.z
        else:
            obj_data["position"][0] += offset_vec.x
            obj_data["position"][1] += offset_vec.y
            
        # Create and add the new object
        new_object = SceneObject(obj_data, selected_obj.is_3d)
        self.state.current_scene.add_object(new_object)
        self.state.selected_object_uid = new_uid
        
        FileUtils.log_message(f"Duplicated object: {new_object.name}")
        return new_object

    # --- Template Generation ---

    def instantiate_template(self, template_name: str, project_name: str):
        """
        Instantiates a full project from one of the predefined templates.
        This operation is typically handled by the GameManager and involves 
        creating new project files on disk.
        """
        
        # Locate the template function based on its name
        template_module_name = f"engine.templates.{template_name}"
        try:
            template_module = sys.modules[template_module_name]
        except KeyError:
            FileUtils.log_error(f"Template module '{template_name}' not found. Check imports.")
            return False

        if not hasattr(template_module, 'create_project'):
            FileUtils.log_error(f"Template '{template_name}' is missing the 'create_project' function.")
            return False
            
        # Determine target project path
        default_root = self.state.config.editor_settings.get('default_project_path', os.path.join(FileUtils.get_engine_root_path(), 'projects'))
        target_path = os.path.join(default_root, project_name)
        
        if os.path.exists(target_path):
             FileUtils.log_error(f"Project directory '{target_path}' already exists.")
             return False

        FileUtils.log_message(f"Instantiating template '{template_name}' into new project '{project_name}'...")
        
        # Call the template's creation function
        is_3d = template_name.startswith('template_3d') or template_name.startswith('template_proc_world') # Simple check
        if template_name.startswith('template_proc_world'):
            success = template_module.create_project(target_path, self.state.game_manager, is_3d=is_3d)
        else:
            success = template_module.create_project(target_path, self.state.game_manager)

        if success:
            # Load the newly created project immediately
            self.state.game_manager.load_project(target_path)
            return True
        
        return False