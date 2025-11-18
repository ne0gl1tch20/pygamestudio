# engine/gui/panel_inspector.py
import pygame
import sys
import copy

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from ..engine.core.engine_state import EngineState
    from ..engine.core.scene_manager import SceneObject, SceneManager
    from ..engine.utils.file_utils import FileUtils
    from ..engine.utils.vector2 import Vector2
    from ..engine.utils.vector3 import Vector3
    from ..engine.gui.gui_widgets import Window, Label, Scrollbar, TextInput, Button, Checkbox, Slider, Dropdown
    from ..engine.physics.rigidbody2d import Rigidbody2D
    from ..engine.physics.rigidbody3d import Rigidbody3D
except ImportError as e:
    print(f"[PanelInspector Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        selected_object_uid = None
        def get_object_by_uid(self, uid): return None
        def __init__(self): self.current_scene = self; self.scene_manager = self
        def get_scene_object_schema(self): return {"name": {"type": "string", "label": "Name"}}
    class SceneObject:
        def __init__(self): self.name = "MockObject"; self.position = Vector2(0, 0); self.rotation = 0; self.scale = Vector2(1, 1); self.components = []
        def get_component(self, type): return None
    class SceneManager:
        def get_scene_object_schema(self): return {}
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[PI-INFO] {msg}")
    class Vector2:
        def __init__(self, x, y): self.x, self.y = x, y
        def to_tuple(self): return (self.x, self.y)
    class Vector3:
        def __init__(self, x, y, z): self.x, self.y, self.z = x, y, z
        def to_tuple(self): return (self.x, self.y, self.z)
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
    class Button:
        def __init__(self, rect, text, **kwargs): self.rect = rect
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
        def get_value(self): return 0.5
    class Dropdown:
        def __init__(self, rect, options, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return options[0]
    class Rigidbody2D:
        def get_schema(): return {"mass": {"type": "float", "label": "Mass (kg)"}}
    class Rigidbody3D:
        def get_schema(): return {"mass": {"type": "float", "label": "Mass (kg)"}}


# Component Schemas Mapping (Add all component schemas here)
COMPONENT_SCHEMAS = {
    "Rigidbody2D": Rigidbody2D.get_schema,
    "Rigidbody3D": Rigidbody3D.get_schema,
    # Add other component schemas here (e.g., BoxCollider2D, Script, SpriteRenderer, MeshRenderer)
    # Mocking a few others for demonstration
    "SpriteRenderer": lambda: {"asset": {"type": "asset_selector", "asset_type": "image", "label": "Sprite Asset"}},
    "MeshRenderer": lambda: {"mesh_asset": {"type": "asset_selector", "asset_type": "mesh", "label": "Mesh Asset"}},
    "Script": lambda: {"file": {"type": "asset_selector", "asset_type": "script", "label": "Script File"}},
    "BehaviorTree": lambda: {"tree_name": {"type": "dropdown", "label": "Behavior Tree", "options": ["DefaultAI", "PatrolOnly"]}},
}


class PanelInspector:
    """
    Displays the properties and components of the currently selected SceneObject.
    Allows editing of properties via various GUI widgets.
    """
    
    ITEM_HEIGHT = 28
    PADDING = 10
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=False, movable=False, resizeable=False)
        self.rect = rect.copy()
        
        self.font = pygame.font.Font(None, 18)
        
        # State
        self.current_object_uid = None
        self.widgets = {} # {widget_key: widget_instance}
        self.scrollbar = None
        self.content_rect = self.window.get_content_rect()
        
        self.add_component_button = Button(pygame.Rect(0, 0, 150, 24), "➕ Add Component", action=self._show_add_component_menu)
        self.add_component_menu = None # Dropdown/Window for component selection
        self._update_ui_rects()

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements based on window size."""
        self.window.rect = self.rect 
        self.content_rect = self.window.get_content_rect()
        
        # Add Component Button position
        btn_w, btn_h = self.add_component_button.rect.size
        self.add_component_button.rect.topleft = (self.content_rect.x + (self.content_rect.width - btn_w) // 2, self.content_rect.bottom - btn_h - self.PADDING)

        # Update scrollbar max scroll (this is estimated and updated on draw)
        max_scroll = 1000 # Placeholder
        scroll_rect = pygame.Rect(self.content_rect.right - 10, self.content_rect.y, 10, self.content_rect.height)
        self.scrollbar = Scrollbar(scroll_rect, max_scroll)


    def _build_widgets(self, obj: SceneObject):
        """Dynamically generates all input widgets for the object's properties and components."""
        self.widgets.clear()
        
        if not obj:
            return
            
        y_offset = self.content_rect.y + self.PADDING 
        x = self.content_rect.x + self.PADDING
        width = self.content_rect.width - 2 * self.PADDING - 10 # - scrollbar width
        
        # --- 1. Base SceneObject Properties ---
        # NOTE: We skip object schema generation for this complexity level and hardcode the main properties
        
        # Name Input
        y_offset = self._add_widget(y_offset, x, width, "Name", "name", obj.name, "string")
        
        # Transform Properties (Position, Rotation, Scale)
        is_3d = self.state.current_scene.is_3d if self.state.current_scene else False
        vec_type = "vector3" if is_3d else "vector2"

        y_offset = self._add_widget(y_offset, x, width, "Position", "position", obj.position.to_tuple(), vec_type)
        
        rot_val = obj.rotation.to_tuple() if is_3d else obj.rotation
        rot_type = "vector3" if is_3d else "float"
        y_offset = self._add_widget(y_offset, x, width, "Rotation", "rotation", rot_val, rot_type)
        
        scale_val = obj.scale.to_tuple() if is_3d else obj.scale.to_tuple()
        y_offset = self._add_widget(y_offset, x, width, "Scale", "scale", scale_val, vec_type)

        # --- 2. Components ---
        y_offset += self.PADDING * 2
        y_offset = self._add_header(y_offset, x, width, "Components")
        
        for i, comp_data in enumerate(obj.components):
            comp_type = comp_data.get("type", "Unknown")
            
            # Component Header (e.g., Rigidbody2D [X button])
            y_offset = self._add_component_header(y_offset, x, width, comp_type, i)
            
            # Component Properties (from schema)
            schema_func = COMPONENT_SCHEMAS.get(comp_type)
            if schema_func:
                comp_schema = schema_func()
                for key, prop_schema in comp_schema.items():
                    prop_value = comp_data.get(key)
                    # Use schema type and label
                    y_offset = self._add_widget(y_offset, x, width, prop_schema['label'], f"comp_{i}_{key}", prop_value, prop_schema['type'], schema=prop_schema)
            
            y_offset += self.PADDING
            
        # Update scrollbar max after adding all widgets
        total_height = y_offset - self.content_rect.y
        max_scroll = max(0, total_height - self.content_rect.height + self.ITEM_HEIGHT)
        self.scrollbar.max_scroll = max_scroll

    def _add_header(self, y: int, x: int, width: int, text: str) -> int:
        """Adds a simple header label."""
        rect = pygame.Rect(x, y, width, self.ITEM_HEIGHT)
        label = Label(rect, text, font=self.font, text_color=self.state.get_theme_color('accent'))
        self.widgets[f"header_{text.replace(' ', '_')}"] = label
        return y + self.ITEM_HEIGHT + self.PADDING

    def _add_component_header(self, y: int, x: int, width: int, comp_type: str, comp_index: int) -> int:
        """Adds a component header with a collapse/delete button."""
        rect = pygame.Rect(x, y, width, self.ITEM_HEIGHT)
        label = Label(rect, f"Component: {comp_type}", font=self.font)
        self.widgets[f"comp_header_{comp_index}"] = label
        
        # Add Delete Button
        btn_rect = pygame.Rect(rect.right - 20, rect.y + 2, 20, 20)
        delete_btn = Button(btn_rect, "X", action=lambda: self._delete_component(comp_index))
        self.widgets[f"comp_delete_{comp_index}"] = delete_btn
        
        return y + self.ITEM_HEIGHT

    def _add_widget(self, y: int, x: int, width: int, label_text: str, key: str, value: any, type: str, schema: dict = None) -> int:
        """
        Generates and stores the appropriate widget based on property type.
        Returns the next available y-offset.
        """
        
        label_w = 80
        widget_x = x + label_w + 5
        widget_w = width - label_w - 5
        widget_h = self.ITEM_HEIGHT - 4
        
        # Label
        label_rect = pygame.Rect(x, y + 2, label_w, widget_h)
        self.widgets[f"label_{key}"] = Label(label_rect, label_text, font=self.font, alignment="left")
        
        widget_rect = pygame.Rect(widget_x, y + 2, widget_w, widget_h)
        
        if type == 'string' or type == 'asset_selector':
            widget = TextInput(widget_rect, str(value) if value else "")
        elif type == 'float' or type == 'int':
            # Use TextInput for numeric entry (allows live editing)
            widget = TextInput(widget_rect, str(value) if value is not None else "0", is_numeric=True)
        elif type == 'boolean':
            widget = Checkbox(widget_rect, is_checked=bool(value))
        elif type == 'vector2' or type == 'vector3':
            # Multi-part input for vectors (Mocking as a single input for simplicity here)
            # Full implementation would use multiple TextInput widgets side-by-side
            val_str = ', '.join(f"{v:.2f}" for v in value) if isinstance(value, (tuple, list)) else str(value)
            widget = TextInput(widget_rect, val_str, is_numeric=True)
        elif type == 'dropdown':
             widget = Dropdown(widget_rect, schema.get('options', []), initial_selection=value)
        else:
            widget = Label(widget_rect, f"UNSUPPORTED TYPE: {type}", text_color=Color(255, 50, 50).to_rgb())
            
        self.widgets[key] = widget
        
        return y + self.ITEM_HEIGHT


    def _apply_widget_changes(self, obj: SceneObject):
        """Iterates through widgets and applies changes back to the SceneObject."""
        
        is_3d = self.state.current_scene.is_3d if self.state.current_scene else False
        
        # 1. Base Properties
        if "name" in self.widgets:
            obj.name = self.widgets["name"].get_text()
            
        # Helper to parse vector/float input
        def parse_input(key, target_type):
            if key not in self.widgets: return None
            text = self.widgets[key].get_text()
            try:
                if target_type == "float":
                    return float(text)
                elif target_type == "vector2":
                    parts = [float(p.strip()) for p in text.split(',')][:2]
                    return Vector2(*parts) if len(parts) == 2 else None
                elif target_type == "vector3":
                    parts = [float(p.strip()) for p in text.split(',')][:3]
                    return Vector3(*parts) if len(parts) == 3 else None
            except:
                return None

        # Transform updates
        pos_type = "vector3" if is_3d else "vector2"
        pos_val = parse_input("position", pos_type)
        if pos_val: obj.position = pos_val
        
        rot_type = "vector3" if is_3d else "float"
        rot_val = parse_input("rotation", rot_type)
        if rot_type == "float" and rot_val is not None: obj.rotation = rot_val
        if rot_type == "vector3" and rot_val: obj.rotation = rot_val
        
        scale_val = parse_input("scale", pos_type)
        if scale_val: obj.scale = scale_val
        
        # 2. Component Properties
        if obj.components:
            for i, comp_data in enumerate(obj.components):
                comp_type = comp_data.get("type")
                schema_func = COMPONENT_SCHEMAS.get(comp_type)
                if schema_func:
                    comp_schema = schema_func()
                    for key, prop_schema in comp_schema.items():
                        widget_key = f"comp_{i}_{key}"
                        widget = self.widgets.get(widget_key)
                        
                        if widget:
                            if prop_schema['type'] == 'boolean':
                                comp_data[key] = widget.get_value()
                            elif prop_schema['type'] in ['string', 'asset_selector', 'dropdown']:
                                comp_data[key] = widget.get_value() # get_value for string/dropdown
                            elif prop_schema['type'] in ['float', 'int']:
                                try:
                                    comp_data[key] = float(widget.get_text()) # Cast
                                except:
                                    pass
                            # Vector types would require complex parsing here as well
        
        # Save changes to the project state (delegated to editor main loop or autosave)
        # FileUtils.log_message(f"Applied changes to {obj.name}.")


    def _show_add_component_menu(self):
        """Toggles the visibility of the Add Component dropdown menu."""
        
        if self.add_component_menu:
            self.add_component_menu = None
            return

        # Get list of available component types not already on the object
        available_comps = []
        current_obj = self.state.get_object_by_uid(self.state.selected_object_uid)
        if current_obj:
            existing_types = {c.get("type") for c in current_obj.components}
            available_comps = [t for t in COMPONENT_SCHEMAS.keys() if t not in existing_types]
            
            if not available_comps:
                FileUtils.log_warning("No new components available to add.")
                return

            # Create a mock dropdown/window for component selection
            menu_rect = pygame.Rect(self.add_component_button.rect.x, self.add_component_button.rect.y - 150, 
                                    self.add_component_button.rect.width, 150)
            self.add_component_menu = Dropdown(menu_rect, available_comps, action=self._add_selected_component)


    def _add_selected_component(self, component_type: str):
        """Action: Adds the selected component type to the object."""
        obj = self.state.get_object_by_uid(self.state.selected_object_uid)
        if obj and component_type:
            
            # Get default values from schema (mocking default data)
            default_data = {"type": component_type}
            schema_func = COMPONENT_SCHEMAS.get(component_type)
            if schema_func:
                schema = schema_func()
                for key, prop_schema in schema.items():
                    default_data[key] = prop_schema.get("default", 
                                                         0.0 if prop_schema['type'] in ['float', 'int'] else 
                                                         False if prop_schema['type'] == 'boolean' else 
                                                         "" if prop_schema['type'] in ['string', 'asset_selector'] else 
                                                         [0, 0, 0] if prop_schema['type'] == 'vector3' else 
                                                         [0, 0] if prop_schema['type'] == 'vector2' else 
                                                         None)
                    
            obj.add_component(default_data)
            self.add_component_menu = None # Close menu
            self.current_object_uid = None # Force widget rebuild on next draw
            FileUtils.log_message(f"Added component '{component_type}' to {obj.name}")


    def _delete_component(self, component_index: int):
        """Action: Deletes the component at the given index from the selected object."""
        obj = self.state.get_object_by_uid(self.state.selected_object_uid)
        if obj and 0 <= component_index < len(obj.components):
            comp_type = obj.components[component_index]["type"]
            del obj.components[component_index]
            self.current_object_uid = None # Force widget rebuild
            FileUtils.log_message(f"Removed component '{comp_type}' from {obj.name}")


    def draw(self, surface: pygame.Surface, theme: str):
        """Draws the inspector panel and all its widgets."""
        
        # 1. Update Layout (Handles window resizing implicitly)
        self.rect = self.window.rect # Ensure the panel's rect is set by the manager
        self._update_ui_rects()
        
        # 2. Draw Window Frame
        self.window.draw(surface, theme)
        content_rect = self.content_rect
        
        obj = self.state.get_object_by_uid(self.state.selected_object_uid)
        
        # Check if selection changed or no object is selected
        if not obj:
            if self.current_object_uid is not None:
                self.widgets.clear()
                self.current_object_uid = None
            Label(content_rect, "No object selected.").draw(surface, theme)
            return

        # 3. Widget Rebuild & State Sync
        if obj.uid != self.current_object_uid:
            self._build_widgets(obj)
            self.current_object_uid = obj.uid
        else:
            # Apply changes from last frame's input to the object state
            self._apply_widget_changes(obj) 

        # 4. Draw Scrollbar
        self.scrollbar.draw(surface, theme)
        scroll_offset = self.scrollbar.get_scroll_offset()
        
        # 5. Draw Widgets
        
        # Clip rendering to the content area (above the Add Component button)
        clip_rect = content_rect.copy()
        clip_rect.height -= self.add_component_button.rect.height + self.PADDING * 2
        surface.set_clip(clip_rect)
        
        for key, widget in self.widgets.items():
            # Translate widget position by scroll offset
            if hasattr(widget, 'rect'):
                widget.rect.y -= scroll_offset
                
            widget.draw(surface, theme)
            
            # Reset rect position after drawing for next frame's input check
            if hasattr(widget, 'rect'):
                widget.rect.y += scroll_offset

        surface.set_clip(None)
        
        # 6. Draw "Add Component" button (always at the bottom)
        self.add_component_button.draw(surface, theme)
        
        # 7. Draw Add Component Menu (if open)
        if self.add_component_menu:
            self.add_component_menu.draw(surface, theme)