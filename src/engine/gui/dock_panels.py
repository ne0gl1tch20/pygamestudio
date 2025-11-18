# engine/gui/dock_panels.py
import pygame
import sys
from typing import Dict, Any, Callable

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from ..engine.core.engine_state import EngineState
    from ..engine.utils.file_utils import FileUtils
    from ..engine.gui.gui_widgets import Window, Label, Button
    
    # Import all panel classes (which will be defined later)
    # We must mock them if they fail to load to ensure this file is runnable.
    from engine.gui.panel_hierarchy import PanelHierarchy
    from engine.gui.panel_inspector import PanelInspector
    from engine.gui.panel_assets import PanelAssets
    from engine.gui.panel_console import PanelConsole
    from engine.gui.panel_timeline import PanelTimeline
    from engine.gui.panel_properties import PanelProperties
    # Import Editor Windows (which are essentially docked/floating panels)
    from editor.editor_ui import EditorSettingsWindow, EditorHelpTutorialWindow, EditorExportWindow, EditorNetworkTester, EditorWorkshopBrowser, EditorPluginBrowser
    
except ImportError as e:
    print(f"[DockPanels Import Error] {e}. Using Internal Mocks for Panels.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def ui_state(self, k): return False
        def get_asset_loader(self): return self # Mock asset loader
        def get_icon(self, name): 
            s = pygame.Surface((24, 24)); s.fill((255, 255, 255)); return s
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[DP-INFO] {msg}")
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def is_open(self): return True
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect
    
    # Mock Panel Classes
    class MockPanel:
        def __init__(self, rect, state, **kwargs): self.rect = rect; self.state = state; self.is_open_flag = True
        def draw(self, surface, theme): pygame.draw.rect(surface, (100, 50, 50), self.rect, 0); Label(self.rect, self.__class__.__name__).draw(surface, 'dark')
        def handle_event(self, event): return False
        def is_open(self): return self.is_open_flag
        def close(self): self.is_open_flag = False
        def open(self): self.is_open_flag = True
    PanelHierarchy, PanelInspector, PanelAssets, PanelConsole = MockPanel, MockPanel, MockPanel, MockPanel
    PanelTimeline, PanelProperties = MockPanel, MockPanel
    EditorSettingsWindow, EditorHelpTutorialWindow, EditorExportWindow = MockPanel, MockPanel, MockPanel
    EditorNetworkTester, EditorWorkshopBrowser, EditorPluginBrowser = MockPanel, MockPanel, MockPanel


class DockPanelManager:
    """
    Manages the layout, resizing, and visibility of all docked and floating panels 
    in the Editor UI.
    """
    
    # Keys should match the panel's internal state key in EngineState.ui_state
    DOCKABLE_PANEL_CONFIG = {
        'panel_hierarchy': {'class': PanelHierarchy, 'title': "Hierarchy 🌳", 'default_side': 'left', 'size_ratio': 0.2},
        'panel_inspector': {'class': PanelInspector, 'title': "Inspector 🔍", 'default_side': 'right', 'size_ratio': 0.25},
        'panel_assets': {'class': PanelAssets, 'title': "Assets 📁", 'default_side': 'bottom', 'size_ratio': 0.2},
        'panel_console': {'class': PanelConsole, 'title': "Console 💻", 'default_side': 'bottom', 'size_ratio': 0.2},
        'panel_timeline': {'class': PanelTimeline, 'title': "Cutscene Timeline 🎬", 'default_side': 'bottom', 'size_ratio': 0.15},
        'panel_properties': {'class': PanelProperties, 'title': "Project Properties ⚙️", 'default_side': 'left', 'size_ratio': 0.15},
    }
    
    # Floating/Window Panels (Non-dockable, managed by TopBar actions)
    WINDOW_PANEL_CONFIG = {
        'settings_window': {'class': EditorSettingsWindow, 'title': "Editor Settings ⚙️", 'size': (600, 400)},
        'help_tutorial_window': {'class': EditorHelpTutorialWindow, 'title': "Help & Tutorials ❓", 'size': (700, 500)},
        'export_window': {'class': EditorExportWindow, 'title': "Export Build 🚀", 'size': (500, 450)},
        'network_tester_window': {'class': EditorNetworkTester, 'title': "Multiplayer Test 🌐", 'size': (800, 400)},
        'workshop_browser_window': {'class': EditorWorkshopBrowser, 'title': "Workshop Browser 🛠️", 'size': (900, 600)},
        'plugin_browser_window': {'class': EditorPluginBrowser, 'title': "Plugin Manager 🔌", 'size': (700, 450)},
    }
    
    def __init__(self, state: EngineState, topbar_height: int):
        self.state = state
        self.topbar_height = topbar_height
        self.docked_panels: Dict[str, Any] = {}     # Docked panels instances
        self.floating_windows: Dict[str, Window] = {} # Floating window instances
        self.plugin_panels: Dict[str, Callable] = {} # Custom plugin panels to be rendered

        # Layout variables
        self.screen_rect = self.state.screen_rect.copy()
        self.screen_rect.y += self.topbar_height
        self.screen_rect.height -= self.topbar_height
        
        # Resizing/Docking State
        self.is_resizing = False
        self.resize_target: str = None
        self.resize_start_pos: tuple[int, int] = (0, 0)
        
        self._initialize_panels()
        self._calculate_layout()


    def _initialize_panels(self):
        """Instantiates all core dockable panels and floating windows."""
        
        # 1. Docked Panels
        for key, config in self.DOCKABLE_PANEL_CONFIG.items():
            self.docked_panels[key] = config['class'](
                rect=pygame.Rect(0, 0, 100, 100), # Placeholder rects
                state=self.state,
                title=config['title']
            )
            # Ensure the visibility state is reflected in ui_state
            self.state.ui_state[key] = True # Default all core panels visible

        # 2. Floating Windows (Lazy instantiation is safer, but we'll pre-create for simplicity)
        for key, config in self.WINDOW_PANEL_CONFIG.items():
            # Calculate a centered starting position
            w, h = config['size']
            x = (self.state.screen_rect.width - w) // 2
            y = (self.state.screen_rect.height - h) // 2
            
            self.floating_windows[key] = config['class'](
                rect=pygame.Rect(x, y, w, h),
                state=self.state,
                title=config['title']
            )
            # Ensure the visibility state is reflected in ui_state (default hidden)
            self.state.ui_state[key] = False


    def _calculate_layout(self):
        """
        Calculates the Rects for all docked panels and the central viewport.
        Uses a simple fixed-ratio layout system.
        """
        
        self.screen_rect = self.state.screen_rect.copy()
        self.screen_rect.y += self.topbar_height
        self.screen_rect.height -= self.topbar_height
        
        # Initialize bounds for the central viewport
        view_x, view_y = self.screen_rect.topleft
        view_w, view_h = self.screen_rect.size
        
        # --- Left Dock ---
        left_panels = [self.docked_panels[k] for k, c in self.DOCKABLE_PANEL_CONFIG.items() if c['default_side'] == 'left' and self.state.ui_state.get(k, False)]
        if left_panels:
            left_width = int(self.DOCKABLE_PANEL_CONFIG['panel_hierarchy']['size_ratio'] * self.screen_rect.width)
            view_x += left_width
            view_w -= left_width
            
            # Divide left space vertically
            panel_h = view_h / len(left_panels)
            current_y = self.screen_rect.top
            for panel in left_panels:
                panel.rect = pygame.Rect(self.screen_rect.x, current_y, left_width, int(panel_h))
                current_y += panel_h
                
        # --- Right Dock ---
        right_panels = [self.docked_panels[k] for k, c in self.DOCKABLE_PANEL_CONFIG.items() if c['default_side'] == 'right' and self.state.ui_state.get(k, False)]
        if right_panels:
            right_width = int(self.DOCKABLE_PANEL_CONFIG['panel_inspector']['size_ratio'] * self.screen_rect.width)
            view_w -= right_width
            
            # Divide right space vertically
            panel_h = view_h / len(right_panels)
            current_y = self.screen_rect.top
            for panel in right_panels:
                panel.rect = pygame.Rect(view_x + view_w, current_y, right_width, int(panel_h))
                current_y += panel_h

        # --- Bottom Dock ---
        bottom_panels = [self.docked_panels[k] for k, c in self.DOCKABLE_PANEL_CONFIG.items() if c['default_side'] == 'bottom' and self.state.ui_state.get(k, False)]
        if bottom_panels:
            bottom_height = int(self.DOCKABLE_PANEL_CONFIG['panel_console']['size_ratio'] * self.screen_rect.height)
            view_h -= bottom_height
            
            # Divide bottom space horizontally
            panel_w = view_w / len(bottom_panels)
            current_x = view_x
            bottom_y = view_y + view_h
            for panel in bottom_panels:
                panel.rect = pygame.Rect(current_x, bottom_y, int(panel_w), bottom_height)
                current_x += panel_w
                
        # --- Final Viewport Rect ---
        self.viewport_rect = pygame.Rect(view_x, view_y, view_w, view_h)


    # --- Public API for TopBar/Editor Main ---

    def toggle_panel(self, panel_key: str):
        """Toggles the visibility of a docked panel or floating window."""
        
        # Handle Floating Windows
        if panel_key in self.floating_windows:
            window = self.floating_windows[panel_key]
            
            # Toggle visibility flag in EngineState
            current_state = self.state.ui_state.get(panel_key, False)
            self.state.ui_state[panel_key] = not current_state
            
            # Open/close the window instance itself (for internal state)
            if not current_state:
                window.open()
            else:
                window.close()
            FileUtils.log_message(f"Floating Window '{panel_key}' toggled: {self.state.ui_state[panel_key]}")
            return

        # Handle Docked Panels
        if panel_key in self.docked_panels:
            current_state = self.state.ui_state.get(panel_key, False)
            self.state.ui_state[panel_key] = not current_state
            self._calculate_layout()
            FileUtils.log_message(f"Docked Panel '{panel_key}' toggled: {self.state.ui_state[panel_key]}")
            return
            
        FileUtils.log_warning(f"Attempted to toggle unknown panel key: {panel_key}")

    def register_plugin_panel(self, panel_name: str, render_func: Callable, initial_state: dict):
        """Registers a custom UI panel from a plugin."""
        # This function is called by the PluginManager via the PluginAPI
        if panel_name not in self.plugin_panels:
            # We treat plugin panels as floating windows for now
            self.plugin_panels[panel_name] = {
                'render_func': render_func,
                'window': Window(pygame.Rect(50, 50, 300, 300), panel_name, closable=True, movable=True),
                'state': initial_state if initial_state is not None else {}
            }
            self.state.ui_state[f'plugin_{panel_name}'] = False # Hidden by default
            FileUtils.log_message(f"Plugin Panel '{panel_name}' registered.")


    # --- Main Loop Methods ---

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles events for resizing and all contained panels/windows."""
        consumed = False
        
        # 1. Handle Window Resize Event (recalculate layout only on resize event)
        if event.type == pygame.VIDEORESIZE:
            self._calculate_layout()
            
        # 2. Handle Dragging/Resizing (Priority 1)
        if self.is_resizing:
            if event.type == pygame.MOUSEMOTION:
                # Actual resizing logic (skipped for simple fixed-ratio demo)
                pass 
            if event.type == pygame.MOUSEBUTTONUP:
                self.is_resizing = False
                self.resize_target = None
                return True # Consumed mouse up
        
        # 3. Handle Floating Windows (Priority 2: They are on top)
        for key, window in self.floating_windows.items():
            if self.state.ui_state.get(key, False):
                if window.handle_event(event):
                    consumed = True
                    
        # 4. Handle Plugin Windows (Priority 3)
        for name, data in self.plugin_panels.items():
            key = f'plugin_{name}'
            if self.state.ui_state.get(key, False):
                if data['window'].handle_event(event):
                    consumed = True
                    # If window closed via X button, update state
                    if not data['window'].is_open():
                         self.state.ui_state[key] = False

        # 5. Handle Docked Panels (Priority 4)
        for key, panel in self.docked_panels.items():
            if self.state.ui_state.get(key, False):
                if panel.handle_event(event):
                    consumed = True
        
        return consumed


    def draw(self, surface: pygame.Surface):
        """Draws all open docked panels and floating windows."""
        
        theme = self.state.config.editor_settings.get('theme', 'dark')

        # 1. Draw Docked Panels
        for key, panel in self.docked_panels.items():
            if self.state.ui_state.get(key, False):
                panel.draw(surface, theme)
                
        # 2. Draw Floating Windows
        # Draw the last opened/most relevant on top (order doesn't matter for this simple demo)
        for key, window in self.floating_windows.items():
            if self.state.ui_state.get(key, False):
                window.draw(surface, theme)
                
        # 3. Draw Plugin Windows
        for name, data in self.plugin_panels.items():
            key = f'plugin_{name}'
            if self.state.ui_state.get(key, False):
                # Plugin panels render their window frame, then the plugin's function renders content
                data['window'].draw(surface, theme) 
                
                # Render plugin content inside the window content area (mock)
                # The plugin's render_func must be able to draw onto the main surface within the window's rect
                content_rect = data['window'].get_content_rect()
                try:
                    data['render_func'](surface, content_rect, data['state'], self.state)
                except Exception as e:
                    FileUtils.log_error(f"Error drawing plugin panel '{name}': {e}")

        # 4. Draw Viewport Placeholder (optional, usually done by editor_viewport)
        if self.state.is_editor_mode:
            pygame.draw.rect(surface, (10, 10, 10), self.viewport_rect, 0)
            Label(self.viewport_rect, f"Viewport ({self.state.ui_state.get('active_viewport', '2D')})").draw(surface, theme)