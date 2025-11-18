# editor/editor_visual_scripting.py
import pygame
import sys
import copy
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.scripting.visual_script_runtime import VisualScriptRuntime, NodeRegistry
    from engine.gui.gui_widgets import Window, Label, Button, Dropdown
    from engine.utils.file_utils import FileUtils
    from engine.utils.color import Color
    from engine.utils.vector2 import Vector2
except ImportError as e:
    print(f"[EditorVisualScripting Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        selected_object_uid = None
        def get_object_by_uid(self, uid): return None
        def __init__(self): self.visual_script_runtime = self
    class VisualScriptRuntime:
        def __init__(self, state): pass
        def initialize_script(self, obj, graph): FileUtils.log_message("Mock Init V-Script")
    class NodeRegistry:
        REGISTRY = {"StartEvent": {"metadata": {"category": "Events"}}, "SetPosition": {"metadata": {"category": "Transform"}}, "AddFloat": {"metadata": {"category": "Math"}}}
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[EVS-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[EVS-ERROR] {msg}", file=sys.stderr)
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
    class Dropdown:
        def __init__(self, rect, options, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return options
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)
    class Vector2:
        def __init__(self, x, y): self.x, self.y = x, y


class EditorVisualScripting:
    """
    Floating window/tool for creating and editing visual script node graphs.
    """
    NODE_WIDTH = 150
    ITEM_HEIGHT = 20
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Visual Scripting ⚙️"):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=True, movable=True)
        self.rect = rect.copy()
        
        self.font = pygame.font.Font(None, 14)
        
        # State
        self.active_object_uid = None
        self.script_graph: Dict[str, Any] = self._create_default_graph()
        
        # Interaction
        self.is_dragging_node = None
        self.pan_offset = Vector2(0, 0)
        self.node_menu_open = False
        
        # UI Elements
        node_types = sorted(NodeRegistry.REGISTRY.keys())
        self.node_menu_dropdown = Dropdown(pygame.Rect(0, 0, 150, 24), node_types, action=self._add_node_from_menu)
        self.btn_run = Button(pygame.Rect(0, 0, 80, 24), "▶️ Run", self.state.asset_loader.get_icon('play'), action=self._run_script)
        
        self._update_ui_rects()

    def _create_default_graph(self):
        """Initializes a basic default graph (Update -> SetPosition)."""
        return {
            "name": "DefaultScript",
            "nodes": {
                "N1": {"id": "N1", "type": "UpdateEvent", "pos":, "outputs": {"Out": {"type": "exec", "connections": [{"target_node": "N2"}]}}},
                "N2": {"id": "N2", "type": "SetPosition", "pos":, 
                       "inputs": {"Position": {"type": "vector2", "connections": [{"target_node": "N3"}]}}, 
                       "outputs": {"Out": {"type": "exec", "connections": []}}},
                "N3": {"id": "N3", "type": "FloatConstant", "pos":, "properties": {"Value": 1.0}}
            }
        }
        
    def _update_ui_rects(self):
        """Updates the rects of internal UI elements."""
        self.window.rect = self.rect 
        content = self.window.get_content_rect()
        
        # Top-right controls
        self.btn_run.rect.topright = (content.right - 10, content.y + 10)
        self.node_menu_dropdown.rect.topright = (content.right - 100, content.y + 40)
        self.node_menu_dropdown.rect.width = 150

    def set_active_object(self, obj_uid: str):
        """Sets the object whose visual script is being edited."""
        self.active_object_uid = obj_uid
        # Load script_graph from the object's VisualScript component (Mock)
        # self.script_graph = obj.get_component("VisualScript").get("graph_data") 
        self.window.open()
        FileUtils.log_message(f"Visual Scripting active for: {obj_uid}")

    def _run_script(self):
        """Action: Saves the graph and initializes the script instance in the runtime."""
        obj = self.state.get_object_by_uid(self.active_object_uid)
        if obj:
            # Save graph (Mock)
            # obj.get_component("VisualScript")["graph_data"] = self.script_graph 
            
            # Initialize in runtime
            self.state.visual_script_runtime.initialize_script(obj, self.script_graph)
            FileUtils.log_message(f"Visual Script for {obj.name} executed (Runtime Mock).")
        
    def _add_node_from_menu(self, node_type: str):
        """Action: Adds a new node to the graph from the menu selection."""
        if node_type not in NodeRegistry.REGISTRY: return
        
        # Mock position at center of view (minus pan offset)
        new_id = f"N{len(self.script_graph['nodes']) + 1}"
        new_node = {"id": new_id, "type": node_type, "pos": [-self.pan_offset.x + 200, -self.pan_offset.y + 150]}
        
        # Mock inputs/outputs based on registry (for drawing later)
        new_node['inputs'] = {"In": {"type": "exec", "connections": []}} 
        new_node['outputs'] = {"Out": {"type": "exec", "connections": []}}
        
        self.script_graph['nodes'][new_id] = new_node
        self.node_menu_dropdown.is_open_list = False
        FileUtils.log_message(f"Added node: {node_type} ({new_id})")

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = super().handle_event(event)
        self._update_ui_rects()
        
        # UI events
        if self.btn_run.handle_event(event): consumed = True
        if self.node_menu_dropdown.handle_event(event): consumed = True
        
        mouse_pos = pygame.mouse.get_pos()
        content = self.window.get_content_rect()

        # Node Dragging Logic
        if content.collidepoint(mouse_pos):
            
            # Convert mouse pos to graph space (account for window pos and pan)
            graph_mouse_pos = Vector2(mouse_pos - content.x, mouse_pos - content.y)
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check for node drag start
                for node_id, node in self.script_graph['nodes'].items():
                    node_rect = self._get_node_rect(node, content)
                    if node_rect.collidepoint(mouse_pos):
                        self.is_dragging_node = node_id
                        self._drag_offset = graph_mouse_pos - Vector2(node['pos'], node['pos'])
                        return True
                        
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.is_dragging_node = None
                
            elif event.type == pygame.MOUSEMOTION:
                if self.is_dragging_node:
                    node = self.script_graph['nodes'][self.is_dragging_node]
                    new_pos = graph_mouse_pos - self._drag_offset
                    node['pos'] = new_pos.x
                    node['pos'] = new_pos.y
                    return True
                
            # Pan Graph (MMB/Scroll)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
                self.is_panning = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 2:
                self.is_panning = False
            elif event.type == pygame.MOUSEMOTION and self.is_panning:
                mouse_dx, mouse_dy = self.state.input_manager.mouse_delta
                self.pan_offset.x += mouse_dx
                self.pan_offset.y += mouse_dy
                return True
                
        return consumed

    def _get_node_rect(self, node: Dict, content_rect: pygame.Rect) -> pygame.Rect:
        """Calculates the screen-space rect for a node."""
        
        # Calculate height based on pins/properties
        num_pins = max(len(node.get('inputs', [])), len(node.get('outputs', [])))
        node_h = self.NODE_WIDTH // 3 + max(1, num_pins) * self.ITEM_HEIGHT // 2 # Mock height calc
        
        # Screen position (accounting for pan and window offset)
        screen_x = content_rect.x + node['pos'] + self.pan_offset.x
        screen_y = content_rect.y + node['pos'] + self.pan_offset.y
        
        return pygame.Rect(screen_x, screen_y, self.NODE_WIDTH, node_h)


    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        super().draw(surface, theme)
        content = self.window.get_content_rect()
        colors = _get_theme_colors(theme)
        
        # Draw background grid (mock)
        grid_color = colors['primary']
        pygame.draw.rect(surface, grid_color, content, 0)
        
        # Draw all nodes and connections
        surface.set_clip(content)
        
        # 1. Draw Connections (Simplified)
        for node_id, node in self.script_graph['nodes'].items():
            source_rect = self._get_node_rect(node, content)
            
            for pin_name, pin_data in node.get('outputs', {}).items():
                for conn in pin_data.get('connections', []):
                    target_node = self.script_graph['nodes'].get(conn['target_node'])
                    if target_node:
                        target_rect = self._get_node_rect(target_node, content)
                        # Mock connection line
                        pygame.draw.line(surface, Color.white().to_rgb(), source_rect.midright, target_rect.midleft, 2)
                        

        # 2. Draw Nodes
        for node_id, node in self.script_graph['nodes'].items():
            node_rect = self._get_node_rect(node, content)
            
            # Draw node body
            bg_color = colors['secondary'] if node_id != self.is_dragging_node else colors['hover']
            pygame.draw.rect(surface, bg_color, node_rect, 0, 5)
            pygame.draw.rect(surface, colors['accent'], node_rect, 2, 5) 
            
            # Draw Node Title
            Label(pygame.Rect(node_rect.x, node_rect.y, node_rect.width, self.ITEM_HEIGHT), node['type'], font=self.font).draw(surface, theme)
            
        surface.set_clip(None)
        
        # 3. Draw UI Controls (on top)
        self.btn_run.draw(surface, theme)
        self.node_menu_dropdown.draw(surface, theme)

# Mock _get_theme_colors for standalone testing
def _get_theme_colors(theme: str):
    if theme == 'dark':
        return {
            "primary": (50, 50, 50), "secondary": (70, 70, 70), "hover": (90, 90, 90), 
            "accent": (50, 150, 255), "text": (200, 200, 200), "text_disabled": (120, 120, 120)
        }
    else:
        return {
            "primary": (230, 230, 230), "secondary": (210, 210, 210), "hover": (190, 190, 190), 
            "accent": (0, 100, 200), "text": (50, 50, 50), "text_disabled": (150, 150, 150)
        }