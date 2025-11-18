# editor/editor_csg_modeler.py
import pygame
import sys
import os
import math
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.rendering.csg_modeler import CSGModeler, CSGNode
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Window, Label, Button, Dropdown
    from engine.utils.color import Color
    from engine.utils.vector3 import Vector3
except ImportError as e:
    print(f"[EditorCSGModeler Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): self.csg_modeler = self
        selected_object_uid = None
    class CSGModeler:
        def __init__(self, state): pass
        def get_primitive_types(self): return ['box', 'sphere']
        def get_boolean_ops(self): return ['union', 'subtract']
        def rebuild_mesh(self, node): return None
        def get_active_tree_root(self): 
            return CSGNode('subtract', 'Cutout', 'boolean', children=[CSGNode('box', 'Base', 'primitive', params={'size': 2.0}), CSGNode('sphere', 'Cut', 'primitive', params={'radius': 1.0})])
        def export_mesh(self, mesh, path): FileUtils.log_message(f"Mock Export OBJ: {path}")
    class CSGNode:
        def __init__(self, type, name, op_type, children=None, params=None, transform=None): self.type = type; self.name = name; self.op_type = op_type; self.children = children if children else []; self.params = params if params else {}
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[ECM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[ECM-ERROR] {msg}", file=sys.stderr)
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def get_content_rect(self): return self.rect
        def is_open(self): return True
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect; self.text = text
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Dropdown:
        def __init__(self, rect, options, **kwargs): self.rect = rect; self.options = options
        def get_value(self): return self.options[0]
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)
    class Vector3:
        def __init__(self, x, y, z): self.x, self.y, self.z = x, y, z


class EditorCSGModeler:
    """
    Floating window for creating and editing 3D models using Constructive Solid Geometry (CSG).
    """
    TREE_PANEL_WIDTH = 250
    NODE_HEIGHT = 40
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "CSG Modeler 🧱"):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.csg_modeler: CSGModeler = self.state.csg_modeler
        
        # State
        self.selected_node: CSGNode | None = None
        self.widgets: Dict[str, Any] = {}
        self.tree_scroll_offset = 0
        
        # UI Elements
        self.btn_rebuild = Button(pygame.Rect(0, 0, 100, 30), "🔨 Rebuild", action=self._rebuild_mesh)
        self.btn_export = Button(pygame.Rect(0, 0, 100, 30), "🚀 Export OBJ", action=self._export_mesh)
        
        self._update_ui_rects()
        self._build_widgets()

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements."""
        self.window.rect = self.rect 
        content = self.window.get_content_rect()
        
        # Tree View Rect (Left Side)
        self.tree_view_rect = pygame.Rect(content.x, content.y + 40, self.TREE_PANEL_WIDTH, content.height - 40)
        
        # Properties/Preview Rect (Right Side)
        self.props_preview_rect = pygame.Rect(content.x + self.TREE_PANEL_WIDTH, content.y, content.width - self.TREE_PANEL_WIDTH, content.height)
        
        # Buttons
        self.btn_rebuild.rect.topleft = (self.props_preview_rect.x + 10, content.y + 5)
        self.btn_export.rect.topleft = (self.props_preview_rect.x + 120, content.y + 5)
        
    def _build_widgets(self):
        """Builds widgets for the selected node's properties."""
        self.widgets.clear()
        if not self.selected_node:
            self.widgets['info'] = Label(self.props_preview_rect, "Select a CSG Node", alignment="center")
            return
            
        # Mock widgets based on selected_node.params/transform
        y = self.props_preview_rect.y + 40
        x = self.props_preview_rect.x + 10
        w = self.props_preview_rect.width - 20
        
        # Node Name
        self.widgets['name'] = TextInput(pygame.Rect(x, y, w, 24), self.selected_node.name)
        y += 30
        
        # Transform Properties (Mock Position Input)
        self.widgets['label_pos'] = Label(pygame.Rect(x, y, 80, 24), "Position:", alignment="left")
        pos_str = ', '.join(map(str, self.selected_node.transform.get('position', [0, 0, 0])))
        self.widgets['pos'] = TextInput(pygame.Rect(x + 85, y, w - 85, 24), pos_str, is_numeric=True)
        y += 30
        
        # Primitive Parameters (Mock Size Slider)
        if self.selected_node.op_type == 'primitive':
            size = self.selected_node.params.get('size', 1.0)
            self.widgets['label_size'] = Label(pygame.Rect(x, y, 80, 24), "Size:", alignment="left")
            self.widgets['size'] = Slider(pygame.Rect(x + 85, y, w - 85, 24), min_val=0.1, max_val=10.0, initial_val=size)
            y += 30
        
    def _rebuild_mesh(self):
        """Action: Rebuilds the mesh from the current tree."""
        # Sync widget changes back to the selected node before rebuilding
        self._sync_widgets_to_node()
        
        # Rebuild the final mesh
        final_mesh = self.csg_modeler.rebuild_mesh()
        
        if final_mesh:
            FileUtils.log_message("CSG Mesh rebuilt successfully.")
            # Mock: Assign the new mesh to the currently selected SceneObject if one exists
            selected_obj = self.state.get_object_by_uid(self.state.selected_object_uid)
            if selected_obj and selected_obj.get_component("MeshRenderer"):
                 # Mock setting the new mesh data
                 selected_obj.get_component("MeshRenderer")["mock_mesh_data"] = final_mesh.to_dict() 
                 
    def _export_mesh(self):
        """Action: Exports the current rebuilt mesh."""
        final_mesh = self.csg_modeler.rebuild_mesh()
        if final_mesh:
            # Mock export path
            path = os.path.join(self.state.current_project_path, 'assets', 'models', 'csg_export.json')
            self.csg_modeler.export_mesh(final_mesh, path)
            
    def _sync_widgets_to_node(self):
        """Pulls values from widgets and updates the selected CSGNode object."""
        if not self.selected_node: return

        try:
            self.selected_node.name = self.widgets['name'].get_text()
            
            # Position update (Mock parsing)
            pos_text = self.widgets['pos'].get_text()
            self.selected_node.transform['position'] = [float(p.strip()) for p in pos_text.split(',')][:3]
            
            # Primitive parameters
            if self.selected_node.op_type == 'primitive':
                self.selected_node.params['size'] = self.widgets['size'].get_value()

        except Exception as e:
            FileUtils.log_warning(f"CSG Property sync error: {e}")

    def _draw_csg_tree(self, surface: pygame.Surface, content: pygame.Rect, theme: str):
        """Recursively draws the CSG operation tree."""
        pygame.draw.rect(surface, self.state.get_theme_color('primary'), content, 0)
        
        # Draw header/controls (New Primitive, New Boolean)
        self._draw_tree_node_recursive(surface, self.csg_modeler.active_tree_root, content.x + 10, content.y + 10, theme)

    def _draw_tree_node_recursive(self, surface: pygame.Surface, node: CSGNode, x: int, y: int, theme: str, depth: int = 0) -> int:
        """Draws one node and its children in the tree view."""
        
        colors = _get_theme_colors(theme)
        
        # Node Box
        node_rect = pygame.Rect(x + depth * 15, y, self.TREE_PANEL_WIDTH - x - depth * 15, self.NODE_HEIGHT)
        
        bg_color = colors['secondary'] if node != self.selected_node else colors['accent']
        pygame.draw.rect(surface, bg_color, node_rect, 0, 5)
        
        # Icon/Label
        icon = "🔶" if node.op_type == 'primitive' else "➕" if node.type == 'union' else "➖"
        text = f"{icon} {node.name}"
        Label(pygame.Rect(node_rect.x + 5, node_rect.y, node_rect.width - 5, self.NODE_HEIGHT), text, alignment="left", text_color=Color.white().to_rgb()).draw(surface, theme)
        
        next_y = y + self.NODE_HEIGHT + 5
        
        # Recursively draw children
        for child in node.children:
            next_y = self._draw_tree_node_recursive(surface, child, x, next_y, theme, depth + 1)
            
        return next_y


    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = super().handle_event(event)
        self._update_ui_rects()
        
        # Handle buttons
        if self.btn_rebuild.handle_event(event): consumed = True
        if self.btn_export.handle_event(event): consumed = True
        
        # Handle widgets (properties panel)
        self._sync_widgets_to_node() # Sync down to node before checking for input changes
        for widget in self.widgets.values():
            if hasattr(widget, 'handle_event') and widget.handle_event(event): consumed = True

        # Handle mouse click on the tree view for selection
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.tree_view_rect.collidepoint(pygame.mouse.get_pos()):
             # Mock: Simply cycle through nodes on click (real would be a hit test)
             all_nodes = [self.csg_modeler.active_tree_root] + self.csg_modeler.active_tree_root.children
             if not self.selected_node:
                 self.selected_node = all_nodes[0]
             else:
                 try:
                     current_index = all_nodes.index(self.selected_node)
                     self.selected_node = all_nodes[(current_index + 1) % len(all_nodes)]
                 except: # Fallback if selected_node not found
                     self.selected_node = all_nodes[0]
             
             self._build_widgets() # Rebuild for new selection
             return True
             
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        super().draw(surface, theme)
        content = self.window.get_content_rect()
        
        # 1. Draw CSG Tree View (Left)
        self._draw_csg_tree(surface, self.tree_view_rect, theme)
        
        # 2. Draw Properties Panel (Right)
        pygame.draw.rect(surface, self.state.get_theme_color('primary'), self.props_preview_rect, 0)
        
        # Draw Buttons
        self.btn_rebuild.draw(surface, theme)
        self.btn_export.draw(surface, theme)
        
        # Draw Widgets
        self._build_widgets() # Rebuild/Reposition
        for widget in self.widgets.values():
            if hasattr(widget, 'draw'): widget.draw(surface, theme)
        
        # Draw 3D Preview (Mock)
        preview_area = pygame.Rect(self.props_preview_rect.x + 10, self.props_preview_rect.y + 150, self.props_preview_rect.width - 20, self.props_preview_rect.height - 160)
        pygame.draw.rect(surface, (0, 0, 0), preview_area, 0)
        Label(preview_area, "3D Mesh Preview (Mock)", text_color=Color.white().to_rgb()).draw(surface, theme)