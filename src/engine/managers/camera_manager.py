# engine/managers/camera_manager.py
import pygame
import sys
import copy
import math

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.scene_manager import SceneObject
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.utils.vector3 import Vector3
    from engine.utils.math_utils import MathUtils
except ImportError as e:
    print(f"[CameraManager Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[CM-INFO] {msg}")
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = x, y
        def __sub__(self, other): return Vector2(self.x - other.x, self.y - other.y)
        def to_tuple(self): return (self.x, self.y)
        def copy(self): return Vector2(self.x, self.y)
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = x, y, z
        def to_tuple(self): return (self.x, self.y, self.z)
    class MathUtils:
        @staticmethod
        def lerp(a, b, t): return a + (b - a) * t
    class SceneObject:
        def __init__(self, uid): self.uid = uid; self.position = Vector2(0, 0); self.is_3d = False
        def get_component(self, type): return {"is_active": True, "projection": "orthographic", "target_uid": None, "follow_speed": 1.0}


# --- Camera Data Structure (Represents the Camera SceneObject's state) ---

class CameraObject:
    """
    A unified representation of a Camera's essential state (position, rotation, zoom/FOV).
    It is tied to a SceneObject with a CameraComponent.
    """
    def __init__(self, scene_object: SceneObject):
        self.scene_object = scene_object
        self.is_3d = scene_object.is_3d
        
        # Position/Rotation (References the SceneObject's properties)
        self.position = scene_object.position
        self.rotation = scene_object.rotation
        
        # Camera-specific properties from component
        comp = scene_object.get_component("CameraComponent")
        self.is_active = comp.get("is_active", False)
        self.projection = comp.get("projection", "orthographic" if not self.is_3d else "perspective")
        self.follow_target_uid = comp.get("target_uid", None)
        self.follow_speed = comp.get("follow_speed", 1.0)
        
        # 2D Orthographic specific
        self.zoom = comp.get("zoom", 1.0) # 1.0 is default un-zoomed
        
        # 3D Perspective specific
        self.fov = comp.get("fov", 60.0) # Field of View (degrees)
        self.near_clip = comp.get("near_clip", 0.1)
        self.far_clip = comp.get("far_clip", 1000.0)


