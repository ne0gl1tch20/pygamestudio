# editor/editor_plugin_browser.py
import pygame
import sys
import os
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.plugin_manager import PluginManager
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Window, Label, Button, Scrollbar
    from engine.utils.color import Color
except ImportError as e:
    print(f"[EditorPluginBrowser Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): self.plugin_manager = self
    class PluginManager:
        def __init__(self, state): pass
        def get_plugin_list(self): 
            return {"plugin_a": {"is_loaded": True, "version": "1.0", "author": "Mock"}, "plugin_b": {"is_loaded": False, "version": "0.5", "author": "Mock"}}
        def load_plugin(self, uid): FileUtils.log_message(f"Mock Load: {uid}")
        def unload_plugin(self, uid): FileUtils.log_message(f"Mock Unload: {uid}")
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[EPB-INFO] {msg}")
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
    class Scrollbar:
        def __init__(self, rect, max_scroll): self.rect = rect; self.max_scroll = max_scroll
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_scroll_offset(self): return 0
    class Color:
        @staticmethod
        def green(): return (0, 255, 0)
        @staticmethod
        def red(): return (255, 0, 0)
        @staticmethod
        def white(): return (255, 255, 255)


class EditorPluginBrowser(Window):
    """
    Floating window for viewing, loading, and unloading plugins.
    (This is a specialized version of the generic one in editor_ui.py)
    """
    ITEM_HEIGHT = 40
    PADDING = 10
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Plugin Manager 🔌"):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.plugin_manager: PluginManager = self.state.plugin_manager
        self.widgets: Dict[str, Any] = {}
        self.scrollbar = None
        self.font = pygame.font.Font(None, 18)
        self._update_ui_rects()
        self._build_widgets()

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements."""
        self.window.rect = self.rect 
        content = self.window.get_content_rect()
        
        # Scrollbar setup
        max_scroll = 1000 # Placeholder
        scroll_rect = pygame.Rect(content.right - 10, content.y + 30, 10, content.height - 40)
        self.scrollbar = Scrollbar(scroll_rect, max_scroll)
        
    def _build_widgets(self):
        """Dynamically generates a list of buttons/labels for all plugins."""
        self.widgets.clear()
        
        plugins = self.plugin_manager.get_plugin_list()
        content = self.window.get_content_rect()
        x, y = content.x + self.PADDING, content.y + self.PADDING
        w = content.width - 2 * self.PADDING - self.scrollbar.rect.width
        
        y = y + 20 # Space for header

        for i, (p_id, data) in enumerate(plugins.items()):
            is_loaded = data.get('is_loaded', False)
            btn_text = "🔌 Load" if not is_loaded else "🛑 Unload"
            
            # Label: Plugin Name / Version / Author
            label_rect = pygame.Rect(x, y + i * self.ITEM_HEIGHT, w - 100, self.ITEM_HEIGHT)
            label_text = f"{p_id} | v{data.get('version', 'N/A')} | by {data.get('author', 'Unknown')}"
            self.widgets[f'label_{p_id}'] = Label(label_rect, label_text, alignment="left")
            
            # Button: Load/Unload
            btn_rect = pygame.Rect(content.right - 10 - self.scrollbar.rect.width - 100, y + i * self.ITEM_HEIGHT + 5, 90, 30)
            btn = Button(btn_rect, btn_text, action=lambda p=p_id, l=is_loaded: self._toggle_plugin(p, l))
            btn.is_toggled = is_loaded
            self.widgets[f'btn_{p_id}'] = btn
        
        # Update scrollbar max
        total_height = len(plugins) * self.ITEM_HEIGHT
        self.scrollbar.max_scroll = max(0, total_height - (content.height - 40))


    def _toggle_plugin(self, plugin_id: str, is_loaded: bool):
        """Action: Loads or unloads a plugin."""
        if is_loaded:
            self.plugin_manager.unload_plugin(plugin_id)
        else:
            self.plugin_manager.load_plugin(plugin_id)
            
        # Rebuild widgets to update toggled state
        self._build_widgets()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = super().handle_event(event)
        self._update_ui_rects()
        
        # Handle scrollbar
        if self.scrollbar.handle_event(event): consumed = True
        scroll_offset = self.scrollbar.get_scroll_offset()
        
        for widget in self.widgets.values():
            if hasattr(widget, 'rect'): widget.rect.y -= scroll_offset # Apply scroll for input check
            if hasattr(widget, 'handle_event') and widget.handle_event(event): consumed = True
            if hasattr(widget, 'rect'): widget.rect.y += scroll_offset # Restore rect

        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        super().draw(surface, theme)
        content = self.window.get_content_rect()
        colors = _get_theme_colors(theme)
        
        # Rebuild and draw header
        Label(pygame.Rect(content.x + self.PADDING, content.y + 5, content.width - 20, 20), "Available Plugins", text_color=colors['accent'], alignment="left").draw(surface, theme)
        
        # 1. Draw Widgets
        surface.set_clip(pygame.Rect(content.x, content.y + 30, content.width - 10, content.height - 40))
        scroll_offset = self.scrollbar.get_scroll_offset()
        
        for widget in self.widgets.values():
            if hasattr(widget, 'rect'): widget.rect.y -= scroll_offset
            if hasattr(widget, 'draw'): widget.draw(surface, theme)
            if hasattr(widget, 'rect'): widget.rect.y += scroll_offset

        surface.set_clip(None)
        
        # 2. Draw Scrollbar
        self.scrollbar.draw(surface, theme)