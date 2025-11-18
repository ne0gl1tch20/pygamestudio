# engine/templates/template_2d_platformer.py
import uuid
import sys
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.vector2 import Vector2
    from engine.utils.color import Color
except ImportError as e:
    print(f"[Template Import Error] {e}. Using Internal Mocks.")
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = x, y
        def to_tuple(self): return (self.x, self.y)
    class Color:
        @staticmethod
        def gray(): return (128, 128, 128)
        @staticmethod
        def green(): return (0, 255, 0)
        def to_rgb(self): return (self.r, self.g, self.b)


def get_platformer_template_data() -> Dict[str, Any]:
    """
    Generates a complete, minimal scene data structure for a 2D Platformer game.
    """
    
    # Define a reusable script for the player logic
    player_script_content = """
# Script: player_platformer_controller.py
# Attached to the Player object.

def init(self):
    self.speed = 200 # Units per second
    self.jump_force = 450
    self.is_jumping = False
    print(f"Platformer Player initialized: {self.name}")

def update(self, dt):
    # Retrieve managers from the sandbox's state
    input_manager = self.input_manager
    rb_comp = self.get_component("Rigidbody2D")
    
    # We need the Rigidbody2D instance's velocity to manipulate it
    # NOTE: In a true script execution, the Rigidbody2D instance would be managed 
    # and exposed via the engine's physics system, but here we mock it by 
    # relying on the SceneObject's position and the physics system's integration.
    
    # Mocking physics interaction directly on SceneObject properties for this demo
    
    # Horizontal Movement
    move_x = 0
    if input_manager.get_key('a'):
        move_x -= 1
    if input_manager.get_key('d'):
        move_x += 1
        
    # Apply movement velocity (mocking horizontal control)
    # We directly manipulate the SceneObject's position for simple movement,
    # and the physics system will handle gravity/collisions.
    self.position.x += move_x * self.speed * dt
    
    # Jump (spacebar)
    # The Physics2D system should expose a property like rb_comp.is_grounded 
    # or the object itself should have it. Mocking a check against y > 100 for simplicity.
    is_grounded_mock = self.position.y >= 300 # See Physics2D.py floor mock
    
    if input_manager.get_key_down('space') and is_grounded_mock:
        # Mocking a vertical impulse/force application
        # To affect the Rigidbody2D velocity, we need a way to reference it.
        # In this mock, we assume the physics system looks for the velocity property
        # on the object itself or its associated Rigidbody2D instance.
        
        # NOTE: This requires the ScriptEngine Sandbox to have access to the 
        # actual Rigidbody2D instance or the SceneObject's state is directly used by physics.
        # Assuming the physics system tracks velocity internally:
        
        # Triggering a jump (we set a high temporary y-velocity)
        # Find the actual SceneObject to apply to its Rigidbody2D via engine state.
        obj = self.state.get_object_by_uid(self.uid)
        if obj and self.state.physics_system_2d and obj in self.state.physics_system_2d.rigidbody_map:
             rb = self.state.physics_system_2d.rigidbody_map[obj]
             rb.velocity.y = -self.jump_force # Y-up (negative is jump)
             rb.is_grounded = False # Clear grounded flag
             
        # Alternative: Directly manipulate the SceneObject's position 
        # (less physically accurate, but works for simpler games)
        # self.position.y -= self.jump_force * dt * 0.5 
        
        print("Jump attempted.")
"""

    scene_is_3d = False
    
    scene_data = {
        "name": "Platformer_Scene",
        "is_3d": scene_is_3d,
        "scene_properties": {
            "gravity": [0, 980.0], # Standard 2D gravity (pixels/sec^2, Y-down)
            "background_color": Color(50, 50, 100).to_rgb() # Dark blue sky
        },
        "scripts": { # A place to store project-level scripts
            "player_platformer_controller.py": player_script_content
        },
        "objects": [
            # 1. Player Character
            {
                "uid": "P1001",
                "name": "Player",
                "type": "sprite",
                "position": [0, 250], # Start above the ground mock (Y=300)
                "scale": [1.0, 1.0],
                "rotation": 0,
                "components": [
                    {"type": "Rigidbody2D", "mass": 5.0, "restitution": 0.1, "is_dynamic": True, "linear_damping": 0.05},
                    {"type": "BoxCollider2D", "width": 32, "height": 64, "offset": [0, 0]},
                    {"type": "SpriteRenderer", "asset": "player_idle.png", "layer": 10},
                    {"type": "Script", "file": "player_platformer_controller.py", "enabled": True}
                ]
            },
            # 2. Ground Platform (Static)
            {
                "uid": "G2001",
                "name": "Ground",
                "type": "sprite",
                "position": [0, 300], # Reference floor position in Physics2D mock
                "scale": [10.0, 1.0], # Long and flat
                "rotation": 0,
                "components": [
                    {"type": "BoxCollider2D", "width": 1000, "height": 32, "offset": [0, -16]},
                    {"type": "SpriteRenderer", "asset": "platform_base.png", "layer": 0}
                    # NOTE: No Rigidbody2D means it's static in Physics2D
                ]
            },
            # 3. Camera
            {
                "uid": "CAM_001",
                "name": "Main Camera",
                "type": "camera",
                "position": [0, 0],
                "rotation": 0,
                "components": [
                    {"type": "CameraComponent", "is_active": True, "projection": "orthographic", "target_uid": "P1001", "follow_speed": 4.0, "zoom": 1.5}
                ]
            }
        ]
    }
    
    # 4. Generate Mock Assets (Placeholder images/textures)
    # NOTE: In a full project run, the AssetLoader would create these mock assets 
    # when loading the scene. We just include the script content here.
    
    return scene_data

