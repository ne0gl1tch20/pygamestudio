# engine/templates/template_3d_fps.py
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
    from engine.rendering.mesh_loader import MockPygame3DMesh
    from engine.rendering.mesh_loader import MeshLoader # Assume MeshLoader is available for primitives
except ImportError as e:
    print(f"[Template Import Error] {e}. Using Internal Mocks.")
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = x, y, z
        def to_tuple(self): return (self.x, self.y, self.z)
    class Color:
        @staticmethod
        def gray(): return (128, 128, 128)
        @staticmethod
        def white(): return (255, 255, 255)
        def to_rgb(self): return (self.r, self.g, self.b)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[T3DFPS-INFO] {msg}")
        @staticmethod
        def write_text(path, content): pass
        @staticmethod
        def write_json(path, data): pass
        @staticmethod
        def create_dirs_if_not_exist(path): os.makedirs(path, exist_ok=True)
    class MockPygame3DMesh: # Define a mock mesh for generation
        def __init__(self, vertices=None, faces=None): self.vertices = vertices; self.faces = faces
    class MeshLoader:
        def __init__(self, state): pass
        def save_mesh_to_json(self, mesh, path): FileUtils.write_json(path, mesh.to_dict())
        def generate_primitive(self, name, type, **kwargs):
             # Simple cube mock for saving
             s = kwargs.get('size', 1.0) / 2.0
             vertices = [[-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s], [-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s]]
             faces = [[4, 5, 6], [4, 6, 7], [0, 3, 2], [0, 2, 1], [3, 7, 6], [3, 6, 2], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [4, 7, 3], [4, 3, 0]]
             return MockPygame3DMesh(vertices, faces)

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

