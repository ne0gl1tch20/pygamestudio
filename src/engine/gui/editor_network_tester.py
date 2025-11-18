# editor/editor_network_tester.py
import pygame
import sys
import os
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.network_manager import NetworkManager
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Window, Label, Button, TextInput
    from engine.utils.color import Color
except ImportError as e:
    print(f"[EditorNetworkTester Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): 
            self.network_manager = self
            self.config = self
            self.network_settings = {"default_host": "127.0.0.1", "default_port": 5555}
    class NetworkManager:
        def __init__(self, state): pass
        def is_hosting(self): return False
        def is_client(self): return False
        def start_host(self, host, port): FileUtils.log_message("Mock Host Start"); return True
        def stop(self): FileUtils.log_message("Mock Stop Net"); return True
        def start_client(self, host, port): FileUtils.log_message("Mock Client Start"); return True
        def send_chat_message(self, msg): FileUtils.log_message(f"Mock Chat: {msg}")
        clients = {}
        host, port, client_id = "127.0.0.1", 5555, None
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[ENT-INFO] {msg}")
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
    class TextInput:
        def __init__(self, rect, text, **kwargs): self.rect = rect; self.text = text
        def get_text(self): return self.text
        def set_text(self, text): self.text = text
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass


class EditorNetworkTester(Window):
    """
    Specialized window for hosting, joining, and testing multiplayer connections.
    (This is a specialized version of the generic one in editor_ui.py)
    """
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Multiplayer Test 🌐"):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.network_manager: NetworkManager = self.state.network_manager
        self.widgets: Dict[str, Any] = {}
        self._update_ui_rects()
        self.widgets = self._create_widgets() # Final build of widgets

    def _create_widgets(self):
        widgets = {}
        content = self.get_content_rect()
        x, y = content.x + 10, content.y + 10
        w, h = content.width - 20, 24
        
        # Host/Server Controls
        widgets['header_host'] = Label(pygame.Rect(x, y, w, h), "Host / Server", text_color=self.state.get_theme_color('accent'))
        y += h + 5
        
        widgets['label_host'] = Label(pygame.Rect(x, y, 100, h), "Host IP:", alignment="left")
        widgets['host_ip'] = TextInput(pygame.Rect(x + 100, y, 150, h), self.state.config.network_settings.get("default_host", "127.0.0.1"))
        widgets['label_port'] = Label(pygame.Rect(x + 260, y, 60, h), "Port:", alignment="left")
        widgets['host_port'] = TextInput(pygame.Rect(x + 320, y, 80, h), str(self.state.config.network_settings.get("default_port", 5555)), is_numeric=True)
        y += h + 5
        
        widgets['btn_start_server'] = Button(pygame.Rect(x, y, 200, 30), "🌐 Start Host (Server)", action=lambda: self._toggle_host(True))
        widgets['btn_stop_server'] = Button(pygame.Rect(x + 210, y, 150, 30), "⏹️ Stop Server", action=lambda: self._toggle_host(False))
        y += 40
        
        # Client Controls
        widgets['header_client'] = Label(pygame.Rect(x, y, w, h), "Client / Join", text_color=self.state.get_theme_color('accent'))
        y += h + 5
        widgets['btn_start_client'] = Button(pygame.Rect(x, y, 200, 30), "🔌 Join Client", action=lambda: self._toggle_client(True))
        widgets['btn_stop_client'] = Button(pygame.Rect(x + 210, y, 150, 30), "❌ Disconnect", action=lambda: self._toggle_client(False))
        y += 40
        
        # Status
        widgets['header_status'] = Label(pygame.Rect(x, y, w, h), "Network Status", text_color=self.state.get_theme_color('accent'))
        y += h + 5
        widgets['status_label'] = Label(pygame.Rect(x, y, w, h), "Status: Idle", alignment="left")
        y += h + 5
        widgets['chat_status_label'] = Label(pygame.Rect(x, y, w, h), "Chat: ", alignment="left")
        y += h + 5
        
        # Chat Input
        widgets['chat_input'] = TextInput(pygame.Rect(x, content.bottom - 30, w - 80, 24), "", placeholder="Send Chat Message...")
        widgets['chat_send_btn'] = Button(pygame.Rect(content.right - 85, content.bottom - 30, 75, 24), "Send", action=self._send_chat)
        
        return widgets

    def _toggle_host(self, start: bool):
        host = self.widgets['host_ip'].get_text()
        port = int(self.widgets['host_port'].get_text())
        if start:
            self.network_manager.start_host(host, port)
        else:
            self.network_manager.stop()

    def _toggle_client(self, join: bool):
        host = self.widgets['host_ip'].get_text()
        port = int(self.widgets['host_port'].get_text())
        if join:
            self.network_manager.start_client(host, port)
        else:
            self.network_manager.stop()

    def _send_chat(self):
        message = self.widgets['chat_input'].get_text()
        if message:
            self.network_manager.send_chat_message(message)
            self.widgets['chat_input'].set_text("")
            
    def _update_ui_rects(self):
        self.window.rect = self.rect 

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        consumed = super().handle_event(event)
        self._update_ui_rects()
        
        # Rebuild to update dynamic button states (Start/Stop)
        # self.widgets = self._create_widgets()

        for widget in self.widgets.values():
            if hasattr(widget, 'handle_event') and widget.handle_event(event): consumed = True
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return
        super().draw(surface, theme)
        
        # Update dynamic status label text
        nm = self.network_manager
        
        # Update chat status (Mock: last 3 log lines that contain CHAT)
        chat_logs = [l for l in FileUtils.read_last_log_lines(FileUtils.get_log_file_path(), 20) if "[CHAT]" in l]
        chat_status = "\n".join(chat_logs[-3:])
        self.widgets['chat_status_label'].text = f"Chat: \n{chat_status}"
        
        if nm.is_hosting():
             self.widgets['status_label'].text = f"Status: HOST @ {nm.host}:{nm.port} | Clients: {len(nm.clients)}"
        elif nm.is_client():
             self.widgets['status_label'].text = f"Status: CLIENT @ {nm.host}:{nm.port} | ID: {nm.client_id if nm.client_id else 'WAITING'}"
        else:
             self.widgets['status_label'].text = "Status: Idle"

        for widget in self.widgets.values():
            if hasattr(widget, 'draw'): widget.draw(surface, theme)