# editor/editor_ui.py
import pygame
import sys
from typing import Dict, Any, List, Callable

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.gui.topbar import TopBar
    from engine.gui.dock_panels import DockPanelManager
    from engine.gui.gui_widgets import Window, Button, Label, TextInput, Checkbox
    from editor.editor_tutorial import EditorTutorial
except ImportError as e:
    print(f"[EditorUI Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): 
            self.ui_state = {"show_settings": False, "show_help": False, "show_export": False, "show_tutorial": False}
            self.config = self
            self.editor_settings = {"screen_width": 1280, "screen_height": 720, "theme": "dark"}
            self.current_project_path = ""
            self.export_manager = self
            self.network_manager = self
            self.workshop_manager = self
            self.plugin_manager = self
            self.save_load_manager = self
        def set_setting(self, *args): pass
        def get_setting(self, *args): return 'dark'
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[EUI-INFO] {msg}")
    class TopBar:
        def __init__(self, state, dock_manager): self.state = state
        def handle_event(self, event): return False
        def draw(self, surface): pass
        HEIGHT = 36
    class DockPanelManager:
        def __init__(self, state, height): self.state = state; self.viewport_rect = pygame.Rect(0, height, 1280, 720-height)
        def handle_event(self, event): return False
        def draw(self, surface): pass
        def toggle_panel(self, key): self.state.ui_state[key] = not self.state.ui_state.get(key, False)
        def register_plugin_panel(self, *args): pass
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect; self.title=title
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def is_open(self): return self.state.ui_state.get(self.title, False)
        def get_content_rect(self): return self.rect
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
    class TextInput:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_text(self): return "mock"
    class Checkbox:
        def __init__(self, rect, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return True
    class EditorTutorial:
        def __init__(self, state): pass
        def handle_event(self, event): return False
        def draw(self, surface): pass
        def is_active(self): return self.state.ui_state.get("show_tutorial", False)
        def start_tutorial(self): self.state.ui_state["show_tutorial"] = True

# --- Editor Window Classes (Required by Topbar.py and Dock_panels.py) ---

class EditorSettingsWindow(Window):
    """Floating window for editing Editor-level and Project-level settings."""
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.widgets = self._create_widgets()
        
    def _create_widgets(self):
        """Generates widgets based on EngineConfig settings."""
        widgets = {}
        content_rect = self.get_content_rect()
        y = content_rect.y + 10
        x = content_rect.x + 10
        w = content_rect.width - 20
        h = 24
        
        # Theme Setting
        widgets['label_theme'] = Label(pygame.Rect(x, y, 150, h), "Editor Theme:", alignment="left")
        widgets['theme'] = Dropdown(pygame.Rect(x + 160, y, w - 160, h), ["dark", "light"], initial_selection=self.state.config.editor_settings.get('theme', 'dark'), action=self._update_theme)
        y += h + 5
        
        # Resolution Setting (Editor)
        editor_w = self.state.config.editor_settings.get('screen_width', 1280)
        editor_h = self.state.config.editor_settings.get('screen_height', 720)
        widgets['label_res'] = Label(pygame.Rect(x, y, 150, h), "Editor Resolution:", alignment="left")
        widgets['res_w'] = TextInput(pygame.Rect(x + 160, y, 80, h), str(editor_w), is_numeric=True)
        widgets['res_h'] = TextInput(pygame.Rect(x + 245, y, 80, h), str(editor_h), is_numeric=True)
        y += h + 5

        # Autosave Interval
        autosave = self.state.config.editor_settings.get('autosave_interval_minutes', 5)
        widgets['label_autosave'] = Label(pygame.Rect(x, y, 150, h), "Autosave (min):", alignment="left")
        widgets['autosave'] = TextInput(pygame.Rect(x + 160, y, 80, h), str(autosave), is_numeric=True)
        y += h + 10
        
        # Project-level Settings (Mock a few for persistence demo)
        widgets['header_proj'] = Label(pygame.Rect(x, y, w, h), "Project Settings (Saved in project.json)", text_color=self.state.get_theme_color('accent'))
        y += h + 5
        
        # Network Port
        net_port = self.state.config.project_settings.get('network_port', 5555)
        widgets['label_net_port'] = Label(pygame.Rect(x, y, 150, h), "Network Port:", alignment="left")
        widgets['net_port'] = TextInput(pygame.Rect(x + 160, y, 80, h), str(net_port), is_numeric=True)
        y += h + 5
        
        # Max Players
        max_p = self.state.config.project_settings.get('max_players', 4)
        widgets['label_max_p'] = Label(pygame.Rect(x, y, 150, h), "Max Players:", alignment="left")
        widgets['max_p'] = TextInput(pygame.Rect(x + 160, y, 80, h), str(max_p), is_numeric=True)
        y += h + 5
        
        # Save Button
        widgets['save_btn'] = Button(pygame.Rect(content_rect.right - 100, content_rect.bottom - 30, 80, 24), 
                                     "Apply & Save", action=self._apply_and_save)

        return widgets
        
    def _update_theme(self, new_theme: str):
        """Action: Updates the editor theme."""
        self.state.config.set_setting('editor_settings', 'theme', new_theme)
        self.state.config.save_config()
        FileUtils.log_message(f"Theme set to {new_theme}.")

    def _apply_and_save(self):
        """Action: Applies all settings changes and saves configurations."""
        try:
            # Editor Settings
            new_w = int(self.widgets['res_w'].get_text())
            new_h = int(self.widgets['res_h'].get_text())
            new_autosave = int(self.widgets['autosave'].get_text())
            
            self.state.config.set_setting('editor_settings', 'screen_width', new_w)
            self.state.config.set_setting('editor_settings', 'screen_height', new_h)
            self.state.config.set_setting('editor_settings', 'autosave_interval_minutes', new_autosave)
            
            # Project Settings
            new_net_port = int(self.widgets['net_port'].get_text())
            new_max_p = int(self.widgets['max_p'].get_text())
            
            self.state.config.set_setting('project_settings', 'network_port', new_net_port)
            self.state.config.set_setting('project_settings', 'max_players', new_max_p)
            
            # Save to disk
            self.state.config.save_config()
            FileUtils.log_message("Settings applied and saved successfully.")
            
            # NOTE: Changing editor resolution requires screen re-initialization in main loop (outside this class)
            
        except ValueError:
            FileUtils.log_error("Invalid input in settings panel. Please enter valid numbers.")
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.state.ui_state.get('settings_window', False): return False
        
        consumed = super().handle_event(event)
        
        # Update widgets rects in case of dragging
        self._update_widgets_rects()
        
        for widget in self.widgets.values():
            if hasattr(widget, 'handle_event') and widget.handle_event(event):
                consumed = True
                
        return consumed
        
    def _update_widgets_rects(self):
        """Re-positions widgets based on window dragging/resizing (mocked)."""
        # Simple re-initialization mock
        self.widgets = self._create_widgets()

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.state.ui_state.get('settings_window', False): return
        
        super().draw(surface, theme)
        
        for widget in self.widgets.values():
            if hasattr(widget, 'draw'):
                widget.draw(surface, theme)


class EditorHelpTutorialWindow(Window):
    """Floating window for Help documentation and First-Time Tutorial."""
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.tutorial = EditorTutorial(state)
        
        self.btn_start_tutorial = Button(pygame.Rect(0, 0, 150, 30), "Replay Tutorial", action=self._start_tutorial)
        self.search_input = TextInput(pygame.Rect(0, 0, 200, 24), "Search Help...")
        self.content_label = Label(pygame.Rect(0, 0, 500, 300), "Welcome to Pygame Studio V4! Search or start the tutorial.", alignment="left")
        
        self._update_ui_rects()
        
    def _start_tutorial(self):
        """Action: Starts the step-by-step tutorial."""
        self.tutorial.start_tutorial()
        
    def _update_ui_rects(self):
        content = self.get_content_rect()
        self.btn_start_tutorial.rect.topleft = (content.x + 10, content.y + 10)
        self.search_input.rect.topleft = (content.x + 180, content.y + 16)
        self.content_label.rect.topleft = (content.x + 10, content.y + 50)
        self.content_label.rect.width = content.width - 20
        self.content_label.rect.height = content.height - 60

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.state.ui_state.get('help_tutorial_window', False): return False
        
        consumed = super().handle_event(event)
        
        # Update widget rects
        self._update_ui_rects()
        
        if self.btn_start_tutorial.handle_event(event): consumed = True
        if self.search_input.handle_event(event): consumed = True
        
        # Pass to tutorial overlay handler
        if self.tutorial.is_active() and self.tutorial.handle_event(event):
            consumed = True
            
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.state.ui_state.get('help_tutorial_window', False): return
        
        super().draw(surface, theme)
        
        self.btn_start_tutorial.draw(surface, theme)
        self.search_input.draw(surface, theme)
        self.content_label.draw(surface, theme) # Draws documentation content
        
        # Draw the tutorial overlay if active
        if self.tutorial.is_active():
            self.tutorial.draw(surface)


class EditorExportWindow(Window):
    """Floating window for building and exporting the game project."""
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        
        self.widgets = self._create_widgets()
        
    def _create_widgets(self):
        widgets = {}
        content = self.get_content_rect()
        x, y = content.x + 10, content.y + 10
        w, h = content.width - 20, 24
        
        widgets['label_project'] = Label(pygame.Rect(x, y, w, h), f"Project: {os.path.basename(self.state.current_project_path)}", alignment="left")
        y += h + 5
        
        widgets['label_target'] = Label(pygame.Rect(x, y, 100, h), "Target Platform:", alignment="left")
        
        # Dropdown for export types (from ExportManager)
        from engine.core.export_manager import ExportManager
        widgets['export_type'] = Dropdown(pygame.Rect(x + 120, y, 200, h), list(ExportManager.EXPORT_TYPES.keys()))
        y += h + 5
        
        widgets['label_path'] = Label(pygame.Rect(x, y, 100, h), "Export Path:", alignment="left")
        # Mock Path Input
        widgets['export_path'] = TextInput(pygame.Rect(x + 120, y, w - 180, h), self.state.export_manager.default_export_path)
        y += h + 20
        
        widgets['export_btn'] = Button(pygame.Rect(x, y, w, 30), "🚀 Start Export", action=self._start_export)
        
        return widgets

    def _start_export(self):
        """Action: Calls the ExportManager to build the game."""
        export_type = self.widgets['export_type'].get_value()
        export_path = self.widgets['export_path'].get_text()
        
        if self.state.export_manager:
            self.state.export_manager.export_project(export_type, export_path)
            
    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.state.ui_state.get('export_window', False): return False
        
        consumed = super().handle_event(event)
        self._update_widgets_rects()
        
        for widget in self.widgets.values():
            if hasattr(widget, 'handle_event') and widget.handle_event(event):
                consumed = True
        return consumed

    def _update_widgets_rects(self):
        self.widgets = self._create_widgets()

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.state.ui_state.get('export_window', False): return
        super().draw(surface, theme)
        for widget in self.widgets.values():
            if hasattr(widget, 'draw'): widget.draw(surface, theme)


class EditorNetworkTester(Window):
    """Floating window for hosting, joining, and testing multiplayer."""
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.widgets = self._create_widgets()
        
    def _create_widgets(self):
        widgets = {}
        content = self.get_content_rect()
        x, y = content.x + 10, content.y + 10
        w, h = content.width - 20, 24
        
        # Mode Selection
        widgets['header_mode'] = Label(pygame.Rect(x, y, w, h), "Multiplayer Mode", text_color=self.state.get_theme_color('accent'))
        y += h + 5
        
        # Host/Server Controls
        widgets['label_host'] = Label(pygame.Rect(x, y, 100, h), "Host IP:", alignment="left")
        widgets['host_ip'] = TextInput(pygame.Rect(x + 100, y, 150, h), self.state.config.network_settings.get("default_host", "127.0.0.1"))
        widgets['label_port'] = Label(pygame.Rect(x + 260, y, 60, h), "Port:", alignment="left")
        widgets['host_port'] = TextInput(pygame.Rect(x + 320, y, 80, h), str(self.state.config.network_settings.get("default_port", 5555)), is_numeric=True)
        y += h + 5
        
        widgets['btn_start_server'] = Button(pygame.Rect(x, y, 200, 30), "🌐 Start Host (Server)", action=lambda: self._toggle_host(True))
        widgets['btn_stop_server'] = Button(pygame.Rect(x + 210, y, 150, 30), "⏹️ Stop Server", action=lambda: self._toggle_host(False))
        y += 40
        
        # Client Controls
        widgets['btn_start_client'] = Button(pygame.Rect(x, y, 200, 30), "🔌 Join Client", action=lambda: self._toggle_client(True))
        widgets['btn_stop_client'] = Button(pygame.Rect(x + 210, y, 150, 30), "❌ Disconnect", action=lambda: self._toggle_client(False))
        y += 40
        
        # Status/Chat (Mock Console for Network Messages)
        widgets['header_status'] = Label(pygame.Rect(x, y, w, h), "Network Status/Chat", text_color=self.state.get_theme_color('accent'))
        y += h + 5
        widgets['chat_input'] = TextInput(pygame.Rect(x, content.bottom - 30, w - 80, 24), "", placeholder="Send Chat Message...")
        widgets['chat_send_btn'] = Button(pygame.Rect(content.right - 85, content.bottom - 30, 75, 24), "Send", action=self._send_chat)
        
        # Status Label
        widgets['status_label'] = Label(pygame.Rect(x, y, w, content.height - y - 35), "Status: Idle", alignment="left")
        
        return widgets

    def _toggle_host(self, start: bool):
        """Action: Starts or stops the network host (server)."""
        nm = self.state.network_manager
        if start:
            host = self.widgets['host_ip'].get_text()
            port = int(self.widgets['host_port'].get_text())
            if nm.start_host(host, port):
                self.widgets['status_label'].text = f"Status: Host Running on {host}:{port}"
        else:
            nm.stop()
            self.widgets['status_label'].text = "Status: Server Stopped"

    def _toggle_client(self, join: bool):
        """Action: Joins or disconnects the client."""
        nm = self.state.network_manager
        if join:
            host = self.widgets['host_ip'].get_text()
            port = int(self.widgets['host_port'].get_text())
            if nm.start_client(host, port):
                self.widgets['status_label'].text = f"Status: Client Connecting to {host}:{port}"
        else:
            nm.stop()
            self.widgets['status_label'].text = "Status: Client Disconnected"

    def _send_chat(self):
        """Action: Sends a chat message via NetworkManager."""
        message = self.widgets['chat_input'].get_text()
        if message:
            self.state.network_manager.send_chat_message(message)
            self.widgets['chat_input'].set_text("")
            
    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.state.ui_state.get('network_tester_window', False): return False
        consumed = super().handle_event(event)
        self._update_widgets_rects()
        for widget in self.widgets.values():
            if hasattr(widget, 'handle_event') and widget.handle_event(event): consumed = True
        return consumed

    def _update_widgets_rects(self): self.widgets = self._create_widgets()
    def draw(self, surface: pygame.Surface, theme: str):
        if not self.state.ui_state.get('network_tester_window', False): return
        super().draw(surface, theme)
        # Update dynamic status label text
        nm = self.state.network_manager
        if nm.is_hosting():
             self.widgets['status_label'].text = f"Status: HOST @ {nm.host}:{nm.port} | Clients: {len(nm.clients)}"
        elif nm.is_client():
             self.widgets['status_label'].text = f"Status: CLIENT @ {nm.host}:{nm.port} | ID: {nm.client_id if nm.client_id else 'WAITING'}"
        
        for widget in self.widgets.values():
            if hasattr(widget, 'draw'): widget.draw(surface, theme)


class EditorWorkshopBrowser(Window):
    """Floating window for browsing, uploading, and downloading Workshop items."""
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.widgets = self._create_widgets()
        
    def _create_widgets(self):
        widgets = {}
        content = self.get_content_rect()
        x, y = content.x + 10, content.y + 10
        w, h = content.width - 20, 24
        
        # Tabs for Browse / Upload
        widgets['btn_browse'] = Button(pygame.Rect(x, y, 100, 30), "Browse", action=lambda: self._set_tab('browse'))
        widgets['btn_upload'] = Button(pygame.Rect(x + 110, y, 100, 30), "Upload Project", action=lambda: self._set_tab('upload'))
        y += 40
        
        # Mocked content area for the active tab (using a Label for simplicity)
        widgets['content_area'] = Label(pygame.Rect(x, y, w, content.height - y - 10), "Select a tab to view content.", alignment="left")
        
        return widgets

    def _set_tab(self, tab: str):
        """Action: Switches the active tab in the workshop window."""
        FileUtils.log_message(f"Workshop tab switched to: {tab}")
        # In a real UI, this would render different views. We mock the content with a Label.
        if tab == 'browse':
            self.state.workshop_manager.scan_workshop()
            item_count = len(self.state.workshop_manager.available_items)
            self.widgets['content_area'].text = f"Browsing Workshop: Found {item_count} items. (Use EditorWorkshop.py to view details)"
        elif tab == 'upload':
            self.widgets['content_area'].text = f"Upload tab: Ready to upload {os.path.basename(self.state.current_project_path)}"
            
    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.state.ui_state.get('workshop_browser_window', False): return False
        consumed = super().handle_event(event)
        self._update_widgets_rects()
        for widget in self.widgets.values():
            if hasattr(widget, 'handle_event') and widget.handle_event(event): consumed = True
        return consumed

    def _update_widgets_rects(self): self.widgets = self._create_widgets()
    def draw(self, surface: pygame.Surface, theme: str):
        if not self.state.ui_state.get('workshop_browser_window', False): return
        super().draw(surface, theme)
        for widget in self.widgets.values():
            if hasattr(widget, 'draw'): widget.draw(surface, theme)


class EditorPluginBrowser(Window):
    """Floating window for viewing, loading, and unloading plugins."""
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.widgets = self._create_widgets()
        
    def _create_widgets(self):
        widgets = {}
        content = self.get_content_rect()
        x, y = content.x + 10, content.y + 10
        w, h = content.width - 20, 24
        
        widgets['header_plugins'] = Label(pygame.Rect(x, y, w, h), "Available Plugins (Click to Toggle Load)", text_color=self.state.get_theme_color('accent'))
        y += h + 5
        
        # Dynamic button list for plugins
        plugins = self.state.plugin_manager.get_plugin_list() if self.state.plugin_manager else {}
        for i, (p_id, data) in enumerate(plugins.items()):
            is_loaded = data.get('is_loaded', False)
            btn_text = f"{p_id} ({data.get('version', 'N/A')})"
            
            # Create a button for each plugin
            btn = Button(pygame.Rect(x, y + i * (h + 5), w, h), btn_text, action=lambda p=p_id, l=is_loaded: self._toggle_plugin(p, l))
            btn.is_toggled = is_loaded
            widgets[f'plugin_btn_{p_id}'] = btn
        
        return widgets

    def _toggle_plugin(self, plugin_id: str, is_loaded: bool):
        """Action: Loads or unloads a plugin."""
        pm = self.state.plugin_manager
        if is_loaded:
            pm.unload_plugin(plugin_id)
        else:
            pm.load_plugin(plugin_id)
            
        # Re-create widgets to update toggled state
        self.widgets = self._create_widgets()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.state.ui_state.get('plugin_browser_window', False): return False
        consumed = super().handle_event(event)
        self._update_widgets_rects()
        for widget in self.widgets.values():
            if hasattr(widget, 'handle_event') and widget.handle_event(event): consumed = True
        return consumed

    def _update_widgets_rects(self): self.widgets = self._create_widgets()
    def draw(self, surface: pygame.Surface, theme: str):
        if not self.state.ui_state.get('plugin_browser_window', False): return
        super().draw(surface, theme)
        for widget in self.widgets.values():
            if hasattr(widget, 'draw'): widget.draw(surface, theme)


# --- Main Editor UI Orchestrator ---

class EditorUI:
    """
    The central handler for all Editor UI components (TopBar, Docking, Floating Windows).
    """
    
    def __init__(self, state: EngineState, topbar: TopBar, dock_manager: DockPanelManager):
        self.state = state
        self.topbar = topbar
        self.dock_manager = dock_manager
        self.menu_commands: Dict[str, Callable] = {} # For TopBar dynamic menu commands (File/Save As...)

    def register_plugin_menu_command(self, menu_path: str, command_func: Callable):
        """Called by PluginManager/PluginAPI to register new commands."""
        self.menu_commands[menu_path] = command_func
        FileUtils.log_message(f"Registered menu command: {menu_path}")
        # NOTE: A real system would update the TopBar's dropdown menu structure here.

    def handle_events(self, events: list[pygame.event.Event]) -> bool:
        """Passes events to UI components in priority order."""
        consumed = False
        
        for event in events:
            # 1. TopBar (Highest Priority)
            if self.topbar.handle_event(event):
                consumed = True
            
            # 2. Dock Panels & Floating Windows
            if self.dock_manager.handle_event(event):
                consumed = True
                
        # If UI has consumed the mouse/keyboard, ensure InputManager knows.
        if consumed:
             self.state.input_manager.consume_input()
        
        return consumed

    def draw(self, surface: pygame.Surface):
        """Draws all UI elements."""
        
        # 1. Docked Panels and Viewport Placeholder (handled by DockPanelManager)
        self.dock_manager.draw(surface)
        
        # 2. TopBar (Drawn last to ensure it's on top)
        self.topbar.draw(surface)
        
        # NOTE: EditorTutorial draw is called implicitly within EditorHelpTutorialWindow.draw