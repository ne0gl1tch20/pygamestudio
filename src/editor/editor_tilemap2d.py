# editor/editor_tilemap2d.py
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
    from engine.utils.vector2 import Vector2
    from engine.utils.color import Color
    from engine.gui.gui_widgets import Window, Button, Label
except ImportError as e:
    print(f"[EditorTilemap2D Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def get_asset_loader(self): return self
        def get_asset(self, type, name): 
            s = pygame.Surface((32, 32)); s.fill((100, 100, 100)); return s
    class SceneObject:
        def __init__(self, uid): self.uid = uid; self.name = "MockTilemap"; self.components = [{"type": "TilemapRenderer", "tilemap_data": {"width": 10, "height": 10, "tile_size": 32, "tiles": []}}]
        def get_component(self, type): return self.components[0]
    class CameraObject:
        def __init__(self): self.position = Vector2(0, 0); self.zoom = 1.0
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[ET2D-INFO] {msg}")
    class Vector2:
        def __init__(self, x, y): self.x, self.y = float(x), float(y)
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
        def yellow(): return (255, 255, 0)
        @staticmethod
        def red(): return (255, 0, 0)

class EditorTilemap2D:
    """
    Specialized editor panel for visualizing and editing 2D tilemap data.
    Allows tile selection, tile painting, and tile asset management.
    """
    
    TILESET_PREVIEW_SIZE = 64
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Tilemap Editor 🗺️"):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=True, movable=True)
        self.rect = rect.copy()
        
        self.font = pygame.font.Font(None, 18)
        
        # State
        self.active_tilemap_uid = None
        self.selected_tile_type = "grass" # Tile type/asset to paint
        self.is_painting = False
        self.tilemap_obj: SceneObject | None = None
        self.tilemap_data: Dict[str, Any] | None = None

        # UI Elements
        self.btn_load_tileset = Button(pygame.Rect(0, 0, 150, 24), "Load Tileset", action=self._load_tileset_mock)
        self.btn_save_tilemap = Button(pygame.Rect(0, 0, 150, 24), "Save Tilemap", action=self._save_tilemap_mock)
        self.tileset_buttons = {} # {tile_type: Button}
        
        self._update_ui_rects()
        
    def set_active_tilemap(self, tilemap_obj: SceneObject):
        """Sets the SceneObject containing the TilemapRenderer component as active."""
        comp = tilemap_obj.get_component("TilemapRenderer")
        if not comp:
            FileUtils.log_error(f"Object {tilemap_obj.name} does not have a TilemapRenderer.")
            return

        self.active_tilemap_uid = tilemap_obj.uid
        self.tilemap_obj = tilemap_obj
        self.tilemap_data = comp.get("tilemap_data")
        
        self._update_tileset_buttons()
        self.window.open()
        FileUtils.log_message(f"Tilemap Editor active for: {tilemap_obj.name}")

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements based on window size."""
        self.window.rect = self.rect 
        content = self.window.get_content_rect()
        
        # Buttons on the right side
        btn_x = content.right - 10 - 150
        y = content.y + 10
        
        self.btn_load_tileset.rect.topleft = (btn_x, y)
        y += 30
        self.btn_save_tilemap.rect.topleft = (btn_x, y)
        y += 30
        
        # Tileset preview area (Mock)
        self.tileset_preview_rect = pygame.Rect(btn_x, y, 150, content.height - y - 10)
        
        # Main tilemap view area (The big canvas on the left)
        self.tilemap_view_rect = pygame.Rect(content.x + 10, content.y + 10, content.width - 150 - 30, content.height - 20)
        
        # Update tileset buttons based on new rect
        self._update_tileset_buttons()

    def _load_tileset_mock(self):
        """Mock Action: Triggers file dialog to load a tileset JSON/PNG."""
        FileUtils.log_message("Action: Load Tileset triggered (Mock).")
        # Mock add some tile types
        self._mock_add_tile_types(["road", "lava", "water"])
        self._update_tileset_buttons()
        
    def _mock_add_tile_types(self, new_types: List[str]):
        """Helper to mock adding new tile types to the data."""
        if self.tilemap_data and 'tile_types' not in self.tilemap_data:
            self.tilemap_data['tile_types'] = {}
            
        for t in new_types:
            self.tilemap_data['tile_types'][t] = {"asset": f"{t}_tile.png"}
        
    def _save_tilemap_mock(self):
        """Mock Action: Saves the current tilemap data back to the project assets."""
        if self.tilemap_data:
            # Assuming tilemap data is saved in a component and will be saved with the scene.
            # We explicitly save a file here if needed (e.g., a dedicated tileset.json)
            FileUtils.log_message(f"Action: Tilemap data saved/updated for {self.tilemap_obj.name}.")
            
    def _update_tileset_buttons(self):
        """Generates buttons for each tile type found in the tilemap data."""
        self.tileset_buttons.clear()
        if not self.tilemap_data or 'tile_types' not in self.tilemap_data:
            return
            
        x, y = self.tileset_preview_rect.topleft
        btn_w, btn_h = 70, 30
        
        for i, (tile_type, data) in enumerate(self.tilemap_data['tile_types'].items()):
            btn = Button(pygame.Rect(x + 5 + (i % 2) * 75, y + 5 + (i // 2) * 35, btn_w, btn_h), 
                         tile_type.capitalize(), action=lambda t=tile_type: self._select_tile(t))
            self.tileset_buttons[tile_type] = btn
            
    def _select_tile(self, tile_type: str):
        """Action: Selects a tile type to use for painting."""
        self.selected_tile_type = tile_type
        FileUtils.log_message(f"Tile selected for painting: {tile_type}")


    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = self.window.handle_event(event)
        if not self.window.rect.collidepoint(pygame.mouse.get_pos()): return consumed

        # Update widget rects
        self._update_ui_rects()
        
        # Button/Widget events
        for btn in [self.btn_load_tileset, self.btn_save_tilemap] + list(self.tileset_buttons.values()):
            if btn.handle_event(event): consumed = True
            
        # Tilemap Painting Logic (LMB Down/Drag inside map view)
        if self.tilemap_view_rect.collidepoint(pygame.mouse.get_pos()):
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.is_painting = True
                self._paint_tile_at_mouse(event.pos)
                consumed = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.is_painting = False
                consumed = True
            elif event.type == pygame.MOUSEMOTION and self.is_painting and event.buttons[0]:
                self._paint_tile_at_mouse(event.pos)
                consumed = True
                
        return consumed

    def _paint_tile_at_mouse(self, mouse_pos: tuple[int, int]):
        """Converts mouse position to grid coordinates and updates the tilemap data."""
        if not self.tilemap_data: return
        
        tile_size = self.tilemap_data.get('tile_size', 32)
        grid_w = self.tilemap_data.get('width', 1)
        grid_h = self.tilemap_data.get('height', 1)
        
        # Calculate world position (simplified: directly from mouse pos in view)
        rel_x = mouse_pos[0] - self.tilemap_view_rect.x
        rel_y = mouse_pos[1] - self.tilemap_view_rect.y
        
        # Convert to grid index
        grid_x = rel_x // tile_size
        grid_y = rel_y // tile_size
        
        if 0 <= grid_x < grid_w and 0 <= grid_y < grid_h:
            # Update the tile data
            self.tilemap_data['tiles'][grid_y][grid_x] = {"type": self.selected_tile_type, "asset": f"{self.selected_tile_type}_tile.png"}
            # NOTE: For performance, this change should be debounced or marked as "dirty"
            # FileUtils.log_message(f"Painted tile at ({grid_x}, {grid_y}) with {self.selected_tile_type}")
            

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        # 1. Draw Window Frame
        super().draw(surface, theme)
        
        # 2. Draw Buttons/UI Controls
        for btn in [self.btn_load_tileset, self.btn_save_tilemap] + list(self.tileset_buttons.values()):
            # Highlight selected tile
            if btn.text.lower().replace(" ", "") == self.selected_tile_type.lower():
                btn.is_toggled = True
            else:
                btn.is_toggled = False
            btn.draw(surface, theme)
            
        # 3. Draw Tileset Preview Placeholder
        pygame.draw.rect(surface, self.state.get_theme_color('secondary'), self.tileset_preview_rect, 0, 3)
        Label(self.tileset_preview_rect.inflate(-10, -10), "Tileset Assets", text_color=self.state.get_theme_color('text_disabled')).draw(surface, theme)

        # 4. Draw Main Tilemap View
        self._draw_tilemap_view(surface, self.tilemap_view_rect, theme)

    def _draw_tilemap_view(self, surface: pygame.Surface, view_rect: pygame.Rect, theme: str):
        """Renders the tilemap and grid lines for editing."""
        
        pygame.draw.rect(surface, self.state.get_theme_color('primary'), view_rect, 0)
        
        if not self.tilemap_data:
            Label(view_rect, "No Tilemap Object Selected", text_color=self.state.get_theme_color('text_disabled')).draw(surface, theme)
            return

        tile_size = self.tilemap_data.get('tile_size', 32)
        grid_w = self.tilemap_data.get('width', 1)
        grid_h = self.tilemap_data.get('height', 1)
        
        # Clip rendering to the view area
        surface.set_clip(view_rect)
        
        # --- Draw Tiles ---
        for y in range(grid_h):
            for x in range(grid_w):
                tile_data = self.tilemap_data['tiles'][y][x]
                tile_rect = pygame.Rect(view_rect.x + x * tile_size, view_rect.y + y * tile_size, tile_size, tile_size)
                
                # Get Tile Asset/Color (Mock)
                tile_type = tile_data.get("type", "default")
                color = {"water": Color(0, 50, 150).to_rgb(), "grass": Color(50, 150, 50).to_rgb(), "sand": Color(200, 200, 100).to_rgb()}.get(tile_type, Color.red().to_rgb())
                
                # Draw the tile background
                pygame.draw.rect(surface, color, tile_rect, 0)
                
        # --- Draw Grid Lines ---
        grid_color = Color(100, 100, 100).to_rgb()
        
        # Vertical lines
        for x in range(grid_w + 1):
            x_pos = view_rect.x + x * tile_size
            pygame.draw.line(surface, grid_color, (x_pos, view_rect.y), (x_pos, view_rect.bottom))
            
        # Horizontal lines
        for y in range(grid_h + 1):
            y_pos = view_rect.y + y * tile_size
            pygame.draw.line(surface, grid_color, (view_rect.x, y_pos), (view_rect.right, y_pos))
            
        surface.set_clip(None)


# --- 3D Tilemap Editor (Mock Implementation) ---

class EditorTilemap3D:
    """
    Specialized editor panel for visualizing and editing 3D tilemaps/voxel data.
    Mocked due to complexity.
    """
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Tilemap 3D Editor 🧊"):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=True, movable=True)
        self.rect = rect.copy()
        
        self.font = pygame.font.Font(None, 24)
        self.active_tilemap_uid = None
        
        self.btn_generate = Button(pygame.Rect(0, 0, 150, 30), "Generate Voxel World", action=self._generate_mock)
        self._update_ui_rects()

    def set_active_tilemap(self, tilemap_obj: SceneObject):
        """Sets the active 3D tilemap (e.g., a VoxelGrid component)."""
        self.active_tilemap_uid = tilemap_obj.uid
        self.window.open()
        FileUtils.log_message(f"Tilemap 3D Editor active for: {tilemap_obj.name}")

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements."""
        self.window.rect = self.rect 
        content = self.window.get_content_rect()
        self.btn_generate.rect.center = content.center

    def _generate_mock(self):
        """Mock Action: Generates a procedural 3D world (delegates to procedural template)."""
        FileUtils.log_message("Action: Mock Generate 3D Voxel World triggered.")
        # This would typically open a dialog for procedural generation parameters
        pass

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = self.window.handle_event(event)
        self._update_ui_rects()
        if self.btn_generate.handle_event(event): consumed = True
                
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        super().draw(surface, theme)
        content = self.window.get_content_rect()
        
        Label(content, "3D Voxel/Tilemap Editor (Feature Mock)", text_color=Color.white().to_rgb()).draw(surface, theme)
        self.btn_generate.draw(surface, theme)