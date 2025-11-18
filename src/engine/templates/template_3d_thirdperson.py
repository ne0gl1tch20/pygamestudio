# engine/templates/template_3d_thirdperson.py
import uuid
import sys
import os
import math
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.vector3 import Vector3
    from engine.utils.color import Color
    from engine.utils.file_utils import FileUtils
    from engine.rendering.mesh_loader import MockPygame3DMesh, MeshLoader
    from engine.utils.math_utils import MathUtils
except ImportError as e:
    print(f"[Template Import Error] {e}. Using Internal Mocks.")
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = x, y, z
        def to_tuple(self): return (self.x, self.y, self.z)
        def __sub__(self, other): return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
        def __mul__(self, scalar): return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
        @property
        def magnitude(self): return (self.x**2 + self.y**2 + self.z**2)**0.5
        def normalize(self): return self * (1/self.magnitude if self.magnitude > 0 else 0)
    class Color:
        @staticmethod
        def gray(): return (128, 128, 128)
        @staticmethod
        def blue(): return (0, 0, 255)
        def to_rgb(self): return (self.r, self.g, self.b)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[T3DTP-INFO] {msg}")
        @staticmethod
        def write_text(path, content): pass
        @staticmethod
        def write_json(path, data): pass
        @staticmethod
        def create_dirs_if_not_exist(path): os.makedirs(path, exist_ok=True)
    class MockPygame3DMesh:
        def __init__(self, vertices=None, faces=None): self.vertices = vertices; self.faces = faces
        def to_dict(self): return {"vertices": self.vertices, "faces": self.faces}
    class MeshLoader:
        def __init__(self, state): pass
        def save_mesh_to_json(self, mesh, path): FileUtils.write_json(path, mesh.to_dict())
        def generate_primitive(self, name, type, **kwargs):
             s = kwargs.get('size', 1.0) / 2.0
             vertices = [[-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s], [-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s]]
             faces = [[4, 5, 6], [4, 6, 7], [0, 3, 2], [0, 2, 1], [3, 7, 6], [3, 6, 2], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [4, 7, 3], [4, 3, 0]]
             return MockPygame3DMesh(vertices, faces)
    class MathUtils:
        @staticmethod
        def deg_to_rad(deg): return deg * (math.pi / 180.0)
        @staticmethod
        def lerp(a, b, t): return a + (b - a) * t

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

