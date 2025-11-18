# editor/editor_audio_waveform.py
import pygame
import sys
import os
import math
import numpy as np
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.managers.audio_manager import AudioManager
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Window, Label, Button, Slider, Dropdown
    from engine.utils.color import Color
except ImportError as e:
    print(f"[EditorAudioWaveform Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): self.audio_manager = self
    class AudioManager:
        def __init__(self, state): pass
        def generate_waveform(self, type, dur, freq, vol, adsr): return np.zeros(100)
        def array_to_pygame_sound(self, arr): 
            class MockSound:
                def play(self): FileUtils.log_message("Mock Play Waveform")
            return MockSound()
        def export_waveform_to_wav(self, arr, path): FileUtils.log_message(f"Mock Export WAV: {path}"); return True
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[EAW-INFO] {msg}")
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
    class Slider:
        def __init__(self, rect, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return kwargs.get('initial_val', 0.5)
    class Dropdown:
        def __init__(self, rect, options, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return options[0]
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)
        @staticmethod
        def red(): return (255, 0, 0)
        @staticmethod
        def yellow(): return (255, 255, 0)


class EditorAudioWaveform:
    """
    Floating window for procedurally generating, visualizing, and editing 
    audio waveforms (simple synth/sound effects).
    """
    
    WAVEFORM_TYPES = ["sine", "square", "saw", "triangle"]
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Audio Waveform Editor 🎵"):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.audio_manager: AudioManager = self.state.audio_manager
        
        # State
        self.widgets: Dict[str, Any] = {}
        self.current_waveform: np.ndarray = np.zeros(44100) # 1 second of silence default
        
        # Parameters (Default values)
        self.params = {
            "type": "sine", "duration": 1.0, "frequency": 440.0, "volume": 0.5, 
            "attack": 0.05, "decay": 0.1, "sustain_level": 0.5, "release": 0.2
        }

        self._update_ui_rects()
        self._build_widgets()
        self._generate_and_cache_sound() # Generate initial sound

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements."""
        self.window.rect = self.rect 

    def _build_widgets(self):
        """Generates all parameter widgets."""
        self.widgets.clear()
        content = self.window.get_content_rect()
        x, y = content.x + 10, content.y + 10
        w, h = content.width - 20, 24
        
        def add_slider(y_start, label_text, key, min_val, max_val, step=0.01):
            """Helper for adding a slider with label."""
            widgets[f"label_{key}"] = Label(pygame.Rect(x, y_start, 100, h), f"{label_text}:", alignment="left")
            widgets[key] = Slider(pygame.Rect(x + 105, y_start, 150, h), min_val=min_val, max_val=max_val, initial_val=self.params[key], step=step)
            widgets[f"val_{key}"] = Label(pygame.Rect(x + 260, y_start, 50, h), f"{self.params[key]:.2f}")
            return y_start + h + 5

        # Waveform Type
        widgets['label_type'] = Label(pygame.Rect(x, y, 100, h), "Wave Type:", alignment="left")
        widgets['type'] = Dropdown(pygame.Rect(x + 105, y, 150, h), self.WAVEFORM_TYPES, initial_selection=self.params['type'])
        y += h + 10
        
        # Core Parameters
        y = add_slider(y, "Frequency (Hz)", "frequency", 50.0, 2000.0, step=1.0)
        y = add_slider(y, "Duration (s)", "duration", 0.1, 5.0, step=0.05)
        y = add_slider(y, "Volume", "volume", 0.0, 1.0)
        y += 10
        
        # ADSR Envelope
        widgets['header_adsr'] = Label(pygame.Rect(x, y, w, h), "ADSR Envelope", text_color=self.state.get_theme_color('accent'))
        y += h + 5
        y = add_slider(y, "Attack (s)", "attack", 0.0, 1.0)
        y = add_slider(y, "Decay (s)", "decay", 0.0, 1.0)
        y = add_slider(y, "Sustain Lvl", "sustain_level", 0.0, 1.0)
        y = add_slider(y, "Release (s)", "release", 0.0, 1.0)
        y += 10
        
        # Control Buttons
        widgets['btn_generate'] = Button(pygame.Rect(x, y, 120, 30), "🎵 Generate", action=self._generate_and_cache_sound)
        widgets['btn_play'] = Button(pygame.Rect(x + 130, y, 80, 30), "▶️ Play", action=self._play_sound)
        widgets['btn_export'] = Button(pygame.Rect(x + 220, y, 100, 30), "⬇️ Export WAV", action=self._export_wav)

    def _get_current_adsr(self):
        """Returns the ADSR parameters as a dictionary."""
        return {
            "attack": self.params['attack'], "decay": self.params['decay'],
            "sustain_level": self.params['sustain_level'], "release": self.params['release']
        }

    def _sync_params_from_widgets(self):
        """Pulls current values from all widgets into the self.params dict."""
        for key in self.params.keys():
            widget = self.widgets.get(key)
            if widget:
                if key == 'type':
                    self.params[key] = widget.get_value()
                else:
                    self.params[key] = float(widget.get_value()) # Sliders/Dropdowns return float/str

    def _generate_and_cache_sound(self):
        """Generates the waveform array and caches the pygame.Sound object."""
        self._sync_params_from_widgets() # Update params first
        
        self.current_waveform = self.audio_manager.generate_waveform(
            type=self.params['type'],
            duration=self.params['duration'],
            frequency=self.params['frequency'],
            volume=self.params['volume'],
            adsr=self._get_current_adsr()
        )
        self._cached_sound = self.audio_manager.array_to_pygame_sound(self.current_waveform)
        FileUtils.log_message(f"Generated {self.params['type']} waveform: {len(self.current_waveform)} samples.")

    def _play_sound(self):
        """Action: Plays the currently cached sound."""
        if self._cached_sound:
            self._cached_sound.play()
        
    def _export_wav(self):
        """Action: Exports the current waveform to a WAV file."""
        if self.current_waveform.size > 0:
            # Mock file path
            path = os.path.join(self.state.current_project_path, 'assets', 'sounds', 'generated_fx.wav')
            self.audio_manager.export_waveform_to_wav(self.current_waveform, path)


    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = super().handle_event(event)
        self._update_ui_rects()
        
        # Handle all widgets
        # Rebuild widgets every frame to sync label values
        self._build_widgets() 
        self._sync_params_from_widgets() # Ensure self.params is up-to-date
        
        for widget in self.widgets.values():
            if hasattr(widget, 'handle_event') and widget.handle_event(event):
                consumed = True
                
        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        super().draw(surface, theme)
        content = self.window.get_content_rect()
        
        # Rebuild widgets
        self._build_widgets() 

        # 1. Draw Widgets (Parameters/Controls)
        for widget in self.widgets.values():
            if hasattr(widget, 'draw'): widget.draw(surface, theme)
            
        # 2. Draw Waveform Visualization (Mock)
        vis_rect = pygame.Rect(content.x + 330, content.y + 10, content.width - 340, content.height - 20)
        pygame.draw.rect(surface, (0, 0, 0), vis_rect, 0) # Black background
        
        if self.current_waveform.size > 0:
            points = []
            for i in range(vis_rect.width):
                # Sample the waveform array at this pixel index
                # Map array index (0 to N) to pixel index (0 to width)
                arr_index = int(i * self.current_waveform.size / vis_rect.width)
                sample = self.current_waveform[arr_index] # Value from -32768 to 32767
                
                # Normalize sample to 0-1 and map to y-coordinate
                norm_sample = sample / 32768.0 # -1.0 to 1.0
                y = int(vis_rect.centery - norm_sample * (vis_rect.height / 2.5)) # 2.5 buffer
                
                points.append((vis_rect.x + i, y))
                
            if len(points) > 1:
                pygame.draw.lines(surface, Color.yellow().to_rgb(), False, points, 1)