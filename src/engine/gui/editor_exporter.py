# editor/editor_exporter.py
import pygame
import sys
import os
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.export_manager import ExportManager
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Window, Label, Button, Dropdown, TextInput
except ImportError as e:
    print(f"[EditorExporter Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): 
            self.export_manager = self
            self.current_project_path = "path/to/project"
            self.config = self
            self.project_settings = {"game_title": "Mock Game"}
    class ExportManager:
        def __init__(self, state): self.EXPORT_TYPES = {"desktop": "Desktop Build", "web_html5": "Web Stub"}
        default_export_path = os.path.join(FileUtils.get_engine_root_path(), 'builds')
        def export_project(self, *args): FileUtils.log_message("Mock Export"); return True
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[EEX-INFO] {msg}")
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def get_content_rect(self): return self.rect
        def is_open(self): return True
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect; self.text = text
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
    class TextInput:
        def __init__(self, rect, text, **kwargs): self.rect = rect; self.text = text
        def get_text(self): return self.text
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass


class EditorExportWindow(Window):
    """
    Specialized window for building and exporting the game project.
    (This is a specialized version of the generic one in editor_ui.py)
    """
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Export Build 🚀"):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.export_manager: ExportManager = self.state.export_manager
        self.widgets: Dict[str, Any] = {}
        self._update_ui_rects()
        self.widgets = self._create_widgets()

    def _create_widgets(self):
        widgets = {}
        content = self.get_content_rect()
        x, y = content.x + 10, content.y + 10
        w, h = content.width - 20, 24
        
        widgets['label_project'] = Label(pygame.Rect(x, y, w, h), f"Project: {self.state.config.project_settings.get('game_title', 'N/A')}", alignment="left")
        y += h + 10
        
        widgets['header_target'] = Label(pygame.Rect(x, y, w, h), "Export Target", text_color=self.state.get_theme_color('accent'))
        y += h + 5
        
        widgets['label_type'] = Label(pygame.Rect(x, y, 150, h), "Target Platform:", alignment="left")
        widgets['export_type'] = Dropdown(pygame.Rect(x + 160, y, 200, h), list(self.export_manager.EXPORT_TYPES.keys()))
        y += h + 10
        
        widgets['label_path'] = Label(pygame.Rect(x, y, 150, h), "Export Path:", alignment="left")
        widgets['export_path'] = TextInput(pygame.Rect(x + 160, y, w - 160, h), self.export_manager.default_export_path)
        y += h + 20
        
        widgets['export_btn'] = Button(pygame.Rect(x, y, w, 40), "🚀 Start Export", action=self._start_export)
        
        return widgets

    def _start_export(self):
        """Action: Calls the ExportManager to build the game."""
        export_type = self.widgets['export_type'].get_value()
        export_path = self.widgets['export_path'].get_text()
        
        if self.state.export_manager:
            self.state.export_manager.export_project(export_type, export_path)
            
    def _update_ui_rects(self):
        self.window.rect = self.rect 

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        consumed = super().handle_event(event)
        self._update_ui_rects()
        for widget in self.widgets.values():
            if hasattr(widget, 'handle_event') and widget.handle_event(event): consumed = True
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return
        super().draw(surface, theme)
        for widget in self.widgets.values():
            if hasattr(widget, 'draw'): widget.draw(surface, theme)