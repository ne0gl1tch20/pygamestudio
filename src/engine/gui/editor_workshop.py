# editor/editor_workshop.py
import pygame
import sys
import os
import math
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.workshop_manager import WorkshopManager
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Window, Label, Button, Scrollbar, TextInput
    from engine.utils.color import Color
except ImportError as e:
    print(f"[EditorWorkshop Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): self.workshop_manager = self; self.current_project_path = "path/to/project"
    class WorkshopManager:
        def __init__(self, state): pass
        def scan_workshop(self): pass
        def get_available_items(self): 
            return {"item_1": {"name": "Demo Game", "author": "Me", "rating": 4.5, "download_count": 10}, "item_2": {"name": "A Shader Pack", "author": "You", "rating": 3.0, "download_count": 5}}
        def upload_project(self, path, tags, desc): FileUtils.log_message("Mock Upload")
        def download_and_import(self, uid): FileUtils.log_message(f"Mock Download: {uid}")
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[EWS-INFO] {msg}")
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
    class TextInput:
        def __init__(self, rect, text, **kwargs): self.rect = rect; self.text = text
        def get_text(self): return self.text
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)


class EditorWorkshopBrowser(Window):
    """
    Specialized window for browsing, uploading, and downloading Workshop items.
    (This is a specialized version of the generic one in editor_ui.py)
    """
    ITEM_HEIGHT = 60
    PADDING = 10
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Workshop Browser 🛠️"):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.workshop_manager: WorkshopManager = self.state.workshop_manager
        
        self.active_tab = 'browse' # 'browse' or 'upload'
        self.widgets: Dict[str, Any] = {}
        self.scrollbar = None
        self.font = pygame.font.Font(None, 18)
        
        self._update_ui_rects()
        self._build_widgets()

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements."""
        self.window.rect = self.rect 
        content = self.window.get_content_rect()
        
        # Tabs
        self.btn_browse = Button(pygame.Rect(content.x + 10, content.y + 10, 100, 30), "Browse", action=lambda: self._set_tab('browse'))
        self.btn_upload = Button(pygame.Rect(content.x + 120, content.y + 10, 150, 30), "Upload Project", action=lambda: self._set_tab('upload'))
        
        # Content Area
        self.content_area_rect = pygame.Rect(content.x + 10, content.y + 50, content.width - 20, content.height - 60)
        
        # Scrollbar setup
        scroll_rect = pygame.Rect(content.right - 10, self.content_area_rect.y, 10, self.content_area_rect.height)
        self.scrollbar = Scrollbar(scroll_rect, 0)

    def _set_tab(self, tab: str):
        """Switches the active tab and rebuilds widgets."""
        self.active_tab = tab
        self._build_widgets()
        self.workshop_manager.scan_workshop()
        self.scrollbar.set_scroll_offset(0)
        FileUtils.log_message(f"Workshop tab switched to: {tab}")

    def _build_widgets(self):
        """Generates all widgets for the current active tab."""
        self.widgets.clear()
        content = self.content_area_rect
        x, y = content.x + self.PADDING, content.y + self.PADDING
        w = content.width - 2 * self.PADDING - self.scrollbar.rect.width
        
        if self.active_tab == 'browse':
            self._build_browse_widgets(x, y, w)
        elif self.active_tab == 'upload':
            self._build_upload_widgets(x, y, w)
            
        # Update scrollbar max
        total_height = y + self.PADDING - self.content_area_rect.y
        self.scrollbar.max_scroll = max(0, total_height - self.content_area_rect.height + self.PADDING)


    def _build_browse_widgets(self, x_start, y_start, width):
        """Builds widgets for the 'Browse' tab (list of available items)."""
        y = y_start
        items = self.workshop_manager.get_available_items().items()
        
        for p_id, data in items:
            # Item Container Rect
            item_rect = pygame.Rect(x_start, y, width, self.ITEM_HEIGHT)
            
            # Label: Name / Author / Rating
            name_lbl = Label(pygame.Rect(x_start + 5, y + 5, width - 150, 20), 
                             f"{data.get('name', 'N/A')} by {data.get('author', 'Unknown')}")
            rating_lbl = Label(pygame.Rect(x_start + 5, y + 25, width - 150, 20), 
                               f"Rating: {data.get('rating', 'N/A')} ⭐ | Downloads: {data.get('download_count', 0)}")
            
            # Button: Download
            btn_download = Button(pygame.Rect(item_rect.right - 120, y + 15, 100, 30), 
                                  "⬇️ Download", action=lambda uid=p_id: self._download_item(uid))
            
            self.widgets[f'item_rect_{p_id}'] = item_rect # For drawing box
            self.widgets[f'name_lbl_{p_id}'] = name_lbl
            self.widgets[f'rating_lbl_{p_id}'] = rating_lbl
            self.widgets[f'btn_dl_{p_id}'] = btn_download
            
            y += self.ITEM_HEIGHT + 5

    def _build_upload_widgets(self, x_start, y_start, width):
        """Builds widgets for the 'Upload' tab."""
        y = y_start
        
        widgets['label_desc'] = Label(pygame.Rect(x_start, y, 200, 24), "Description:", alignment="left")
        widgets['desc_input'] = TextInput(pygame.Rect(x_start + 10, y + 25, width - 20, 100), "Describe your creation...")
        y += 135
        
        widgets['label_tags'] = Label(pygame.Rect(x_start, y, 200, 24), "Tags (comma separated):", alignment="left")
        widgets['tags_input'] = TextInput(pygame.Rect(x_start + 10, y + 25, width - 20, 24), "game, asset, script")
        y += 60
        
        widgets['btn_upload_final'] = Button(pygame.Rect(x_start, y, width, 40), 
                                             "⬆️ Upload Current Project", action=self._upload_project)

    def _download_item(self, item_id: str):
        """Action: Downloads and imports a workshop item."""
        if self.workshop_manager.download_and_import(item_id):
            FileUtils.log_message(f"Item {item_id} imported successfully.")
        
    def _upload_project(self):
        """Action: Uploads the current project as a workshop item."""
        desc = self.widgets['desc_input'].get_text()
        tags_str = self.widgets['tags_input'].get_text()
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]
        
        if self.state.current_project_path:
            self.workshop_manager.upload_project(self.state.current_project_path, tags, desc)
        else:
            FileUtils.log_error("No project loaded to upload.")


    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = super().handle_event(event)
        self._update_ui_rects()
        
        # Tabs
        if self.btn_browse.handle_event(event): consumed = True
        if self.btn_upload.handle_event(event): consumed = True
        
        # Scrollbar
        if self.scrollbar.handle_event(event): consumed = True
        scroll_offset = self.scrollbar.get_scroll_offset()
        
        # Widgets
        for key, widget in self.widgets.items():
            if key.startswith('item_rect_') or key.startswith('label_'): continue
            
            if hasattr(widget, 'rect'): widget.rect.y -= scroll_offset
            if hasattr(widget, 'handle_event') and widget.handle_event(event): consumed = True
            if hasattr(widget, 'rect'): widget.rect.y += scroll_offset

        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        super().draw(surface, theme)
        colors = _get_theme_colors(theme)
        
        # Tabs
        self.btn_browse.is_toggled = (self.active_tab == 'browse')
        self.btn_upload.is_toggled = (self.active_tab == 'upload')
        self.btn_browse.draw(surface, theme)
        self.btn_upload.draw(surface, theme)
        
        # Content Background
        pygame.draw.rect(surface, colors['primary'], self.content_area_rect, 0)
        
        # Draw Scrollbar
        self.scrollbar.draw(surface, theme)

        # Draw Widgets
        surface.set_clip(self.content_area_rect.inflate(-10, -10))
        scroll_offset = self.scrollbar.get_scroll_offset()
        
        if self.active_tab == 'browse':
            for key, widget in self.widgets.items():
                if key.startswith('item_rect_'):
                    # Draw item box
                    rect = widget.copy()
                    rect.y -= scroll_offset
                    pygame.draw.rect(surface, colors['secondary'], rect, 0, 5)
                elif hasattr(widget, 'rect'):
                    widget.rect.y -= scroll_offset
                    widget.draw(surface, theme)
                    widget.rect.y += scroll_offset
        else: # Upload tab
            for widget in self.widgets.values():
                if hasattr(widget, 'draw'): widget.draw(surface, theme)
                
        surface.set_clip(None)
