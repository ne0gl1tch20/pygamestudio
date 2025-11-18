# editor/editor_tutorial.py
import pygame
import sys
import os
import json
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Button, Label
    from engine.utils.color import Color
    from engine.utils.math_utils import MathUtils
except ImportError as e:
    print(f"[EditorTutorial Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        ui_state = {"show_tutorial": False}
        screen_rect = pygame.Rect(0, 0, 1280, 720)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[ETUT-INFO] {msg}")
        @staticmethod
        def read_json(path): return {"steps": [{"id": "S1", "text": "Welcome!", "target_rect": [10, 10, 100, 30]}]}
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect; self.text = text
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
    class Color:
        @staticmethod
        def yellow(): return (255, 255, 0)
    class MathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))

TUTORIAL_FILE = os.path.join(FileUtils.get_engine_root_path(), 'docs', 'tutorial_steps.json')
PROGRESS_FILE = os.path.join(FileUtils.get_engine_root_path(), 'config', 'tutorial_progress.json')


class EditorTutorial:
    """
    Implements the step-by-step, interactive onboarding tutorial system.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.tutorial_steps: List[Dict] = self._load_tutorial_steps()
        self.current_step_index = 0
        self.progress: Dict[str, Any] = self._load_progress()
        
        self.is_active_flag = self.progress.get('completed', False) == False and not self.progress.get('skipped', False) # Start automatically if new user

        # UI Elements
        self.btn_next = Button(pygame.Rect(0, 0, 80, 30), "Next ▶️", action=self._next_step)
        self.btn_back = Button(pygame.Rect(0, 0, 80, 30), "◀️ Back", action=self._prev_step)
        self.btn_skip = Button(pygame.Rect(0, 0, 80, 30), "Skip ❌", action=self._skip_tutorial)
        
        self._update_ui_rects()
        
    def _load_tutorial_steps(self) -> List[Dict]:
        """Loads the tutorial flow from the JSON file."""
        try:
            data = FileUtils.read_json(TUTORIAL_FILE)
            return data.get("steps", [])
        except Exception as e:
            FileUtils.log_error(f"Failed to load tutorial steps: {e}")
            return []

    def _load_progress(self) -> Dict[str, Any]:
        """Loads tutorial progress (last step completed) from local file."""
        try:
            return FileUtils.read_json(PROGRESS_FILE)
        except:
            return {"last_step_id": None, "completed": False, "skipped": False}
            
    def _save_progress(self):
        """Saves current progress state."""
        self.progress['last_step_id'] = self.tutorial_steps[self.current_step_index]['id'] if self.tutorial_steps and 0 <= self.current_step_index < len(self.tutorial_steps) else None
        FileUtils.write_json(PROGRESS_FILE, self.progress)

    # --- Control Actions ---

    def start_tutorial(self):
        """Resets and starts the tutorial from the beginning."""
        self.current_step_index = 0
        self.is_active_flag = True
        self.progress['completed'] = False
        self.progress['skipped'] = False
        FileUtils.log_message("Tutorial started.")
        
    def _next_step(self):
        """Moves to the next tutorial step."""
        if self.current_step_index < len(self.tutorial_steps) - 1:
            self.current_step_index += 1
            self._save_progress()
            FileUtils.log_message(f"Tutorial Step {self.current_step_index + 1}")
        else:
            self.progress['completed'] = True
            self.is_active_flag = False
            self._save_progress()
            FileUtils.log_message("Tutorial completed.")

    def _prev_step(self):
        """Moves to the previous tutorial step."""
        self.current_step_index = MathUtils.clamp(self.current_step_index - 1, 0, len(self.tutorial_steps) - 1)
        self._save_progress()
        
    def _skip_tutorial(self):
        """Skips and permanently dismisses the tutorial for this user."""
        self.is_active_flag = False
        self.progress['skipped'] = True
        self.progress['completed'] = True
        self._save_progress()
        FileUtils.log_message("Tutorial skipped.")

    def is_active(self):
        return self.is_active_flag
        
    def get_current_step(self) -> Dict | None:
        """Returns the data for the current step."""
        if 0 <= self.current_step_index < len(self.tutorial_steps):
            return self.tutorial_steps[self.current_step_index]
        return None

    # --- UI and Drawing ---

    def _update_ui_rects(self):
        """Updates the rects of internal UI buttons based on screen size."""
        screen = self.state.screen_rect
        btn_y = screen.bottom - 40
        
        self.btn_skip.rect.topleft = (screen.right - 90, 10) # Top right
        
        self.btn_next.rect.topright = (screen.right - 10, btn_y)
        self.btn_back.rect.topleft = (screen.right - 180, btn_y)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles events for tutorial controls."""
        if not self.is_active_flag: return False
        
        consumed = False
        
        if self.btn_next.handle_event(event): consumed = True
        if self.btn_back.handle_event(event): consumed = True
        if self.btn_skip.handle_event(event): consumed = True
        
        # NOTE: A real tutorial would also consume input over the highlighted area

        return consumed

    def draw(self, surface: pygame.Surface):
        """Draws the tutorial overlay (dimming background, text box, highlights)."""
        if not self.is_active_flag: return
        
        current_step = self.get_current_step()
        if not current_step: return
        
        theme = self.state.config.editor_settings.get('theme', 'dark')
        colors = _get_theme_colors(theme)
        
        # 1. Draw Dimming Overlay (semi-transparent black)
        dim_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim_surface.fill((0, 0, 0, 180)) # 180 transparency
        surface.blit(dim_surface, (0, 0))
        
        # 2. Draw Highlighted Area (Flashing border mock)
        target_rect_data = current_step.get('target_rect', [10, 10, 100, 30])
        target_rect = pygame.Rect(*target_rect_data)
        
        flash_color = Color.yellow().to_rgb()
        flash_width = 3
        
        # Simple flashing animation (based on time)
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            pygame.draw.rect(surface, flash_color, target_rect.inflate(10, 10), flash_width, 5) # Draw outside the target area
            
        # 3. Draw Text Box (Center/Bottom)
        screen = surface.get_rect()
        text_w = 400
        text_h = 150
        text_box_rect = pygame.Rect(screen.centerx - text_w // 2, screen.bottom - text_h - 50, text_w, text_h)
        
        pygame.draw.rect(surface, colors['primary'], text_box_rect, 0, 10)
        pygame.draw.rect(surface, colors['accent'], text_box_rect, 2, 10)
        
        # Draw step number
        Label(pygame.Rect(text_box_rect.x + 5, text_box_rect.y + 5, text_w, 20), f"Step {self.current_step_index + 1}/{len(self.tutorial_steps)}").draw(surface, theme)

        # Draw main text (multi-line mock)
        main_text_rect = pygame.Rect(text_box_rect.x + 10, text_box_rect.y + 30, text_w - 20, text_h - 60)
        Label(main_text_rect, current_step.get('text', 'No Instructions'), alignment="left").draw(surface, theme)

        # 4. Draw Buttons
        self._update_ui_rects()
        self.btn_next.draw(surface, theme)
        self.btn_skip.draw(surface, theme)
        if self.current_step_index > 0:
            self.btn_back.draw(surface, theme)