def get_thirdperson_template_data() -> Dict[str, Any]:
    """
    Generates a complete, minimal scene data structure for a 3D Third-Person template.
    """
    
    # Player script for movement
    player_script_content = """
# Script: player_thirdperson_controller.py
# Attached to the Player mesh object.

def init(self):
    self.move_speed = 3.0 # Units per second (m/s)
    self.turn_speed = 180 # Degrees per second
    self.is_jumping = False
    
    # Reference to the camera object (assumed to be CAM_001)
    self.camera = self.find_object("Main Camera")
    print(f"Third-Person Player initialized: {self.name}")

def update(self, dt):
    input_manager = self.input_manager
    
    # --- 1. Movement Input ---
    
    move_dir = self.utils.Vector3.zero()
    
    if input_manager.get_key('w'): # Forward
        move_dir.z -= 1
    if input_manager.get_key('s'): # Backward
        move_dir.z += 1
    if input_manager.get_key('a'): # Left
        move_dir.x -= 1
    if input_manager.get_key('d'): # Right
        move_dir.x += 1
        
    # --- 2. Calculate Final Movement Vector (Relative to Camera View) ---
    
    if move_dir.magnitude > 0:
        move_dir = move_dir.normalize()
        
        # Get Camera's horizontal rotation (Yaw)
        cam_yaw = self.camera.rotation.y if self.camera else 0.0
        yaw_rad = self.utils.MathUtils.deg_to_rad(cam_yaw)
        
        # Calculate world-space forward/right vectors based on camera yaw
        forward_x = -math.sin(yaw_rad)
        forward_z = math.cos(yaw_rad)
        
        right_x = math.cos(yaw_rad)
        right_z = math.sin(yaw_rad)
        
        # Project local move_dir onto world space axes
        world_move_x = move_dir.x * right_x + move_dir.z * forward_x
        world_move_z = move_dir.x * right_z + move_dir.z * forward_z
        
        world_move_vec = self.utils.Vector3(world_move_x, 0.0, world_move_z).normalize()
        
        # Apply movement
        self.position += world_move_vec * self.move_speed * dt
        
        # --- 3. Rotation (Turn to Face Direction) ---
        
        # Calculate target rotation (Yaw angle)
        target_yaw_rad = math.atan2(-world_move_vec.x, world_move_vec.z) # atan2(forward_x, forward_z)
        target_yaw_deg = self.utils.MathUtils.rad_to_deg(target_yaw_rad)
        
        # Simple Lerp/smoothing for rotation
        current_yaw = self.rotation.y
        
        # Shortest path angle difference calculation (avoids spinning the long way)
        diff = target_yaw_deg - current_yaw
        if diff > 180: diff -= 360
        if diff < -180: diff += 360
        
        # Apply smooth rotation
        turn_amount = diff * 0.1 # Simple interpolation factor
        
        self.rotation.y += turn_amount
        
        
    # --- 4. Camera Follow Logic (Mocked, as CameraManager handles follow) ---
    # The CameraComponent attached to CAM_001 will handle the smooth follow/offset
"""

    # Camera script for orbiting/zooming
    camera_script_content = """
# Script: camera_thirdperson_orbit.py
# Attached to the Camera object.

def init(self):
    self.offset = self.utils.Vector3(0, 2, -5) # Default shoulder-view offset
    self.mouse_sensitivity = 0.2
    
    # Find the target object (Player)
    self.target = self.find_object("Player")
    
    # If using an explicit script for camera, CameraManager follow should be off
    camera_comp = self.get_component("CameraComponent")
    if camera_comp: camera_comp["target_uid"] = None 
    print(f"Third-Person Camera initialized.")

def update(self, dt):
    input_manager = self.input_manager
    
    # --- 1. Mouse Orbit (Horizontal rotation based on mouse delta) ---
    mouse_dx, mouse_dy = input_manager.get_mouse_delta()
    
    # Orbit the *target* based on mouse X (Yaw)
    yaw_delta = -mouse_dx * self.mouse_sensitivity
    self.target.rotation.y += yaw_delta # Rotate the player/target instead of the camera
    
    # Apply vertical look (Pitch) to the camera's X rotation
    pitch_delta = -mouse_dy * self.mouse_sensitivity
    self.rotation.x += pitch_delta
    self.rotation.x = self.utils.MathUtils.clamp(self.rotation.x, -45.0, 70.0) # Clamp vertical look
    
    # --- 2. Camera Placement ---
    
    if self.target:
        # NOTE: A real implementation would rotate the offset vector by the target's rotation.
        # We simplify: we rotate the target, and the camera is simply offset from it.
        
        # Camera is placed at target position + rotated offset
        
        # Simple rotation of the offset vector by target's Y rotation (Yaw)
        yaw_rad = self.utils.MathUtils.deg_to_rad(self.target.rotation.y)
        
        forward_x = -math.sin(yaw_rad)
        forward_z = math.cos(yaw_rad)
        
        right_x = math.cos(yaw_rad)
        right_z = math.sin(yaw_rad)
        
        # Rotated position (only using the Z-offset from the original local offset)
        rot_offset_x = self.offset.z * forward_x # Z-offset is the distance back
        rot_offset_z = self.offset.z * forward_z
        
        # Final position is target position + static vertical offset + rotated back offset
        target_pos = self.target.position
        new_pos = self.utils.Vector3(
            target_pos.x + rot_offset_x, 
            target_pos.y + self.offset.y, 
            target_pos.z + rot_offset_z
        )
        
        # Smoothly move to new position (to prevent jitter)
        t = 1.0 - math.exp(-6.0 * dt)
        self.position = self.position.lerp(new_pos, t)
        
        # Set camera rotation to look at the target (simplified)
        self.rotation.y = self.target.rotation.y # Match horizontal rotation
"""


    scene_is_3d = True
    
    scene_data = {
        "name": "ThirdPerson_Scene",
        "is_3d": scene_is_3d,
        "scene_properties": {
            "gravity": [0, -9.8, 0], 
            "ambient_light": [80, 80, 80]
        },
        "scripts": { 
            "player_thirdperson_controller.py": player_script_content,
            "camera_thirdperson_orbit.py": camera_script_content
        },
        "objects": [
            # 1. Player Character (Mesh Object P1001 for easy access)
            {
                "uid": "P1001",
                "name": "Player",
                "type": "mesh",
                "position": [0, 1.0, 0],
                "rotation": [0, 0, 0],
                "scale": [0.5, 2.0, 0.5], # Tall box for character
                "components": [
                    {"type": "Rigidbody3D", "mass": 80.0, "restitution": 0.0, "is_dynamic": True}, 
                    {"type": "BoxCollider3D", "half_extents": [0.25, 1.0, 0.25]}, 
                    {"type": "MeshRenderer", "mesh_asset": "default_cube", "material_asset": "default_player_mat"},
                    {"type": "Script", "file": "player_thirdperson_controller.py", "enabled": True}
                ]
            },
            # 2. Ground Plane (Static)
            {
                "uid": "G2001",
                "name": "Ground",
                "type": "mesh",
                "position": [0, 0, 0],
                "rotation": [0, 0, 0],
                "scale": [15.0, 1.0, 15.0],
                "components": [
                    {"type": "BoxCollider3D", "half_extents": [0.5, 0.01, 0.5]},
                    {"type": "MeshRenderer", "mesh_asset": "default_plane", "material_asset": "default_floor_mat"}
                ]
            },
            # 3. Camera (The SceneObject holds the CameraComponent and orbit script)
            {
                "uid": "CAM_001",
                "name": "Main Camera",
                "type": "camera",
                "position": [0, 2.0, -5.0], # Initial offset
                "rotation": [0, 0, 0],
                "components": [
                    {"type": "CameraComponent", "is_active": True, "projection": "perspective", "fov": 60.0, "target_uid": "P1001"}, # Target is set by script init, but default here
                    {"type": "Script", "file": "camera_thirdperson_orbit.py", "enabled": True}
                ]
            }
        ]
    }
    
    return scene_data