class CameraManager:
    """
    Manages all CameraObjects in the scene, determines the active camera, 
    and handles camera-specific updates (e.g., following a target).
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.state.camera_manager = self
        self.cameras: dict[str, CameraObject] = {} # {uid: CameraObject}
        self._active_camera_uid: str | None = None
        
        FileUtils.log_message("CameraManager initialized.")

    def init_cameras(self, scene):
        """Called when a new scene is loaded to discover and register all CameraObjects."""
        self.cameras.clear()
        self._active_camera_uid = None
        
        for obj in scene.get_all_objects():
            if obj.get_component("CameraComponent"):
                self.add_camera(obj)
                
        # Ensure at least one camera is active
        if not self._active_camera_uid and self.cameras:
            self._active_camera_uid = next(iter(self.cameras.keys()))
            self.cameras[self._active_camera_uid].is_active = True
            FileUtils.log_message(f"Set default active camera: {self._active_camera_uid}")

    def add_camera(self, scene_object: SceneObject):
        """Creates and registers a CameraObject from a SceneObject."""
        if scene_object.uid in self.cameras:
            return # Already registered
            
        camera = CameraObject(scene_object)
        self.cameras[camera.scene_object.uid] = camera
        
        if camera.is_active:
            self.set_active_camera(camera.scene_object.uid)

    def set_active_camera(self, uid: str):
        """Sets the camera with the given UID as the actively rendering camera."""
        if uid in self.cameras:
            # Deactivate all others
            for cam in self.cameras.values():
                cam.is_active = (cam.scene_object.uid == uid)
            self._active_camera_uid = uid
            FileUtils.log_message(f"Active camera set to: {uid}")
        else:
            FileUtils.log_error(f"Cannot set active camera: UID {uid} not found.")

    def get_active_camera(self) -> CameraObject | None:
        """Returns the currently active CameraObject."""
        return self.cameras.get(self._active_camera_uid)

    # --- Main Loop Method ---

    def update(self, dt: float, all_scene_objects: list[SceneObject]):
        """
        Updates the state of the active camera, primarily handling following targets.
        """
        active_camera = self.get_active_camera()
        if not active_camera:
            return

        # Handle 'Follow Target' logic
        if active_camera.follow_target_uid:
            target_obj = self.state.get_object_by_uid(active_camera.follow_target_uid)
            
            if target_obj:
                self._follow_target(active_camera, target_obj, dt)
            else:
                active_camera.follow_target_uid = None # Clear invalid target
                
        # Perform bounds checking or other post-processing (Mock: keep rotation clamped)
        if active_camera.is_3d:
            # Clamp 3D Euler angles to prevent gimbal lock artifacts for simplicity
            active_camera.rotation.x = MathUtils.clamp(active_camera.rotation.x, -89.0, 89.0)
            active_camera.rotation.y %= 360.0
        else:
            # Clamp 2D rotation
            active_camera.rotation %= 360.0

    def _follow_target(self, camera: CameraObject, target_obj: SceneObject, dt: float):
        """Smoothly moves the camera towards the target object's position."""
        
        target_pos = target_obj.position
        current_pos = camera.position
        
        # Determine the follow speed based on the component setting
        follow_speed = camera.follow_speed
        
        # Calculate the interpolation factor 't' for the lerp function
        # t = 1 - exp(-speed * dt) for framerate-independent exponential smoothing
        t = 1.0 - math.exp(-follow_speed * dt * 5.0) # 5.0 is a tuning factor
        
        # Perform Linear Interpolation (Lerp)
        if camera.is_3d:
            # Mock 3D position lerp
            new_pos_x = MathUtils.lerp(current_pos.x, target_pos.x, t)
            new_pos_y = MathUtils.lerp(current_pos.y, target_pos.y, t)
            new_pos_z = MathUtils.lerp(current_pos.z, target_pos.z, t)
            camera.position.x, camera.position.y, camera.position.z = new_pos_x, new_pos_y, new_pos_z
        else:
            # 2D position lerp
            new_pos_x = MathUtils.lerp(current_pos.x, target_pos.x, t)
            new_pos_y = MathUtils.lerp(current_pos.y, target_pos.y, t)
            camera.position.x, camera.position.y = new_pos_x, new_pos_y

        # NOTE: If target object has physics-based position, its new position is set 
        # *before* the camera update, making the follow smooth.

    # --- Editor/Inspector Schema ---
    
    @staticmethod
    def get_schema_2d():
        """Returns the schema for the 2D CameraComponent."""
        return {
            "is_active": {"type": "boolean", "label": "Active Camera"},
            "projection": {"type": "dropdown", "label": "Projection", "options": ["orthographic"], "read_only": True},
            "target_uid": {"type": "uid_selector", "label": "Follow Target (UID)"},
            "follow_speed": {"type": "float", "label": "Follow Speed", "min": 0.1, "max": 10.0},
            "zoom": {"type": "float", "label": "Zoom Level", "min": 0.05, "max": 5.0}
        }
        
    @staticmethod
    def get_schema_3d():
        """Returns the schema for the 3D CameraComponent."""
        return {
            "is_active": {"type": "boolean", "label": "Active Camera"},
            "projection": {"type": "dropdown", "label": "Projection", "options": ["perspective", "orthographic"], "read_only": True},
            "target_uid": {"type": "uid_selector", "label": "Follow Target (UID)"},
            "follow_speed": {"type": "float", "label": "Follow Speed", "min": 0.1, "max": 10.0},
            "fov": {"type": "float", "label": "Field of View", "min": 10.0, "max": 170.0},
            "near_clip": {"type": "float", "label": "Near Clip", "min": 0.01, "max": 10.0},
            "far_clip": {"type": "float", "label": "Far Clip", "min": 10.0, "max": 10000.0}
        }