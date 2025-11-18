# engine/gui/panel_properties.py
import pygame
import sys
import copy

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.engine_config import EngineConfig
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Window, Label, Scrollbar, TextInput, Checkbox, Dropdown
    from engine.utils.color import Color
except ImportError as e:
    print(f"[PanelProperties Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): 
            self.config = self
            self.current_scene = self
        def get_setting(self, *args): return 'dark' 
        @property
        def project_settings(self): return {"game_title": "Mock Game", "target_fps": 60, "is_3d_mode": False}
        @property
        def current_scene(self): return {"is_3d": False, "scene_properties": {"gravity": [0, 980], "background_color": [50, 50, 50]}}
        @current_scene.setter
        def current_scene(self, value): pass
    class EngineConfig:
        def set_setting(self, *args): pass
        def save_config(self): FileUtils.log_message("Mock Config Save")
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[PP-INFO] {msg}")
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def get_content_rect(self): return self.rect
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
    class Scrollbar:
        def __init__(self, rect, max_scroll): self.rect = rect; self.max_scroll = max_scroll
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_scroll_offset(self): return 0
    class TextInput:
        def __init__(self, rect, initial_text, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_text(self): return "mock_text"
        def set_text(self, text): pass
    class Checkbox:
        def __init__(self, rect, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return True
    class Dropdown:
        def __init__(self, rect, options, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return options[0]
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)
        @staticmethod
        def black(): return (0, 0, 0)
        @staticmethod
        def yellow(): return (255, 255, 0)

# --- Schemas for Properties ---

PROJECT_SETTINGS_SCHEMA = {
    "game_title": {"type": "string", "label": "Game Title", "tooltip": "Title shown in the final build window."},
    "resolution_x": {"type": "int", "label": "Resolution Width", "min": 320, "max": 4096},
    "resolution_y": {"type": "int", "label": "Resolution Height", "min": 240, "max": 4096},
    "target_fps": {"type": "int", "label": "Target FPS", "min": 15, "max": 240},
    "is_3d_mode": {"type": "boolean", "label": "Use 3D Mode", "tooltip": "Toggles 2D or 3D rendering and physics."},
    "network_port": {"type": "int", "label": "Default Net Port", "min": 1024, "max": 65535},
    "max_players": {"type": "int", "label": "Max Players", "min": 1, "max": 32}
}

SCENE_PROPERTIES_SCHEMA_2D = {
    "name": {"type": "string", "label": "Scene Name", "read_only": True},
    "gravity": {"type": "vector2_list", "label": "Gravity (x, y)", "tooltip": "Force vector applied to all dynamic objects."},
    "background_color": {"type": "color_list", "label": "Background Color (R, G, B)"},
    "initial_camera_zoom": {"type": "float", "label": "Initial Camera Zoom", "min": 0.1, "max": 10.0}
}

SCENE_PROPERTIES_SCHEMA_3D = {
    "name": {"type": "string", "label": "Scene Name", "read_only": True},
    "gravity": {"type": "vector3_list", "label": "Gravity (x, y, z)"},
    "ambient_light": {"type": "color_list", "label": "Ambient Light (R, G, B)"},
    "skybox_asset": {"type": "asset_selector", "asset_type": "texture", "label": "Skybox Texture"}
}


class PanelProperties:
    """
    Displays and allows editing of Project-level settings and Scene-level properties
    (e.g., gravity, global lighting, FPS, window size).
    """
    
    ITEM_HEIGHT = 24
    PADDING = 10
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=False, movable=False, resizeable=False)
        self.rect = rect.copy()
        
        self.font = pygame.font.Font(None, 18)
        
        # State
        self.active_tab = 'project' # 'project' or 'scene'
        self.widgets = {} # {key: widget_instance}
        self.scrollbar = None
        self.content_rect = self.window.get_content_rect()
        
        # UI Elements
        self.btn_project = Button(pygame.Rect(0, 0, 80, 24), "Project", action=lambda: self._set_tab('project'))
        self.btn_scene = Button(pygame.Rect(0, 0, 80, 24), "Scene", action=lambda: self._set_tab('scene'))
        
        self._update_ui_rects()
        self._build_widgets() # Initial build

    def _set_tab(self, tab_name: str):
        """Switches the active tab and forces a widget rebuild."""
        if self.active_tab != tab_name:
            self.active_tab = tab_name
            self._build_widgets()
            FileUtils.log_message(f"Switched to {tab_name} properties tab.")

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements based on window size."""
        self.window.rect = self.rect 
        self.content_rect = self.window.get_content_rect()
        
        # Tab Buttons
        self.btn_project.rect.topleft = (self.content_rect.x + self.PADDING, self.content_rect.y + 2)
        self.btn_scene.rect.topleft = (self.content_rect.x + self.PADDING + self.btn_project.rect.width + 5, self.content_rect.y + 2)
        
        # Calculate the area below the tab buttons for the scrollable content
        self.content_area_rect = self.content_rect.copy()
        self.content_area_rect.y += self.ITEM_HEIGHT + self.PADDING
        self.content_area_rect.height -= self.ITEM_HEIGHT + self.PADDING
        
        # Scrollbar setup
        max_scroll = 1000 # Placeholder
        scroll_rect = pygame.Rect(self.content_area_rect.right - 10, self.content_area_rect.y, 10, self.content_area_rect.height)
        self.scrollbar = Scrollbar(scroll_rect, max_scroll)


    def _build_widgets(self):
        """Dynamically generates all input widgets for the active properties schema."""
        self.widgets.clear()
        
        if self.active_tab == 'project':
            schema = PROJECT_SETTINGS_SCHEMA
            data_source = self.state.config.project_settings
        elif self.active_tab == 'scene' and self.state.current_scene:
            is_3d = self.state.current_scene.is_3d
            schema = SCENE_PROPERTIES_SCHEMA_3D if is_3d else SCENE_PROPERTIES_SCHEMA_2D
            data_source = self._get_scene_properties_source(self.state.current_scene)
        else:
            return

        y_offset = self.content_area_rect.y + self.PADDING
        x = self.content_area_rect.x + self.PADDING
        width = self.content_area_rect.width - 2 * self.PADDING - self.scrollbar.rect.width
        
        for key, prop_schema in schema.items():
            
            prop_value = data_source.get(key)
            if prop_value is None and 'default' in prop_schema:
                prop_value = prop_schema['default']
                
            y_offset = self._add_widget(y_offset, x, width, prop_schema['label'], key, prop_value, prop_schema['type'], schema=prop_schema)
            
        # Update scrollbar max
        total_height = y_offset - self.content_area_rect.y
        max_scroll = max(0, total_height - self.content_area_rect.height)
        self.scrollbar.max_scroll = max_scroll


    def _get_scene_properties_source(self, scene):
        """Combines scene name/3D flag with scene_properties for unified widget access."""
        if not scene: return {}
        data = copy.deepcopy(scene.scene_properties)
        data["name"] = scene.name
        data["is_3d_mode"] = scene.is_3d
        return data

    def _add_widget(self, y: int, x: int, width: int, label_text: str, key: str, value: any, type: str, schema: dict = None) -> int:
        """Generates and stores the appropriate widget."""
        
        label_w = 120
        widget_x = x + label_w + 5
        widget_w = width - label_w - 5
        widget_h = self.ITEM_HEIGHT - 4
        
        # Label
        label_rect = pygame.Rect(x, y + 2, label_w, widget_h)
        self.widgets[f"label_{key}"] = Label(label_rect, label_text, font=self.font, alignment="left")
        
        widget_rect = pygame.Rect(widget_x, y + 2, widget_w, widget_h)
        is_read_only = schema.get("read_only", False)
        
        if type == 'string' or type == 'asset_selector':
            widget = TextInput(widget_rect, str(value) if value else "", read_only=is_read_only)
        elif type in ['float', 'int']:
            widget = TextInput(widget_rect, str(value) if value is not None else "0", is_numeric=True, read_only=is_read_only)
        elif type == 'boolean':
            widget = Checkbox(widget_rect, is_checked=bool(value), disabled=is_read_only)
        elif type in ['vector2_list', 'vector3_list', 'color_list']:
            # Format lists as comma-separated strings for single input box
            val_str = ', '.join(map(str, value)) if isinstance(value, (tuple, list)) else str(value)
            widget = TextInput(widget_rect, val_str, is_numeric=True, read_only=is_read_only)
        else:
            widget = Label(widget_rect, f"UNSUPPORTED: {type}", text_color=Color(255, 50, 50).to_rgb())
            
        self.widgets[key] = widget
        
        return y + self.ITEM_HEIGHT


    def _apply_widget_changes(self):
        """Iterates through widgets and applies changes back to the relevant state/config."""
        
        if self.active_tab == 'project':
            schema = PROJECT_SETTINGS_SCHEMA
            data_target = 'project_settings'
        elif self.active_tab == 'scene' and self.state.current_scene:
            schema = SCENE_PROPERTIES_SCHEMA_3D if self.state.current_scene.is_3d else SCENE_PROPERTIES_SCHEMA_2D
            data_target = 'scene_properties'
        else:
            return

        for key, prop_schema in schema.items():
            widget = self.widgets.get(key)
            if not widget: continue
            
            # Skip read-only fields
            if prop_schema.get("read_only", False): continue
            
            try:
                # 1. Get the raw value from the widget
                if prop_schema['type'] == 'boolean':
                    raw_value = widget.get_value()
                elif prop_schema['type'] in ['string', 'asset_selector']:
                    raw_value = widget.get_text()
                elif prop_schema['type'] in ['float', 'int']:
                    raw_value = float(widget.get_text()) if prop_schema['type'] == 'float' else int(widget.get_text())
                elif prop_schema['type'] in ['vector2_list', 'vector3_list', 'color_list']:
                    # Parse comma-separated list
                    raw_value = [float(p.strip()) for p in widget.get_text().split(',') if p.strip()]
                else:
                    continue
                    
                # 2. Apply the value to the correct location
                if self.active_tab == 'project':
                    self.state.config.set_setting(data_target, key, raw_value)
                elif self.active_tab == 'scene':
                    # Scene name is a special case outside scene_properties dict
                    if key == "name":
                        self.state.current_scene.name = raw_value
                    # All other properties are in scene_properties dict
                    elif self.state.current_scene.scene_properties:
                        self.state.current_scene.scene_properties[key] = raw_value

            except Exception as e:
                # Log error but don't crash the editor
                # FileUtils.log_warning(f"Validation/Parse error for property {key}: {e}")
                pass
                
        # Persist changes to disk (only for project settings, scene is saved separately)
        if self.active_tab == 'project':
            self.state.config.save_config()


    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles user input for tab switching, scrolling, and widgets."""
        consumed = self.window.handle_event(event)
        
        if not self.window.rect.collidepoint(pygame.mouse.get_pos()):
            return consumed # Ignore input outside panel

        # Pass event to tab buttons
        if self.btn_project.handle_event(event) or self.btn_scene.handle_event(event):
            return True
            
        # Pass event to scrollbar
        if self.scrollbar.handle_event(event):
            return True
        
        # Pass event to widgets
        scroll_offset = self.scrollbar.get_scroll_offset()
        for key, widget in self.widgets.items():
            if key.startswith("label_") or key.startswith("header_"): continue # Skip static labels
            
            # Temporarily move widget rect for event handling
            if hasattr(widget, 'rect'):
                widget.rect.y -= scroll_offset
                
            if widget.handle_event(event):
                consumed = True
                
            # Restore widget rect position
            if hasattr(widget, 'rect'):
                widget.rect.y += scroll_offset

        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        """Draws the properties panel, tabs, and widgets."""
        
        # 1. Update Layout
        self.rect = self.window.rect 
        self._update_ui_rects()
        
        # 2. Draw Window Frame
        self.window.draw(surface, theme)
        
        # 3. Draw Tab Buttons (Highlight active tab)
        self.btn_project.is_toggled = (self.active_tab == 'project')
        self.btn_scene.is_toggled = (self.active_tab == 'scene')
        self.btn_project.draw(surface, theme)
        self.btn_scene.draw(surface, theme)
        
        # 4. Widget Rebuild & State Sync
        self._build_widgets()
        self._apply_widget_changes()

        # 5. Draw Scrollbar
        self.scrollbar.draw(surface, theme)
        scroll_offset = self.scrollbar.get_scroll_offset()
        
        # 6. Draw Widgets
        
        # Setup clipping for the scrollable area
        surface.set_clip(self.content_area_rect)
        
        for key, widget in self.widgets.items():
            # Translate widget position by scroll offset
            if hasattr(widget, 'rect'):
                widget.rect.y -= scroll_offset
                
            widget.draw(surface, theme)
            
            # Reset rect position after drawing
            if hasattr(widget, 'rect'):
                widget.rect.y += scroll_offset

        surface.set_clip(None)