# NOTE: This file should contain a function that is called by the template selection in the Editor.
# We make it a standard entry point for template instantiation.
def create_project(project_path: str, game_manager):
    """
    The function called by the Editor/Template Manager to generate the project files.
    """
    
    template_data = get_platformer_template_data()
    scene_data = template_data.copy()
    scripts = template_data.pop("scripts")
    
    # 1. Create main project folder and subfolders
    FileUtils.create_dirs_if_not_exist(project_path)
    scripts_dir = os.path.join(project_path, 'scripts')
    assets_dir = os.path.join(project_path, 'assets')
    FileUtils.create_dirs_if_not_exist(scripts_dir)
    FileUtils.create_dirs_if_not_exist(assets_dir)

    # 2. Write Scripts
    for filename, content in scripts.items():
        FileUtils.write_text(os.path.join(scripts_dir, filename), content)
        
    # 3. Create main.py (Project entry point)
    main_py_content = f"""
# {os.path.basename(project_path)}/main.py
# Automatically generated entry script from 2D Platformer Template.

def start_game(game_manager):
    print("--- 2D Platformer Game Start ---")
    
    # Scene data for the template scene (used if scene file doesn't exist)
    # The actual scene data should be loaded from 'main_scene.json' by the manager.
    # We return the initial data for the GameManager to load if no scene file is present.
    
    # NOTE: Returning the data structure is safer than embedding the file path 
    # to avoid double loading/save issues during template creation.
    return {scene_data} 

def update_game(game_manager, dt):
    # Global game logic here (e.g., scoring, game state)
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

    # 6. Mock Assets (for AssetLoader)
    # Create simple placeholder image files in assets/images/
    try:
        if HAS_PYGAME:
            img_dir = os.path.join(assets_dir, 'images')
            FileUtils.create_dirs_if_not_exist(img_dir)
            
            # Player image (simple box)
            player_surf = pygame.Surface((32, 64), pygame.SRCALPHA)
            player_surf.fill(Color.green().to_rgb())
            pygame.image.save(player_surf, os.path.join(img_dir, 'player_idle.png'))
            
            # Platform image (simple gray block)
            platform_surf = pygame.Surface((100, 32), pygame.SRCALPHA)
            platform_surf.fill(Color.gray().to_rgb())
            pygame.image.save(platform_surf, os.path.join(img_dir, 'platform_base.png'))
            
    except Exception as e:
        print(f"Warning: Failed to create mock Pygame assets: {e}")

    FileUtils.log_message(f"2D Platformer Template created in {project_path}")
    return True

# Check for Pygame dependency
try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False