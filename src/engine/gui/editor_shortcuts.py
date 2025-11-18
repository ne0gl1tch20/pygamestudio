# editor/editor_shortcuts.py
import pygame
import sys
import os
import json
from typing import Dict, Any, List, Callable

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.core.input_manager import InputManager
except ImportError as e:
    print(f"[EditorShortcuts Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[ESC-INFO] {msg}")
    class InputManager:
        def __init__(self, state): pass

# Mock the structure of keyboard_shortcuts.md (or load it if available)
DEFAULT_SHORTCUTS = {
    'Ctrl+S': 'Save Project',
    'Ctrl+Shift+S': 'Save Project As',
    'F5': 'Play Game',
    'Esc': 'Stop Game / Exit Runtime',
    'Ctrl+Z': 'Undo Action (Mock)',
    'Ctrl+Y': 'Redo Action (Mock)',
    'Del': 'Delete Selected Object',
    'W': 'Move Tool',
    'E': 'Rotate Tool',
    'R': 'Scale Tool',
}

class EditorShortcuts:
    """
    Manages and processes global keyboard shortcuts for editor actions.
    This class is not a UI window, but a logic handler called by EditorMain.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.shortcuts: Dict[str, str] = self._load_shortcuts()
        self.input_manager: InputManager = self.state.input_manager
        self.action_map: Dict[str, Callable] = self._create_action_map()
        
        FileUtils.log_message("EditorShortcuts initialized.")

    def _load_shortcuts(self) -> Dict[str, str]:
        """Loads shortcuts from documentation file (Mock or FileUtils)."""
        # In a real system, this would parse docs/keyboard_shortcuts.md
        return DEFAULT_SHORTCUTS

    def _create_action_map(self) -> Dict[str, Callable]:
        """Maps shortcut descriptions to callable engine methods."""
        
        def mock_action(name):
            return lambda: FileUtils.log_message(f"Shortcut Action Executed: {name}")

        return {
            'Save Project': lambda: self.state.save_load_manager.save_full_project(self.state.current_project_path),
            'Save Project As': mock_action('Save Project As'),
            'Play Game': lambda: self.state.game_manager.start_game(self.state.surface) if not self.state.game_manager.is_game_running else self.state.game_manager.stop_game(),
            'Stop Game / Exit Runtime': lambda: self.state.game_manager.stop_game(),
            'Delete Selected Object': lambda: self.state.scene_manager.remove_object(self.state.selected_object_uid) if self.state.selected_object_uid else None,
            'Move Tool': lambda: self._set_tool('move'),
            'Rotate Tool': lambda: self._set_tool('rotate'),
            'Scale Tool': lambda: self._set_tool('scale'),
        }

    def _set_tool(self, tool_name: str):
        """Helper to set the viewport active tool."""
        self.state.ui_state['active_tool'] = tool_name
        
    def check_shortcuts(self):
        """
        Main logic called every frame to check for active shortcuts.
        NOTE: This must be called AFTER input_manager.handle_events.
        """
        if not self.state.is_editor_mode:
            return # Only check editor shortcuts in editor mode

        # Check for key downs this frame
        
        # Helper to check if a specific key combination is pressed down this frame
        def is_combo_pressed(combo_str: str) -> bool:
            parts = combo_str.split('+')
            main_key = parts[-1].strip().lower()
            
            # Check if the main key was pressed down this frame
            if not self.input_manager.get_key_down(main_key):
                return False
                
            # Check modifier keys (Ctrl, Shift, Alt - Mock: only check if key is down)
            if 'ctrl' in [p.lower() for p in parts[:-1]]:
                if not (self.input_manager.get_key('lctrl') or self.input_manager.get_key('rctrl')): return False
            if 'shift' in [p.lower() for p in parts[:-1]]:
                if not (self.input_manager.get_key('lshift') or self.input_manager.get_key('rshift')): return False
            
            return True

        for combo_str, action_name in self.shortcuts.items():
            if is_combo_pressed(combo_str):
                action_func = self.action_map.get(action_name)
                if action_func:
                    action_func()
                    # Consume input if action is successfully mapped and executed
                    self.state.input_manager.consume_input() 
                    return True # Stop checking after the first match is executed

        return False

# Mock _get_theme_colors for standalone testing
def _get_theme_colors(theme: str):
    if theme == 'dark':
        return {
            "primary": (50, 50, 50), "secondary": (70, 70, 70), "hover": (90, 90, 90), 
            "accent": (50, 150, 255), "text": (200, 200, 200), "text_disabled": (120, 120, 120), "border": (35, 35, 35)
        }
    else:
        return {
            "primary": (230, 230, 230), "secondary": (210, 210, 210), "hover": (190, 190, 190), 
            "accent": (0, 100, 200), "text": (50, 50, 50), "text_disabled": (150, 150, 150), "border": (220, 220, 220)
        }