def get_fps_template_data() -> Dict[str, Any]:
    """
    Generates a complete, minimal scene data structure for a 3D First-Person Shooter template.
    """
    
    # Define the FPS Player controller script (attached to the Camera/Player root)
    player_script_content = """
# Script: player_fps_controller.py
# Attached to the Player (Camera) object in 3D scene.

def init(self):
    self.speed = 4.0 # Units per second (m/s)
    self.jump_force = 5.0
    self.mouse_sensitivity = 0.2
    
    # Store Pitch (X-rotation) separately to clamp vertical look
    self.pitch = 0.0 
    print(f"FPS Player Controller initialized for {self.name}.")

def update(self, dt):
    input_manager = self.input_manager
    
    # --- 1. Rotational Input (Mouse Look) ---
    
    # Only process mouse delta if the viewport is focused/not consumed by UI
    # In runtime, we assume focus. In editor, we check.
    if self.state.is_editor_mode:
        # NOTE: Editor logic for locking mouse would be here.
        pass 
        
    mouse_dx, mouse_dy = input_manager.get_mouse_delta()
    
    # Yaw (Y-rotation, horizontal look) - applied directly to object rotation
    yaw_delta = -mouse_dx * self.mouse_sensitivity
    self.rotation.y += yaw_delta
    
    # Pitch (X-rotation, vertical look) - clamped
    pitch_delta = -mouse_dy * self.mouse_sensitivity
    self.pitch += pitch_delta
    self.pitch = self.utils.MathUtils.clamp(self.pitch, -89.0, 89.0)
    self.rotation.x = self.pitch # Update scene object's X-rotation
    
    # --- 2. Linear Movement (WASD) ---
    
    # Calculate movement direction vectors (relative to object's rotation)
    # This requires converting Yaw to a forward/right vector.
    
    # Calculate horizontal direction vector from Yaw (Y-rotation)
    yaw_rad = self.utils.MathUtils.deg_to_rad(self.rotation.y)
    
    forward_x = -math.sin(yaw_rad)
    forward_z = math.cos(yaw_rad)
    
    right_x = math.cos(yaw_rad)
    right_z = math.sin(yaw_rad)
    
    move_dir = self.utils.Vector3.zero()
    
    if input_manager.get_key('w'): # Forward
        move_dir.x += forward_x
        move_dir.z += forward_z
    if input_manager.get_key('s'): # Backward
        move_dir.x -= forward_x
        move_dir.z -= forward_z
    if input_manager.get_key('a'): # Left
        move_dir.x -= right_x
        move_dir.z -= right_z
    if input_manager.get_key('d'): # Right
        move_dir.x += right_x
        move_dir.z += right_z
        
    # Normalize movement vector and apply speed/dt
    if move_dir.magnitude > 0:
        move_dir = move_dir.normalize() * self.speed * dt
        self.position += move_dir
        
    # --- 3. Jump (Mock Physics Interaction) ---
    rb_comp = self.get_component("Rigidbody3D")
    if rb_comp and input_manager.get_key_down('space'):
        # Mock application of vertical impulse
        # Assuming the physics system has an interface to set vertical velocity
        # obj = self.state.get_object_by_uid(self.uid)
        # if obj and self.state.physics_system_3d and obj in self.state.physics_system_3d.rigidbody_map:
        #      rb = self.state.physics_system_3d.rigidbody_map[obj]
        #      if rb.is_grounded:
        #           rb.velocity.y = self.jump_force
        #           rb.is_grounded = False
        
        # Simple position manipulation mock for jumping if physics isn't linked
        self.position.y += self.jump_force * dt
"""

    scene_is_3d = True
    
    scene_data = {
        "name": "FPS_Scene",
        "is_3d": scene_is_3d,
        "scene_properties": {
            "gravity": [0, -9.8, 0], # Standard 3D gravity (Y-up convention)
            "ambient_light": [50, 50, 50]
        },
        "scripts": { 
            "player_fps_controller.py": player_script_content
        },
        "objects": [
            # 1. Player/Camera (The SceneObject holds the CameraComponent and FPS script)
            {
                "uid": "P1001",
                "name": "FPS_Player",
                "type": "camera",
                "position": [0, 1.8, 0], # Player standing height
                "rotation": [0, 0, 0],
                "scale": [1.0, 1.0, 1.0],
                "components": [
                    # Dynamic rigidbody for physics interaction
                    {"type": "Rigidbody3D", "mass": 80.0, "restitution": 0.05, "is_dynamic": True}, 
                    # Capsule collider would be preferred for FPS, but we mock Box
                    {"type": "BoxCollider3D", "half_extents": [0.4, 0.9, 0.4]}, 
                    {"type": "CameraComponent", "is_active": True, "projection": "perspective", "fov": 75.0, "target_uid": None},
                    {"type": "Script", "file": "player_fps_controller.py", "enabled": True}
                ]
            },
            # 2. Ground Plane (Static)
            {
                "uid": "G2001",
                "name": "Ground",
                "type": "mesh",
                "position": [0, 0, 0],
                "rotation": [0, 0, 0],
                "scale": [10.0, 1.0, 10.0], # Scaled up Plane
                "components": [
                    {"type": "BoxCollider3D", "half_extents": [0.5, 0.01, 0.5]}, # Very thin collider
                    {"type": "MeshRenderer", "mesh_asset": "default_plane", "material_asset": "default_floor_mat"}
                    # Mesh asset 'default_plane' will be created below
                ]
            },
            # 3. Simple Box Obstacle
            {
                "uid": "OBSTACLE_01",
                "name": "Crate",
                "type": "mesh",
                "position": [5, 0.5, 3],
                "rotation": [0, 45, 0],
                "scale": [1.0, 1.0, 1.0],
                "components": [
                    {"type": "BoxCollider3D", "half_extents": [0.5, 0.5, 0.5]},
                    {"type": "MeshRenderer", "mesh_asset": "default_cube", "material_asset": "default_crate_mat"}
                ]
            }
        ]
    }
    
    return scene_data


def create_project(project_path: str, game_manager):
    """
    The function called by the Editor/Template Manager to generate the project files.
    """
    
    template_data = get_fps_template_data()
    scene_data = template_data.copy()
    scripts = template_data.pop("scripts")
    
    # 1. Create main project folder and subfolders
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
# Automatically generated entry script from 3D FPS Template.

def start_game(game_manager):
    print("--- 3D FPS Game Start ---")
    game_manager.state.config.set_setting('project_settings', 'is_3d_mode', True)
    # The Game Manager will load the scene from main_scene.json
    return {scene_data} 

def update_game(game_manager, dt):
    # Global game logic
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

    # 6. Generate Mock Mesh Assets (Cube and Plane)
    
    # Initialize a mock MeshLoader
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
    plane_mesh = mesh_loader.generate_primitive("default_plane", 'plane', size=2.0, segments=1) # Plane is 2x2 by default, scale handles the rest
    mesh_loader.save_mesh_to_json(plane_mesh, os.path.join(mesh_dir, 'default_plane.json'))

    # 7. Mock Material Assets (JSON definitions)
    floor_mat = {"name": "default_floor_mat", "shader_name": "default_lit", "color": [150, 150, 150], "roughness": 0.8}
    crate_mat = {"name": "default_crate_mat", "shader_name": "default_lit", "color": [180, 100, 50], "roughness": 0.5}

    FileUtils.write_json(os.path.join(material_dir, 'default_floor_mat.json'), floor_mat)
    FileUtils.write_json(os.path.join(material_dir, 'default_crate_mat.json'), crate_mat)


    FileUtils.log_message(f"3D FPS Template created in {project_path}")
    return True