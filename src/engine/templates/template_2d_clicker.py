# engine/templates/template_2d_clicker.py
import uuid
import sys
import os
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.vector2 import Vector2
    from engine.utils.color import Color
    from engine.utils.file_utils import FileUtils
    from engine.utils.timer import Timer
except ImportError as e:
    print(f"[Template Import Error] {e}. Using Internal Mocks.")
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = x, y
        def to_tuple(self): return (self.x, self.y)
    class Color:
        @staticmethod
        def yellow(): return (255, 255, 0)
        @staticmethod
        def white(): return (255, 255, 255)
        def to_rgb(self): return (self.r, self.g, self.b)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[T2DC-INFO] {msg}")
        @staticmethod
        def write_text(path, content): pass
        @staticmethod
        def write_json(path, data): pass
        @staticmethod
        def create_dirs_if_not_exist(path): os.makedirs(path, exist_ok=True)
    class Timer:
        def __init__(self, *args): pass

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

def get_clicker_template_data() -> Dict[str, Any]:
    """
    Generates a complete, minimal scene data structure for a 2D Clicker game.
    The player clicks a central object to increase a counter.
    """
    
    # Define the main game loop script
    main_game_script_content = """
# Script: game_state_manager.py
# Attached to a root-level manager object.

def init(self):
    self.score = 0
    self.click_value = 1
    self.auto_click_rate = 0.0 # Clicks per second
    self.auto_click_timer = self.utils.Timer(duration=1.0, is_looping=True)
    self.auto_click_timer.start()
    print(f"Clicker Game State initialized. Score: {self.score}")

def update(self, dt):
    # Auto-clicker logic
    if self.auto_click_rate > 0:
        # Scale the timer duration based on the rate
        self.auto_click_timer.duration = 1.0 / self.auto_click_rate 
        
        if self.auto_click_timer.check():
            self.score += self.click_value
            self.update_ui()

def on_object_clicked(self, obj_uid):
    \"""Called by the central object's click script.\"""
    if obj_uid == "CLICK_TARGET":
        self.score += self.click_value
        print(f"Clicked! New Score: {self.score}")
        self.update_ui()
        
def update_ui(self):
    \"""Mocks updating a UI element's text (e.g., a Label object).\"""
    score_label = self.find_object("ScoreLabel")
    if score_label:
        # Mocking how a script updates another object's component property
        label_comp = score_label.get_component("TextRenderer")
        if label_comp:
            label_comp['text'] = f"Score: {int(self.score)}"
"""

    # Define the click target script
    click_target_script_content = """
# Script: click_target_handler.py
# Attached to the central click target object.

def init(self):
    self.is_clicked = False

def update(self, dt):
    # Handle mouse click detection manually
    input_manager = self.input_manager
    mouse_pos = input_manager.get_mouse_pos()
    
    # Check if the object's screen rect is clicked
    # NOTE: In a true runtime, the Renderer would provide a screen-space AABB or rect
    # Mocking a simple check near the center of the screen
    is_clicked_this_frame = False
    if input_manager.get_mouse_button_down(1): # LMB
        if abs(mouse_pos[0] - 400) < 50 and abs(mouse_pos[1] - 300) < 50: # Mock area check
            is_clicked_this_frame = True
            
    if is_clicked_this_frame:
        # Inform the Game State Manager
        game_manager_obj = self.find_object("GameStateManager")
        if game_manager_obj and hasattr(game_manager_obj, 'on_object_clicked'):
            # Directly call the method on the manager's sandbox instance
            game_manager_obj.on_object_clicked(self.uid)
"""

    scene_is_3d = False
    
    scene_data = {
        "name": "Clicker_Scene",
        "is_3d": scene_is_3d,
        "scene_properties": {
            "gravity": [0, 0], 
            "background_color": Color(20, 20, 30).to_rgb() # Dark background
        },
        "scripts": {
            "game_state_manager.py": main_game_script_content,
            "click_target_handler.py": click_target_script_content
        },
        "objects": [
            # 1. Game State Manager (Invisible object to hold global script)
            {
                "uid": "STATE_MANAGER",
                "name": "GameStateManager",
                "type": "game_object",
                "position": [0, 0],
                "scale": [1, 1],
                "components": [
                    {"type": "Script", "file": "game_state_manager.py", "enabled": True}
                ]
            },
            # 2. Click Target
            {
                "uid": "CLICK_TARGET",
                "name": "ClickTarget",
                "type": "sprite",
                "position": [400, 300], # Centered on an 800x600 screen
                "scale": [1.0, 1.0],
                "rotation": 0,
                "components": [
                    {"type": "BoxCollider2D", "width": 100, "height": 100, "offset": [0, 0]},
                    {"type": "SpriteRenderer", "asset": "coin_icon.png", "layer": 5},
                    {"type": "Script", "file": "click_target_handler.py", "enabled": True}
                ]
            },
            # 3. Score Label (UI element)
            {
                "uid": "SCORE_LBL",
                "name": "ScoreLabel",
                "type": "ui_label",
                "position": [50, 50], # Top-left UI position (Screen Space Mock)
                "scale": [1, 1],
                "rotation": 0,
                "components": [
                    # Mock TextRenderer component for UI element
                    {"type": "TextRenderer", "text": "Score: 0", "font_size": 36, "color": [255, 255, 255]} 
                ]
            },
            # 4. Camera (Fixed)
            {
                "uid": "CAM_001",
                "name": "Main Camera",
                "type": "camera",
                "position": [400, 300], # Fixed position to center on 800x600 mock viewport
                "rotation": 0,
                "components": [
                    {"type": "CameraComponent", "is_active": True, "projection": "orthographic", "zoom": 1.0}
                ]
            }
        ]
    }
    
    return scene_data


def create_project(project_path: str, game_manager):
    """
    The function called by the Editor/Template Manager to generate the project files.
    """
    
    template_data = get_clicker_template_data()
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
# Automatically generated entry script from 2D Clicker Template.

def start_game(game_manager):
    print("--- 2D Clicker Game Start ---")
    game_manager.state.config.set_setting('project_settings', 'resolution_x', 800)
    game_manager.state.config.set_setting('project_settings', 'resolution_y', 600)
    return {scene_data} 

def update_game(game_manager, dt):
    # No global update logic needed, game logic is handled by scripts
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
            
            # Coin image (yellow circle)
            coin_surf = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(coin_surf, Color.yellow().to_rgb(), (50, 50), 45)
            pygame.image.save(coin_surf, os.path.join(img_dir, 'coin_icon.png'))
            
    except Exception as e:
        print(f"Warning: Failed to create mock Pygame assets: {e}")

    FileUtils.log_message(f"2D Clicker Template created in {project_path}")
    return True