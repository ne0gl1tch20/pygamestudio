# engine/gui/panel_console.py
import pygame
import sys
import copy
import os

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from ..engine.core.engine_state import EngineState
    from ..engine.utils.file_utils import FileUtils
    from ..engine.gui.gui_widgets import Window, Label, Scrollbar, TextInput, Button
    from ..engine.utils.color import Color
except ImportError as e:
    print(f"[PanelConsole Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): self.config = self
        def get_setting(self, *args): return 'dark' # Mock theme
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[PC-INFO] {msg}")
        @staticmethod
        def get_log_file_path(): return os.path.join(os.getcwd(), 'logs', 'engine_log.txt')
        @staticmethod
        def read_last_log_lines(path, n): 
            return [f"[{i:03d} INFO] Mock log line {i}" for i in range(1, n + 1)]
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def get_content_rect(self): return self.rect
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
    class Scrollbar:
        def __init__(self, rect, max_scroll): self.rect = rect; self.max_scroll = max_scroll
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_scroll_offset(self): return 0
        def scroll_to_bottom(self): pass
    class TextInput:
        def __init__(self, rect, initial_text, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_text(self): return "mock_command"
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect; self.text = text
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)
        @staticmethod
        def black(): return (0, 0, 0)
        @staticmethod
        def yellow(): return (255, 255, 0)
        @staticmethod
        def red(): return (255, 0, 0)
        @staticmethod
        def green(): return (0, 255, 0)


class PanelConsole:
    """
    Displays engine and game log messages and provides an input area for console commands.
    """
    
    LINE_HEIGHT = 18
    MAX_LINES = 500 # Max lines to read/display from the log file
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=False, movable=False, resizeable=False)
        self.rect = rect.copy()
        
        self.font = pygame.font.Font(None, 16)
        
        # State
        self.log_content = []
        self.last_log_size = 0
        self.scroll_to_bottom_flag = True
        
        # UI Elements
        self.command_input = TextInput(pygame.Rect(0, 0, 100, self.LINE_HEIGHT + 4), "", placeholder="Enter command...")
        self.send_button = Button(pygame.Rect(0, 0, 50, self.LINE_HEIGHT + 4), "Send", action=self._execute_command)
        self.clear_button = Button(pygame.Rect(0, 0, 50, self.LINE_HEIGHT + 4), "Clear", action=self._clear_console)
        self.scrollbar = None
        
        self._update_ui_rects()
        self._load_log_content()

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements based on window size."""
        self.window.rect = self.rect 
        self.content_rect = self.window.get_content_rect()
        
        # Command Input and Send button are at the very bottom
        input_w = self.content_rect.width - 60 - 50 - 10 # Width - Send - Clear - padding
        input_x = self.content_rect.x + 5
        input_y = self.content_rect.bottom - self.LINE_HEIGHT - 6
        
        self.send_button.rect.topright = (self.content_rect.right - 5 - 50 - 5, input_y)
        self.clear_button.rect.topright = (self.content_rect.right - 5, input_y)

        self.command_input.rect.topleft = (input_x, input_y)
        self.command_input.rect.width = input_w
        
        # Adjust content rect for log display area (above the input field)
        self.log_area_rect = self.content_rect.copy()
        self.log_area_rect.height -= (self.LINE_HEIGHT + 10) # Reserve space for input/send


    def _load_log_content(self):
        """Reads the latest lines from the engine log file."""
        log_path = FileUtils.get_log_file_path()
        if os.path.exists(log_path):
            try:
                # Get the current size to check for updates
                current_size = os.path.getsize(log_path)
                
                # Only reload if the file size has changed
                if current_size != self.last_log_size or not self.log_content:
                    # Read the last MAX_LINES from the log file
                    self.log_content = FileUtils.read_last_log_lines(log_path, self.MAX_LINES)
                    self.last_log_size = current_size
                    self.scroll_to_bottom_flag = True # Scroll when new content is loaded
                
            except Exception as e:
                FileUtils.log_error(f"Failed to read engine log file: {e}")
                self.log_content = ["--- FAILED TO READ LOG FILE ---"]
                
        # Update scrollbar max
        self._update_scrollbar_max()


    def _update_scrollbar_max(self):
        """Calculates the max scroll amount based on log content height."""
        content_h = len(self.log_content) * self.LINE_HEIGHT
        max_scroll = max(0, content_h - self.log_area_rect.height)
        
        scroll_rect = pygame.Rect(self.log_area_rect.right - 10, self.log_area_rect.y, 10, self.log_area_rect.height)
        self.scrollbar = Scrollbar(scroll_rect, max_scroll)
        
        if self.scroll_to_bottom_flag:
            self.scrollbar.scroll_to_bottom()
            self.scroll_to_bottom_flag = False


    def _get_log_color(self, line: str):
        """Determines the color of a log line based on its level."""
        if "ERROR" in line:
            return Color.red().to_rgb()
        elif "WARNING" in line:
            return Color.yellow().to_rgb()
        elif "CRITICAL" in line:
            return (255, 165, 0) # Orange
        elif "SUCCESS" in line or "LOADED" in line:
            return Color.green().to_rgb()
        else: # INFO or MESSAGE
            return self.state.get_theme_color('text')

    def _execute_command(self):
        """Action: Executes the command entered in the input field."""
        command_text = self.command_input.get_text().strip()
        if not command_text: return
        
        FileUtils.log_message(f"[COMMAND] > {command_text}")
        self.command_input.set_text("") # Clear input after sending
        
        self.scroll_to_bottom_flag = True # Force scroll down after command
        
        # --- Simple Command Processor Mock ---
        parts = command_text.lower().split()
        if not parts: return
        
        cmd = parts[0]
        
        if cmd == "help":
            FileUtils.log_message("Available Commands: help, debug_state, set_fps [N], spawn [name], net_chat [msg]")
        elif cmd == "debug_state":
            FileUtils.log_message(f"Current Scene: {self.state.current_scene.name if self.state.current_scene else 'None'}")
            FileUtils.log_message(f"Selected Object: {self.state.selected_object_uid}")
        elif cmd == "set_fps" and len(parts) > 1:
            try:
                new_fps = int(parts[1])
                self.state.config.set_setting('project_settings', 'target_fps', new_fps)
                self.state.config.save_config()
                FileUtils.log_message(f"Target FPS set to {new_fps}")
            except:
                FileUtils.log_error("Invalid FPS value.")
        elif cmd == "spawn" and len(parts) > 1:
            # Mock spawn an object
            self.state.scene_manager._add_object()
            FileUtils.log_message(f"Mock object spawned.")
        elif cmd == "net_chat" and len(parts) > 1:
            msg = " ".join(parts[1:])
            if self.state.network_manager:
                self.state.network_manager.send_chat_message(msg)
            else:
                FileUtils.log_message("Network manager not active for chat.")
        else:
            FileUtils.log_error(f"Unknown command: {cmd}")
            
    def _clear_console(self):
        """Action: Clears the displayed log lines."""
        self.log_content = ["--- Console Cleared ---"]
        self.last_log_size = 0
        self.scroll_to_bottom_flag = True
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles user input, primarily for the command input field."""
        consumed = self.window.handle_event(event)
        
        if not self.window.rect.collidepoint(pygame.mouse.get_pos()):
            return consumed # Ignore input outside panel

        # Pass event to top controls
        if self.send_button.handle_event(event) or self.clear_button.handle_event(event):
            return True
            
        # Pass event to command input
        if self.command_input.handle_event(event):
            # Check for ENTER key to execute command
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self._execute_command()
                return True
            return True # Input field consumed event
            
        # Pass event to scrollbar
        if self.scrollbar and self.scrollbar.handle_event(event):
            self.scroll_to_bottom_flag = False # Disable auto-scroll on manual scroll
            return True
                
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        """Draws the console panel, log lines, and command input."""
        
        # 1. Update Layout and load new log data
        self.rect = self.window.rect 
        self._update_ui_rects()
        self._load_log_content() # Check for new log lines

        # 2. Draw Window Frame
        self.window.draw(surface, theme)
        
        # 3. Draw Command Input and Buttons
        self.command_input.draw(surface, theme)
        self.send_button.draw(surface, theme)
        self.clear_button.draw(surface, theme)
        
        # 4. Draw Scrollbar
        self.scrollbar.draw(surface, theme)
        scroll_offset = self.scrollbar.get_scroll_offset()
        
        # 5. Draw Log Content
        
        # Setup clipping for the scrollable log area
        surface.set_clip(self.log_area_rect)
        
        start_x = self.log_area_rect.x + 5
        start_y = self.log_area_rect.y + 5 - scroll_offset
        
        # Determine visible range of lines
        visible_lines = int(self.log_area_rect.height / self.LINE_HEIGHT)
        
        # Draw lines in reverse order (bottom-up for natural console feel, but easier top-down here)
        for i, line in enumerate(self.log_content):
            
            line_y = start_y + i * self.LINE_HEIGHT
            
            # Skip if above or below visible area
            if line_y < self.log_area_rect.y or line_y > self.log_area_rect.bottom:
                continue
                
            text_color = self._get_log_color(line)
            text_surface = self.font.render(line, True, text_color)
            
            # Simple ellipsis for long lines
            if text_surface.get_width() > self.log_area_rect.width - 15:
                # Mock shortening the line
                line = line[:int(self.log_area_rect.width / 10)] + "..."
                text_surface = self.font.render(line, True, text_color)
                
            surface.blit(text_surface, (start_x, line_y))
            
        # Clear clipping
        surface.set_clip(None)