def create_project(project_path: str, game_manager):
    """
    The function called by the Editor/Template Manager to generate the project files.
    """
    
    template_data = get_thirdperson_template_data()
    scene_data = template_data.copy()
    scripts = template_data.pop("scripts")
    
    # 1. Create project folder structure
    FileUtils.create_dirs_if_not_exist(project_path)
    scripts_dir = os.path.join(project_path, 'scripts')
    assets_dir = os.path.join(project_path, 'assets')
    mesh_dir = os.path.join(assets_dir, 'meshes')
    material_dir = os.path.join(assets_dir, 'materials')
    FileUtils.create_dirs_if_not_exist(scripts_dir)
    FileUtils.create_dirs_if_not_exist(assets_dir)
    FileUtils.create_dirs_if_not_exist(mesh_dir)
    FileUtils.create_dirs_if_not_exist(material_dir)

    # 2. Write Scripts
    for filename, content in scripts.items():
        FileUtils.write_text(os.path.join(scripts_dir, filename), content)
        
    # 3. Create main.py (Project entry point)
    main_py_content = f"""
# {os.path.basename(project_path)}/main.py
# Automatically generated entry script from 3D Third-Person Template.

def start_game(game_manager):
    print("--- 3D Third-Person Game Start ---")
    game_manager.state.config.set_setting('project_settings', 'is_3d_mode', True)
    return {scene_data} 

def update_game(game_manager, dt):
    pass
"""
    FileUtils.write_text(os.path.join(project_path, 'main.py'), main_py_content)
    
    # 4. Create project.json
    project_json_content = {
        "name": os.path.basename(project_path),
        "main_scene": "main_scene.json",
        "is_3d": scene_is_3d,
        "assets_path": "assets/",
        "scripts_path": "scripts/",
        "startup_script": "main.py"
    }
    FileUtils.write_json(os.path.join(project_path, 'project.json'), project_json_content)

    # 5. Save initial scene data to main_scene.json
    FileUtils.write_json(os.path.join(project_path, project_json_content['main_scene']), scene_data)

    # 6. Generate Mock Mesh Assets
    class MockEngineState: # Minimal state to pass to MeshLoader
        def __init__(self): 
            self.asset_loader = None
            self.renderer_3d = None
    mock_state = MockEngineState()

    mesh_loader = MeshLoader(mock_state)
    
    # Save the Cube mesh JSON
    cube_mesh = mesh_loader.generate_primitive("default_cube", 'cube', size=1.0)
    mesh_loader.save_mesh_to_json(cube_mesh, os.path.join(mesh_dir, 'default_cube.json'))

    # Save the Plane mesh JSON
    plane_mesh = mesh_loader.generate_primitive("default_plane", 'plane', size=2.0, segments=1)
    mesh_loader.save_mesh_to_json(plane_mesh, os.path.join(mesh_dir, 'default_plane.json'))

    # 7. Mock Material Assets
    floor_mat = {"name": "default_floor_mat", "shader_name": "default_lit", "color": [150, 150, 150], "roughness": 0.8}
    player_mat = {"name": "default_player_mat", "shader_name": "default_lit", "color": [0, 100, 255], "roughness": 0.3}

    FileUtils.write_json(os.path.join(material_dir, 'default_floor_mat.json'), floor_mat)
    FileUtils.write_json(os.path.join(material_dir, 'default_player_mat.json'), player_mat)

    FileUtils.log_message(f"3D Third-Person Template created in {project_path}")
    return True