# engine/gui/topbar.py
import pygame
import sys

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Button, Window, Label
    from engine.gui.dock_panels import DockPanelManager # Used to open panels
except ImportError as e:
    print(f"[Topbar Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def __init__(self): 
            self.is_editor_mode = True
            self.get_theme_color = lambda k: (40, 40, 40)
            self.ui_state = {"show_settings": False}
            self.config = lambda: self # Mock config
            self.editor_settings = {"screen_width": 1280, "screen_height": 720}
            self.game_manager = self
            self.save_load_manager = self
            self.export_manager = self
            self.network_manager = self
            self.workshop_manager = self
            self.plugin_manager = self
            self.asset_loader = self
        def get_icon(self, name): 
            s = pygame.Surface((24, 24)); s.fill((255, 255, 255)); return s
        def save_project(self): FileUtils.log_message("Mock Save")
        def start_game(self, surface): FileUtils.log_message("Mock Play")
        def stop_game(self): FileUtils.log_message("Mock Stop")
    class FileUtils:
        @staticmethod
        def log_message(msg, level="INFO"): print(f"[{level}] {msg}")
    class Button:
        def __init__(self, rect, text, icon, **kwargs): self.rect = rect; self.text = text; self.icon = icon
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect; self.text = text
        def draw(self, surface, theme): pass
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def is_open(self): return False
    class DockPanelManager:
        def __init__(self, state): pass
        def toggle_panel(self, panel_key): FileUtils.log_message(f"Toggle Panel {panel_key}")


class TopBar:
    """
    The main menu bar at the top of the editor window.
    Contains essential controls and access to manager panels.
    Uses emoji icons as required.
    """
    
    HEIGHT = 36
    BUTTON_WIDTH = 100
    
    def __init__(self, state: EngineState, dock_manager: DockPanelManager):
        self.state = state
        self.dock_manager = dock_manager
        self.rect = pygame.Rect(0, 0, self.state.screen_rect.width, self.HEIGHT)
        self.buttons = []
        self._setup_buttons()
        self.is_game_running = False


    def _setup_buttons(self):
        """Initializes all top-bar buttons with emoji icons."""
        
        x_offset = 5
        
        # --- File/Project Management ---
        # 💾 Save 
        btn_save = Button(pygame.Rect(x_offset, 2, self.BUTTON_WIDTH, self.HEIGHT - 4), 
                          "💾 Save", action=self._action_save)
        self.buttons.append(btn_save)
        x_offset += self.BUTTON_WIDTH

        # 📂 Load 
        btn_load = Button(pygame.Rect(x_offset, 2, self.BUTTON_WIDTH, self.HEIGHT - 4), 
                          "📂 Load", action=self._action_load)
        self.buttons.append(btn_load)
        x_offset += self.BUTTON_WIDTH + 10 # Separator

        # --- Core Engine Controls ---
        
        # ⚙️ Settings
        btn_settings = Button(pygame.Rect(x_offset, 2, self.BUTTON_WIDTH, self.HEIGHT - 4), 
                              "⚙️ Settings", action=self._action_toggle_settings)
        self.buttons.append(btn_settings)
        x_offset += self.BUTTON_WIDTH

        # ❓ Help
        btn_help = Button(pygame.Rect(x_offset, 2, self.BUTTON_WIDTH, self.HEIGHT - 4), 
                          "❓ Help", action=self._action_toggle_help)
        self.buttons.append(btn_help)
        x_offset += self.BUTTON_WIDTH + 10

        # --- Pipeline/Manager Access ---
        
        # 🚀 Export
        btn_export = Button(pygame.Rect(x_offset, 2, self.BUTTON_WIDTH, self.HEIGHT - 4), 
                            "🚀 Export", action=self._action_toggle_export)
        self.buttons.append(btn_export)
        x_offset += self.BUTTON_WIDTH

        # 🌐 Multiplayer
        btn_multiplayer = Button(pygame.Rect(x_offset, 2, self.BUTTON_WIDTH, self.HEIGHT - 4), 
                                 "🌐 Multiplayer", action=self._action_toggle_network)
        self.buttons.append(btn_multiplayer)
        x_offset += self.BUTTON_WIDTH

        # 🛠️ Workshop
        btn_workshop = Button(pygame.Rect(x_offset, 2, self.BUTTON_WIDTH, self.HEIGHT - 4), 
                              "🛠️ Workshop", action=self._action_toggle_workshop)
        self.buttons.append(btn_workshop)
        x_offset += self.BUTTON_WIDTH

        # 🔌 Plugins
        btn_plugins = Button(pygame.Rect(x_offset, 2, self.BUTTON_WIDTH, self.HEIGHT - 4), 
                             "🔌 Plugins", action=self._action_toggle_plugins)
        self.buttons.append(btn_plugins)
        x_offset += self.BUTTON_WIDTH + 20

        # --- Play/Stop Controls (Center/Right-aligned) ---
        
        # Play/Stop are toggle buttons, centered or right aligned. We place them near the center.
        self.play_stop_x = self.state.screen_rect.width // 2
        
        self.btn_play = Button(pygame.Rect(self.play_stop_x - 50, 2, 80, self.HEIGHT - 4), 
                               "▶️ Play", action=self._action_play, 
                                is_toggled=False)
        self.buttons.append(self.btn_play)
        
        # 🎨 Theme (Right-aligned, minimal size)
        self.btn_theme = Button(pygame.Rect(self.state.screen_rect.width - 40, 2, 34, self.HEIGHT - 4), 
                                "🎨", action=self._action_toggle_theme, 
                                show_text=False)
        self.buttons.append(self.btn_theme)

    # --- Button Action Callbacks ---
    
    def _action_save(self):
        FileUtils.log_message("TopBar: Action SAVE (Project)")
        if self.state.save_load_manager:
            self.state.save_load_manager.save_full_project(self.state.current_project_path)
        # Trigger dock_panels.py to open Save/Load panel if necessary

    def _action_load(self):
        FileUtils.log_message("TopBar: Action LOAD (Project)")
        self.dock_manager.toggle_panel('panel_assets') # Open Assets panel for file selection (mock)
        
    def _action_toggle_settings(self):
        FileUtils.log_message("TopBar: Action TOGGLE SETTINGS")
        self.dock_manager.toggle_panel('settings_window')
        
    def _action_toggle_help(self):
        FileUtils.log_message("TopBar: Action TOGGLE HELP/TUTORIAL")
        self.dock_manager.toggle_panel('help_tutorial_window')
        self.state.ui_state['show_tutorial'] = True # Force tutorial on for help trigger

    def _action_toggle_export(self):
        FileUtils.log_message("TopBar: Action TOGGLE EXPORT")
        self.dock_manager.toggle_panel('export_window')
        
    def _action_toggle_network(self):
        FileUtils.log_message("TopBar: Action TOGGLE NETWORK/MULTIPLAYER")
        self.dock_manager.toggle_panel('network_tester_window')

    def _action_toggle_workshop(self):
        FileUtils.log_message("TopBar: Action TOGGLE WORKSHOP")
        self.dock_manager.toggle_panel('workshop_browser_window')

    def _action_toggle_plugins(self):
        FileUtils.log_message("TopBar: Action TOGGLE PLUGINS")
        self.dock_manager.toggle_panel('plugin_browser_window')
        
    def _action_toggle_theme(self):
        FileUtils.log_message("TopBar: Action TOGGLE THEME (Mock)")
        current_theme = self.state.config.editor_settings.get('theme', 'dark')
        new_theme = 'light' if current_theme == 'dark' else 'dark'
        self.state.config.set_setting('editor_settings', 'theme', new_theme)
        self.state.config.save_config()
        FileUtils.log_message(f"Theme switched to: {new_theme}")

    def _action_play(self):
        # Play/Stop button logic
        if self.state.game_manager.is_game_running:
            self.state.game_manager.stop_game()
            self.btn_play.text = "▶️ Play"
            self.btn_play.is_toggled = False
            FileUtils.log_message("TopBar: Action STOP")
        else:
            # Get the surface from the state for the runtime to use
            if self.state.surface:
                self.state.game_manager.start_game(self.state.surface)
                self.btn_play.text = "⏹️ Stop"
                self.btn_play.is_toggled = True
                FileUtils.log_message("TopBar: Action PLAY")
            else:
                FileUtils.log_error("Cannot start game: Main surface not available in state.")


    # --- Main Loop Methods ---
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles Pygame events for the top bar."""
        consumed = False
        
        # Check if game manager has stopped/started game and update button state
        is_running_now = self.state.game_manager.is_game_running
        if is_running_now != self.btn_play.is_toggled:
            self.btn_play.is_toggled = is_running_now
            self.btn_play.text = "⏹️ Stop" if is_running_now else "▶️ Play"

        for btn in self.buttons:
            if btn.handle_event(event):
                consumed = True
                break
        
        return consumed

    def draw(self, surface: pygame.Surface):
        """Draws the top bar background and all buttons."""
        
        # Update rect size in case of window resize
        self.rect.width = surface.get_width()
        
        # Draw background
        bg_color = self.state.get_theme_color('topbar_bg')
        pygame.draw.rect(surface, bg_color, self.rect)
        
        # Redraw buttons in case of resize
        self.btn_play.rect.centerx = self.rect.width // 2
        self.btn_theme.rect.x = self.rect.width - 40
        
        # Draw buttons
        for btn in self.buttons:
            btn.draw(surface, self.state.config.editor_settings.get('theme', 'dark'))

        # Draw Title (Mock)
        title_font = pygame.font.Font(None, 18)
        title_text = title_font.render("Pygame Studio Engine V4 - GODMODE PLUS", True, self.state.get_theme_color('text'))
        surface.blit(title_text, (self.rect.width - title_text.get_width() - 5, self.HEIGHT // 2 + 10))