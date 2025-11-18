# editor/editor_shader_graph.py
import pygame
import sys
import copy
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.rendering.shader_system import ShaderSystem
    from engine.gui.gui_widgets import Window, Label, Button
    from engine.utils.file_utils import FileUtils
    from engine.utils.color import Color
except ImportError as e:
    print(f"[EditorShaderGraph Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): self.shader_system = self
    class ShaderSystem:
        def __init__(self, state): pass
        def generate_shader_node_schema(self, name): 
            return {"name": name, "inputs": [{"name": "Albedo", "type": "color"}], "outputs": []}
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[ESG-INFO] {msg}")
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
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)


class EditorShaderGraph:
    """
    Floating window/tool for visually creating and editing 3D shaders 
    using a node-based graph system.
    """
    NODE_WIDTH = 120
    NODE_HEIGHT_BASE = 60
    PIN_RADIUS = 5

    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Shader Graph Editor 🔗"):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=True, movable=True)
        self.rect = rect.copy()
        
        self.font = pygame.font.Font(None, 14)
        
        # State
        self.active_shader_name = "default_lit"
        self.node_data: Dict[str, Any] = {} # {node_id: {type, pos, inputs, outputs}}
        
        # Interaction
        self.is_dragging_node = None
        self.is_dragging_connection = None # (source_node, source_pin)
        self.pan_offset = # Graph pan offset
        
        self._load_default_graph()

    def _load_default_graph(self):
        """Mocks loading a basic shader graph."""
        shader_schema = self.state.shader_system.generate_shader_node_schema(self.active_shader_name)
        
        # Mock Graph Data
        self.node_data = {
            "N1": {"type": "MaterialOutput", "pos":, "inputs": {"Albedo": {"type": "color", "connections": [{"target_node": "N2", "target_pin": "Out"}]}}},
            "N2": {"type": "TextureSampler", "pos":, "outputs": {"Out": {"type": "color", "connections": []}}},
            "N3": {"type": "PBRValue", "pos":, "outputs": {"Roughness": {"type": "float", "connections": []}}}
        }
        
        FileUtils.log_message(f"Loaded mock shader graph for: {self.active_shader_name}")

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = super().handle_event(event)
        
        mouse_pos = pygame.mouse.get_pos()
        content = self.window.get_content_rect()
        if not content.collidepoint(mouse_pos): return consumed

        # 1. Node Dragging/Connection Logic
        
        # Convert mouse pos to graph space (account for window pos and pan)
        graph_mouse_pos = (mouse_pos - content.x - self.pan_offset, 
                           mouse_pos - content.y - self.pan_offset)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check for node drag start
            for node_id, node in self.node_data.items():
                node_rect = self._get_node_rect(node, content)
                if node_rect.collidepoint(mouse_pos):
                    self.is_dragging_node = node_id
                    self._drag_offset = (mouse_pos - node_rect.x, mouse_pos - node_rect.y)
                    return True
            
            # Check for pin drag start (connection)
            # This is complex in a mock, so we skip detailed pin hit test

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging_node:
                self.is_dragging_node = None
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging_node:
                node = self.node_data[self.is_dragging_node]
                # Update node position (relative to window/content area)
                node['pos'] = graph_mouse_pos - (self._drag_offset - self.pan_offset) 
                node['pos'] = graph_mouse_pos - (self._drag_offset - self.pan_offset)
                return True
                
        # 2. Graph Panning (MMB)
        # Mock pan logic is in viewport, skipped here for simplicity
                
        return consumed
        
    def _get_node_rect(self, node: Dict, content_rect: pygame.Rect) -> pygame.Rect:
        """Calculates the screen-space rect for a node."""
        
        # Calculate height based on pins (Mock: max 3 pins, 15px per pin)
        num_pins = max(len(node.get('inputs', [])), len(node.get('outputs', [])))
        node_h = self.NODE_HEIGHT_BASE + num_pins * 15
        
        # Screen position (accounting for pan and window offset)
        screen_x = content_rect.x + node['pos'] + self.pan_offset
        screen_y = content_rect.y + node['pos'] + self.pan_offset
        
        return pygame.Rect(screen_x, screen_y, self.NODE_WIDTH, node_h)


    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        super().draw(surface, theme)
        content = self.window.get_content_rect()
        colors = _get_theme_colors(theme)
        
        # Draw background grid (mock)
        pygame.draw.rect(surface, colors['primary'], content, 0)
        
        # 1. Draw Connections (Simplified)
        surface.set_clip(content)
        for node_id, node in self.node_data.items():
            for pin_name, pin_data in node.get('outputs', {}).items():
                if pin_data.get('connections'):
                    source_rect = self._get_node_rect(node, content)
                    source_pos = source_rect.midright # Mock output pin location
                    
                    for conn in pin_data['connections']:
                        target_node = self.node_data.get(conn['target_node'])
                        if target_node:
                            target_rect = self._get_node_rect(target_node, content)
                            target_pos = target_rect.midleft # Mock input pin location
                            
                            # Draw a Bezier curve (mock with a straight line)
                            pygame.draw.line(surface, Color.white().to_rgb(), source_pos, target_pos, 2)

        # 2. Draw Nodes
        for node_id, node in self.node_data.items():
            node_rect = self._get_node_rect(node, content)
            
            # Draw node body
            bg_color = colors['secondary'] if node_id != self.is_dragging_node else colors['hover']
            pygame.draw.rect(surface, bg_color, node_rect, 0, 5)
            pygame.draw.rect(surface, colors['accent'], node_rect, 2, 5) # Accent border
            
            # Draw Node Title
            Label(pygame.Rect(node_rect.x, node_rect.y, node_rect.width, 20), node['type'], font=self.font).draw(surface, theme)
            
            # Draw Pins (Mock)
            # Input pins on left, Output pins on right
            
        surface.set_clip(None)