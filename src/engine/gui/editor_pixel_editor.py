# editor/editor_pixel_editor.py
import pygame
import sys
import copy
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Window, Label, Button, Slider
    from engine.utils.color import Color
except ImportError as e:
    print(f"[EditorPixelEditor Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): self.asset_loader = self
        def get_asset(self, type, name): 
            s = pygame.Surface((32, 32)); s.fill((255, 0, 255)); return s
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[EPE-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[EPE-ERROR] {msg}", file=sys.stderr)
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def get_content_rect(self): return self.rect
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Slider:
        def __init__(self, rect, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return kwargs.get('initial_val', 1.0)
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)
        @staticmethod
        def red(): return (255, 0, 0)
        def to_rgb(self): return (self.r, self.g, self.b)
        def __init__(self, r, g, b): self.r, self.g, self.b = r, g, b


class EditorPixelEditor:
    """
    Floating window/tool for simple pixel-level editing of sprites and textures.
    Features: pencil, eraser, color picker, zoom.
    """
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Pixel Editor 🖼️"):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=True, movable=True)
        self.rect = rect.copy()
        
        # State
        self.active_asset_name = None
        self.working_surface: pygame.Surface | None = None
        self.current_color = Color(255, 0, 0)
        self.zoom_level = 10.0 # Pixels per source pixel
        self.brush_size = 1
        self.current_tool = 'pencil' # 'pencil', 'eraser', 'picker'
        self.is_drawing = False
        
        # UI Elements
        self.btn_save = Button(pygame.Rect(0, 0, 80, 24), "💾 Save", self.state.asset_loader.get_icon('save'), action=self._save_asset)
        self.btn_pencil = Button(pygame.Rect(0, 0, 30, 30), "✏️", action=lambda: self._set_tool('pencil'))
        self.btn_eraser = Button(pygame.Rect(0, 0, 30, 30), "🧼", action=lambda: self._set_tool('eraser'))
        self.brush_slider = Slider(pygame.Rect(0, 0, 100, 24), min_val=1, max_val=16, initial_val=1, step=1)
        
        self._update_ui_rects()

    def load_asset(self, asset_name: str):
        """Loads an image asset into the editor's working surface."""
        self.active_asset_name = asset_name
        asset = self.state.asset_loader.get_asset('image', asset_name)
        
        if asset:
            self.working_surface = asset.copy().convert_alpha()
            self.window.open()
            self._update_ui_rects()
            FileUtils.log_message(f"Pixel Editor loaded: {asset_name}")
        else:
            FileUtils.log_error(f"Asset '{asset_name}' not found for pixel editing.")
            
    def _save_asset(self):
        """Action: Overwrites the original asset file with the working surface content."""
        if self.working_surface and self.active_asset_name:
            # Mock saving back to disk (requires FileUtils/Pygame save)
            full_path = self.state.asset_loader.get_asset_path('image', self.active_asset_name)
            
            try:
                pygame.image.save(self.working_surface, full_path)
                # Force AssetLoader to reload the asset from disk
                self.state.asset_loader.load_asset('image', self.active_asset_name, force_reload=True)
                FileUtils.log_message(f"Saved pixel edits to {self.active_asset_name}")
            except Exception as e:
                FileUtils.log_error(f"Failed to save image asset: {e}")

    def _set_tool(self, tool_name: str):
        self.current_tool = tool_name

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements."""
        self.window.rect = self.rect 
        content = self.window.get_content_rect()
        
        x, y = content.x + 10, content.y + 10
        self.btn_save.rect.topleft = (content.right - 90, y)
        
        self.btn_pencil.rect.topleft = (x, y)
        self.btn_eraser.rect.topleft = (x + 35, y)
        self.brush_slider.rect.topleft = (x + 75, y)
        self.brush_slider.rect.width = 100

    def _get_pixel_coord(self, mouse_pos: tuple[int, int]) -> tuple[int, int] | None:
        """Converts mouse screen position to (x, y) pixel coordinate on the source surface."""
        if not self.working_surface: return None
        
        # Center the asset in the view area (mock)
        center_x = self.window.rect.x + self.window.rect.width / 2
        center_y = self.window.rect.y + self.window.rect.height / 2
        
        w, h = self.working_surface.get_size()
        
        # Top-left of the zoomed asset
        asset_x = center_x - (w * self.zoom_level) / 2
        asset_y = center_y - (h * self.zoom_level) / 2
        
        # Mouse relative to asset top-left
        rel_x = mouse_pos[0] - asset_x
        rel_y = mouse_pos[1] - asset_y
        
        # Convert to source pixel coordinate
        src_x = int(rel_x / self.zoom_level)
        src_y = int(rel_y / self.zoom_level)
        
        if 0 <= src_x < w and 0 <= src_y < h:
            return src_x, src_y
        return None

    def _draw_pixel(self, pixel_coord: tuple[int, int]):
        """Draws a single pixel/brush stroke on the working surface."""
        if not self.working_surface or not pixel_coord: return

        x, y = pixel_coord
        brush_r = self.brush_size // 2
        
        for dy in range(-brush_r, brush_size - brush_r):
            for dx in range(-brush_r, brush_size - brush_r):
                px, py = x + dx, y + dy
                if 0 <= px < self.working_surface.get_width() and 0 <= py < self.working_surface.get_height():
                    
                    if self.current_tool == 'pencil':
                        self.working_surface.set_at((px, py), self.current_color.to_rgba())
                    elif self.current_tool == 'eraser':
                        self.working_surface.set_at((px, py), (0, 0, 0, 0)) # Transparent
                        

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = super().handle_event(event)
        self._update_ui_rects()
        
        # UI events
        if self.btn_save.handle_event(event): consumed = True
        if self.btn_pencil.handle_event(event): consumed = True
        if self.btn_eraser.handle_event(event): consumed = True
        if self.brush_slider.handle_event(event):
            self.brush_size = int(self.brush_slider.get_value())
            consumed = True

        # Drawing logic
        if self.working_surface:
            pixel_coord = self._get_pixel_coord(pygame.mouse.get_pos())
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and pixel_coord:
                self.is_drawing = True
                self._draw_pixel(pixel_coord)
                consumed = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.is_drawing = False
                consumed = True
            elif event.type == pygame.MOUSEMOTION and self.is_drawing and event.buttons[0] and pixel_coord:
                self._draw_pixel(pixel_coord)
                consumed = True
        
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        super().draw(surface, theme)
        content = self.window.get_content_rect()
        
        self.btn_save.draw(surface, theme)
        self.btn_pencil.is_toggled = (self.current_tool == 'pencil')
        self.btn_eraser.is_toggled = (self.current_tool == 'eraser')
        self.btn_pencil.draw(surface, theme)
        self.btn_eraser.draw(surface, theme)
        self.brush_slider.draw(surface, theme)
        Label(pygame.Rect(self.brush_slider.rect.x, self.brush_slider.rect.y - 15, 100, 15), f"Brush: {self.brush_size}").draw(surface, theme)

        if self.working_surface:
            # Draw the working surface scaled (Zoomed Preview)
            scaled_w = int(self.working_surface.get_width() * self.zoom_level)
            scaled_h = int(self.working_surface.get_height() * self.zoom_level)
            
            scaled_surface = pygame.transform.scale(self.working_surface, (scaled_w, scaled_h))
            
            # Center in content area
            draw_x = content.x + (content.width - scaled_w) // 2
            draw_y = content.y + (content.height - scaled_h) // 2
            
            draw_rect = pygame.Rect(draw_x, draw_y, scaled_w, scaled_h)
            
            # Draw grid lines over the scaled surface
            pygame.draw.rect(surface, Color.black().to_rgb(), draw_rect, 1) # Outline

            surface.blit(scaled_surface, draw_rect.topleft)