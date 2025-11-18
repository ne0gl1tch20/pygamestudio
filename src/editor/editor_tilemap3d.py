# editor/editor_tilemap3d.py
import pygame
import sys
import os
import json
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.scene_manager import SceneObject
    from engine.managers.camera_manager import CameraObject
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector3 import Vector3
    from engine.utils.color import Color
    from engine.gui.gui_widgets import Window, Button, Label
except ImportError as e:
    print(f"[EditorTilemap3D Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
    class SceneObject:
        def __init__(self, uid): self.uid = uid; self.name = "MockTilemap3D"; self.components = [{"type": "VoxelGridRenderer"}]
        def get_component(self, type): return self.components[0]
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[ET3D-INFO] {msg}")
    class Vector3:
        def __init__(self, x, y, z): self.x, self.y, self.z = float(x), float(y), float(z)
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def get_content_rect(self): return self.rect
    class Button:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def handle_event(self, event): return False
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)


class EditorTilemap3D:
    """
    Specialized editor panel for visualizing and editing 3D tilemaps/voxel data.
    Allows for volumetric painting and voxel asset management.
    """
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Tilemap 3D Editor 🧊"):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=True, movable=True)
        self.rect = rect.copy()
        
        self.font = pygame.font.Font(None, 24)
        
        # State
        self.active_tilemap_uid = None
        self.selected_voxel_type = "stone" # Voxel asset/type to paint
        self.is_painting = False
        self.tilemap_obj: SceneObject | None = None
        self.voxel_data: Dict[str, Any] | None = None
        
        # UI Elements
        self.btn_generate = Button(pygame.Rect(0, 0, 200, 30), "Generate Voxel World (Mock)", action=self._generate_mock)
        self.btn_paint = Button(pygame.Rect(0, 0, 100, 30), "Voxel Paint", action=lambda: self._select_tool('paint'))
        self.btn_erase = Button(pygame.Rect(0, 0, 100, 30), "Voxel Erase", action=lambda: self._select_tool('erase'))
        self.current_tool = 'paint'
        
        self._update_ui_rects()

    def set_active_tilemap(self, tilemap_obj: SceneObject):
        """Sets the active 3D tilemap (e.g., a VoxelGrid component)."""
        comp = tilemap_obj.get_component("VoxelGridRenderer") # Mock component name
        if not comp:
             FileUtils.log_error(f"Object {tilemap_obj.name} does not have a VoxelGridRenderer.")
             return
             
        self.active_tilemap_uid = tilemap_obj.uid
        self.tilemap_obj = tilemap_obj
        # Mock Voxel Data Structure
        self.voxel_data = comp.get("voxel_grid_data", {"width": 16, "height": 16, "depth": 16, "voxels": {}})
        
        self.window.open()
        FileUtils.log_message(f"Tilemap 3D Editor active for: {tilemap_obj.name}")

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements."""
        self.window.rect = self.rect 
        content = self.window.get_content_rect()
        
        # Center the generate button
        self.btn_generate.rect.centerx = content.centerx
        self.btn_generate.rect.y = content.y + 10
        
        # Tool buttons (top right)
        self.btn_paint.rect.topleft = (content.right - 210, content.y + 10)
        self.btn_erase.rect.topleft = (content.right - 105, content.y + 10)

    def _generate_mock(self):
        """Mock Action: Generates a procedural 3D world (delegates to procedural template)."""
        FileUtils.log_message("Action: Mock Generate 3D Voxel World triggered. (Requires EditorScene.instantiate_template)")
        # In a full app, this would initiate the generation process with parameters
        pass

    def _select_tool(self, tool_name: str):
        """Action: Selects the active voxel editing tool."""
        self.current_tool = tool_name
        FileUtils.log_message(f"Voxel tool set to: {tool_name}")
        
    def _handle_voxel_interaction(self, event: pygame.event.Event):
        """Mocks the core voxel painting/interaction logic using raycasting."""
        if not self.voxel_data: return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Mock Raycast Hit
            # NOTE: This requires the 3D viewport to perform a raycast and return a hit point/voxel coordinate
            
            # Mock hit coordinate: always the center of the world for demo
            hit_voxel_x, hit_voxel_y, hit_voxel_z = 0, 0, 0 
            
            if self.current_tool == 'paint':
                self.voxel_data['voxels'][f"{hit_voxel_x},{hit_voxel_y},{hit_voxel_z}"] = self.selected_voxel_type
                FileUtils.log_message(f"Mock Painted voxel at ({hit_voxel_x}, {hit_voxel_y}, {hit_voxel_z}) with {self.selected_voxel_type}")
            elif self.current_tool == 'erase':
                if f"{hit_voxel_x},{hit_voxel_y},{hit_voxel_z}" in self.voxel_data['voxels']:
                    del self.voxel_data['voxels'][f"{hit_voxel_x},{hit_voxel_y},{hit_voxel_z}"]
                    FileUtils.log_message(f"Mock Erased voxel at ({hit_voxel_x}, {hit_voxel_y}, {hit_voxel_z})")
            
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = self.window.handle_event(event)
        self._update_ui_rects()
        
        if self.btn_generate.handle_event(event): consumed = True
        if self.btn_paint.handle_event(event): consumed = True
        if self.btn_erase.handle_event(event): consumed = True
        
        # Mock interaction inside the 3D view area (which is typically the rest of the screen)
        if self.state.ui_state.get('active_viewport') == '3D':
            self._handle_voxel_interaction(event)
                
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        # 1. Draw Window Frame
        super().draw(surface, theme)
        content = self.window.get_content_rect()
        
        # 2. Draw Buttons/Controls
        self.btn_generate.draw(surface, theme)
        
        self.btn_paint.is_toggled = (self.current_tool == 'paint')
        self.btn_erase.is_toggled = (self.current_tool == 'erase')
        self.btn_paint.draw(surface, theme)
        self.btn_erase.draw(surface, theme)
        
        # 3. Draw Info Label
        info_rect = pygame.Rect(content.x + 10, content.y + 50, content.width - 20, 50)
        Label(info_rect, f"Voxel Types: {self.selected_voxel_type.capitalize()} | Tool: {self.current_tool.capitalize()}", alignment="left").draw(surface, theme)
        
        # 4. Draw 3D Preview (Mocked)
        preview_rect = pygame.Rect(content.x + 10, content.y + 100, content.width - 20, content.height - 110)
        pygame.draw.rect(surface, (50, 50, 50), preview_rect, 0) # Gray background for preview
        Label(preview_rect, "3D Voxel View (Rendered in Viewport3D)", text_color=Color.white().to_rgb()).draw(surface, theme)