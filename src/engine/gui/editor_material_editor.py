# editor/editor_material_editor.py
import pygame
import sys
import copy
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.rendering.material import Material, MaterialManager
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Window, Label, TextInput, Button, Checkbox, Slider, Dropdown
    from engine.utils.color import Color
    from engine.utils.vector3 import Vector3 # For 3D color/vector visualization
except ImportError as e:
    print(f"[EditorMaterialEditor Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): self.asset_loader = self; self.material_manager = self
        def get_asset(self, type, name): return None
    class Material:
        def __init__(self, name="Default"): self.name = name; self.color = Color.gray(); self.albedo_texture = None; self.metallic = 0.0; self.roughness = 0.8
        def to_dict(self): return {"name": self.name, "color": self.color.to_rgba(), "albedo_texture": self.albedo_texture, "metallic": self.metallic, "roughness": self.roughness, "shader_name": "default_lit"}
    class MaterialManager:
        def __init__(self, state): pass
        def load_material(self, name): return Material(name)
        def save_material(self, mat, name): FileUtils.log_message(f"Mock Saved Material: {name}")
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[EME-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[EME-ERROR] {msg}", file=sys.stderr)
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def get_content_rect(self): return self.rect
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
    class TextInput:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_text(self): return text
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Checkbox:
        def __init__(self, rect, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return True
    class Slider:
        def __init__(self, rect, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return kwargs.get('initial_val', 0.5)
    class Dropdown:
        def __init__(self, rect, options, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return options[0]
    class Color:
        @staticmethod
        def gray(): return Color(128, 128, 128)
        @staticmethod
        def white(): return Color(255, 255, 255)
        def to_rgb(self): return (self.r, self.g, self.b)
    class Vector3:
        def __init__(self, x, y, z): self.x, self.y, self.z = x, y, z


class EditorMaterialEditor:
    """
    Floating window/tool for editing Material properties (color, texture, PBR values).
    """
    ITEM_HEIGHT = 24
    PADDING = 10

    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Material Editor 🎨"):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=True, movable=True)
        self.rect = rect.copy()
        
        self.active_material: Material | None = None
        self.widgets: Dict[str, Any] = {}
        self.current_asset_name = "Default_Lit" # Name of the material being edited

        self.font = pygame.font.Font(None, 18)
        self._load_active_material(self.current_asset_name)
        self._update_ui_rects()

    def _load_active_material(self, name: str):
        """Loads a material from the manager and rebuilds widgets."""
        if self.state.material_manager:
            self.active_material = self.state.material_manager.load_material(name)
        
        if not self.active_material:
            self.active_material = Material(name) # Fallback
            
        self.current_asset_name = name
        self._build_widgets()
        FileUtils.log_message(f"Material Editor loaded: {name}")

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements."""
        self.window.rect = self.rect 
        
    def _build_widgets(self):
        """Generates all property widgets for the active material."""
        self.widgets.clear()
        if not self.active_material: return
        
        content = self.window.get_content_rect()
        x = content.x + self.PADDING
        w = content.width - 2 * self.PADDING
        y = content.y + self.PADDING
        
        def add_prop_widget(y_start, label_text, key, type_str, value, min_val=0.0, max_val=1.0):
            """Helper to add label and input widget."""
            label_w = 120
            widget_w = w - label_w - 5
            
            widgets[f"label_{key}"] = Label(pygame.Rect(x, y_start, label_w, self.ITEM_HEIGHT), label_text, alignment="left")
            widget_rect = pygame.Rect(x + label_w + 5, y_start, widget_w, self.ITEM_HEIGHT)
            
            if type_str == 'string':
                widgets[key] = TextInput(widget_rect, str(value))
            elif type_str == 'slider':
                widgets[key] = Slider(widget_rect, min_val=min_val, max_val=max_val, initial_val=value)
            elif type_str == 'checkbox':
                widgets[key] = Checkbox(widget_rect.inflate(-widget_w + 20, 0), is_checked=value, label="")
            elif type_str == 'color':
                # Mock color input as R, G, B text input
                color_str = ', '.join(map(str, value.to_rgb()))
                widgets[key] = TextInput(widget_rect, color_str, is_numeric=True)
            elif type_str == 'asset_selector':
                 widgets[key] = TextInput(widget_rect, str(value) if value else "None (Click to Select)")
            
            return y_start + self.ITEM_HEIGHT + 2

        # --- Material Info ---
        widgets = self.widgets
        y = add_prop_widget(y, "Name", "name", "string", self.active_material.name)
        y = add_prop_widget(y, "Shader", "shader_name", "string", self.active_material.shader_name, min_val=0.0, max_val=1.0)
        y = add_prop_widget(y, "Transparent", "transparent", "checkbox", self.active_material.transparent)
        y += self.PADDING
        
        # --- Albedo/Color ---
        y = add_prop_widget(y, "Base Color", "color", "color", self.active_material.color)
        y = add_prop_widget(y, "Albedo Texture", "albedo_texture", "asset_selector", self.active_material.albedo_texture)
        y = add_prop_widget(y, "Albedo Tint", "albedo_tint", "color", self.active_material.albedo_tint)
        y += self.PADDING
        
        # --- PBR Properties ---
        widgets[f"header_pbr"] = Label(pygame.Rect(x, y, w, self.ITEM_HEIGHT), "PBR Properties (3D Only)", text_color=self.state.get_theme_color('accent'))
        y += self.ITEM_HEIGHT
        y = add_prop_widget(y, "Metallic", "metallic", "slider", self.active_material.metallic, 0.0, 1.0)
        y = add_prop_widget(y, "Roughness", "roughness", "slider", self.active_material.roughness, 0.0, 1.0)
        y = add_prop_widget(y, "Normal Map", "normal_texture", "asset_selector", self.active_material.normal_texture)
        y += self.PADDING

        # --- Save/Load Buttons ---
        widgets['save_btn'] = Button(pygame.Rect(content.right - 100, content.bottom - 30, 80, 24), 
                                     "💾 Save", self.state.asset_loader.get_icon('save'), action=self._save_material)
        widgets['new_btn'] = Button(pygame.Rect(content.right - 190, content.bottom - 30, 80, 24), 
                                     "➕ New", self.state.asset_loader.get_icon('plus'), action=lambda: self._load_active_material("New_Material"))

    def _save_material(self):
        """Action: Applies widget changes to the material and saves it via the manager."""
        if not self.active_material: return
        
        # Apply changes from widgets (Mocking data retrieval)
        try:
            self.active_material.name = self.widgets['name'].get_text()
            self.active_material.shader_name = self.widgets['shader_name'].get_text()
            self.active_material.transparent = self.widgets['transparent'].get_value()
            
            # Roughness/Metallic from sliders
            self.active_material.roughness = self.widgets['roughness'].get_value()
            self.active_material.metallic = self.widgets['metallic'].get_value()
            
            # Albedo Texture/Normal Map
            self.active_material.albedo_texture = self.widgets['albedo_texture'].get_text()
            self.active_material.normal_texture = self.widgets['normal_texture'].get_text()
            
            # Color update (Mock R,G,B tuple parsing from TextInput)
            color_text = self.widgets['color'].get_text()
            r, g, b = map(int, [p.strip() for p in color_text.split(',')][:3])
            self.active_material.color = Color(r, g, b)

            if self.state.material_manager:
                self.state.material_manager.save_material(self.active_material, self.active_material.name)

        except Exception as e:
            FileUtils.log_error(f"Error applying/saving material changes: {e}")
            
    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = super().handle_event(event)
        self._update_ui_rects()
        
        for widget in self.widgets.values():
            if hasattr(widget, 'handle_event') and widget.handle_event(event):
                consumed = True
                
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        super().draw(surface, theme)
        
        # Rebuild/Position widgets (simplified)
        self._build_widgets() 
        
        # Draw 3D Preview (Mock: Simple sphere)
        content = self.window.get_content_rect()
        preview_rect = pygame.Rect(content.right - 160, content.y + 40, 150, 150)
        pygame.draw.circle(surface, self.active_material.color.to_rgb(), preview_rect.center, 50)
        
        # Draw widgets
        for widget in self.widgets.values():
            if hasattr(widget, 'draw'):
                widget.draw(surface, theme)