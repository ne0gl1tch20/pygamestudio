# engine/templates/template_2d_topdown.py
import uuid
import sys
import os
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.vector2 import Vector2
    from engine.utils.color import Color
    from engine.utils.file_utils import FileUtils
    from engine.managers.behavior_tree_manager import BehaviorTreeManager # Check for BTM dependency
except ImportError as e:
    print(f"[Template Import Error] {e}. Using Internal Mocks.")
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = x, y
        def to_tuple(self): return (self.x, self.y)
    class Color:
        @staticmethod
        def blue(): return (0, 0, 255)
        @staticmethod
        def red(): return (255, 0, 0)
        def to_rgb(self): return (self.r, self.g, self.b)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[T2DT-INFO] {msg}")
        @staticmethod
        def write_text(path, content): pass
        @staticmethod
        def write_json(path, data): pass
        @staticmethod
        def create_dirs_if_not_exist(path): os.makedirs(path, exist_ok=True)
        @staticmethod
        def get_engine_root_path(): return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    HAS_PYGAME = False

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

def get_topdown_template_data() -> Dict[str, Any]:
    """
    Generates a complete, minimal scene data structure for a 2D Top-Down game.
    Includes a Player, an AI NPC with a BehaviorTree, and a basic environment.
    """
    
    # Define a reusable script for the player logic
    player_script_content = """
# Script: player_topdown_controller.py
# Attached to the Player object.

def init(self):
    self.speed = 150 # Pixels per second
    print(f"TopDown Player initialized: {self.name}")

def update(self, dt):
    input_manager = self.input_manager
    
    # Basic WASD movement
    velocity = self.utils.Vector2(0, 0)
    
    if input_manager.get_key('w'):
        velocity.y -= 1
    if input_manager.get_key('s'):
        velocity.y += 1
    if input_manager.get_key('a'):
        velocity.x -= 1
    if input_manager.get_key('d'):
        velocity.x += 1
        
    # Normalize and apply movement
    if velocity.magnitude > 0:
        velocity = velocity.normalize() * self.speed * dt
        self.position += velocity
"""

    scene_is_3d = False
    
    scene_data = {
        "name": "TopDown_Scene",
        "is_3d": scene_is_3d,
        "scene_properties": {
            "gravity": [0, 0], # Top-down has no gravity
            "background_color": Color(50, 100, 50).to_rgb() # Green floor/grass
        },
        "scripts": {
            "player_topdown_controller.py": player_script_content
        },
        "objects": [
            # 1. Player Character (UID P1001 for AI targeting)
            {
                "uid": "P1001",
                "name": "Player",
                "type": "sprite",
                "position": [50, 50],
                "scale": [1.0, 1.0],
                "rotation": 0,
                "components": [
                    {"type": "Rigidbody2D", "mass": 1.0, "is_dynamic": False, "is_kinematic": True}, # Kinematic body
                    {"type": "BoxCollider2D", "width": 32, "height": 32, "offset": [0, 0]},
                    {"type": "SpriteRenderer", "asset": "player_topdown.png", "layer": 10},
                    {"type": "Script", "file": "player_topdown_controller.py", "enabled": True}
                ]
            },
            # 2. AI NPC (Behavior Tree Demo)
            {
                "uid": "NPC001",
                "name": "EnemyGuard",
                "type": "sprite",
                "position": [-100, 50],
                "scale": [1.0, 1.0],
                "rotation": 0,
                "components": [
                    {"type": "Rigidbody2D", "mass": 1.0, "is_dynamic": True}, # Dynamic body for movement
                    {"type": "BoxCollider2D", "width": 32, "height": 32, "offset": [0, 0]},
                    {"type": "SpriteRenderer", "asset": "enemy_topdown.png", "layer": 10},
                    # Behavior Tree Component (references the tree in BTM)
                    {"type": "BehaviorTree", "tree_name": "DefaultAI"}, 
                    # State storage component (used by the BTM tasks)
                    {"type": "AIBTState", "target_x": -100, "move_dir": 1} 
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
                    {"type": "CameraComponent", "is_active": True, "projection": "orthographic", "target_uid": "P1001", "follow_speed": 4.0, "zoom": 1.0}
                ]
            }
        ]
    }
    
    return scene_data


def create_project(project_path: str, game_manager):
    """
    The function called by the Editor/Template Manager to generate the project files.
    """
    
    template_data = get_topdown_template_data()
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
# Automatically generated entry script from 2D Top-Down Template.

def start_game(game_manager):
    print("--- 2D Top-Down Game Start (AI Demo) ---")
    return {scene_data} 

def update_game(game_manager, dt):
    # This loop is where global game state logic would be executed.
    # AI/Physics are run automatically by the EngineRuntime.
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

    # 6. Mock Assets
    try:
        if HAS_PYGAME:
            img_dir = os.path.join(assets_dir, 'images')
            FileUtils.create_dirs_if_not_exist(img_dir)
            
            # Player image (blue circle)
            player_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(player_surf, Color.blue().to_rgb(), (16, 16), 16)
            pygame.image.save(player_surf, os.path.join(img_dir, 'player_topdown.png'))
            
            # Enemy image (red square)
            enemy_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
            enemy_surf.fill(Color.red().to_rgb())
            pygame.image.save(enemy_surf, os.path.join(img_dir, 'enemy_topdown.png'))
            
    except Exception as e:
        print(f"Warning: Failed to create mock Pygame assets: {e}")

    FileUtils.log_message(f"2D Top-Down Template created in {project_path}")
    return True