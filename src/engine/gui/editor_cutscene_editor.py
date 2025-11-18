# editor/editor_cutscene_editor.py
import pygame
import sys
import os
import math
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.managers.cutscene_manager import CutsceneManager, Cutscene, CutsceneTrack
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Window, Label, Button, TextInput, Scrollbar
    from engine.utils.color import Color
    from engine.utils.math_utils import MathUtils
except ImportError as e:
    print(f"[EditorCutsceneEditor Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): self.cutscene_manager = self
        selected_object_uid = None
    class Cutscene:
        def __init__(self): self.tracks = {}; self.length = 10.0
    class CutsceneManager:
        def __init__(self): self.active_cutscene = self.Cutscene(); self.playback_time = 0.0
        def play(self): FileUtils.log_message("CS Play")
        def stop(self): self.playback_time = 0.0; FileUtils.log_message("CS Stop")
        def set_playback_time(self, t): self.playback_time = t
        def get_playback_time(self): return self.playback_time
        def is_playing(self): return False
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[ECE-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[ECE-ERROR] {msg}", file=sys.stderr)
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
    class TextInput:
        def __init__(self, rect, text, **kwargs): self.rect = rect; self.text = text
        def get_text(self): return self.text
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Scrollbar:
        def __init__(self, rect, max_scroll): self.rect = rect; self.max_scroll = max_scroll
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_scroll_offset(self): return 0
    class MathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))


class EditorCutsceneEditor:
    """
    Floating window for comprehensive editing of cutscene timelines.
    Displays the timeline, controls, and allows keyframe manipulation.
    (Extends PanelTimeline logic)
    """
    
    ITEM_HEIGHT = 24
    TIMELINE_X_START = 150 # Reserved width for track names
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str = "Cutscene Editor 🎬"):
        super().__init__(rect, title, closable=True, movable=True)
        self.state = state
        self.cutscene_manager: CutsceneManager = self.state.cutscene_manager
        
        # State
        self.pixels_per_second = 50.0 
        self.dragging_playhead = False
        self.dragging_keyframe = None 
        self.track_scroll_offset = 0.0 # Vertical track scroll
        self.time_scroll_offset = 0.0  # Horizontal time scroll
        
        # UI Elements (Re-use/duplicate from PanelTimeline for standalone window)
        self.btn_play = Button(pygame.Rect(0, 0, 30, 24), "▶️", self.state.asset_loader.get_icon('play'), action=self.cutscene_manager.play)
        self.btn_stop = Button(pygame.Rect(0, 0, 30, 24), "⏹️", self.state.asset_loader.get_icon('stop'), action=self.cutscene_manager.stop)
        self.btn_add_keyframe = Button(pygame.Rect(0, 0, 30, 24), "🔑", action=self._add_keyframe_at_playhead)
        
        self.btn_add_track = Button(pygame.Rect(0, 0, 100, 24), "➕ Track", action=self._add_track)
        
        self._update_ui_rects()

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements."""
        self.window.rect = self.rect 
        content = self.window.get_content_rect()
        
        # Playback Controls (Top-left)
        controls_x, controls_y = content.x + 5, content.y + 5
        self.btn_play.rect.topleft = (controls_x, controls_y)
        self.btn_stop.rect.topleft = (controls_x + 35, controls_y)
        self.btn_add_keyframe.rect.topleft = (controls_x + 70, controls_y)
        self.btn_add_track.rect.topright = (content.right - 10, controls_y)
        
        # Timeline Area (Main space below controls)
        self.timeline_area_rect = pygame.Rect(content.x, content.y + self.ITEM_HEIGHT + 10, content.width, content.height - self.ITEM_HEIGHT - 20)
        self.track_name_rect = pygame.Rect(self.timeline_area_rect.x, self.timeline_area_rect.y, self.TIMELINE_X_START, self.timeline_area_rect.height)
        self.timeline_view_rect = pygame.Rect(self.timeline_area_rect.x + self.TIMELINE_X_START, self.timeline_area_rect.y + self.ITEM_HEIGHT, 
                                              self.timeline_area_rect.width - self.TIMELINE_X_START - 10, self.timeline_area_rect.height - self.ITEM_HEIGHT - 10)
        
        # Scrollbars (Vertical and Horizontal are critical here)
        # Vertical Track Scrollbar
        self.track_scrollbar = Scrollbar(pygame.Rect(self.timeline_view_rect.right, self.timeline_view_rect.y, 10, self.timeline_view_rect.height), 0)
        # Horizontal Time Scrollbar
        self.time_scrollbar = Scrollbar(pygame.Rect(self.timeline_view_rect.x, self.timeline_view_rect.bottom, self.timeline_view_rect.width, 10), 0, orientation='horizontal')
        
        # Update scrollbar max values based on data
        self._update_scrollbar_max()
        
    def _update_scrollbar_max(self):
        """Recalculates max scroll for both scrollbars."""
        cutscene = self.cutscene_manager.active_cutscene
        num_tracks = len(cutscene.tracks) if cutscene else 0
        total_track_height = num_tracks * self.ITEM_HEIGHT
        self.track_scrollbar.max_scroll = max(0, total_track_height - self.timeline_view_rect.height)
        
        cutscene_length = cutscene.length if cutscene else 10.0
        total_time_width = int(cutscene_length * self.pixels_per_second)
        self.time_scrollbar.max_scroll = max(0, total_time_width - self.timeline_view_rect.width)


    def _add_track(self):
        """Action: Adds a new track linked to the currently selected object."""
        if self.state.selected_object_uid and self.cutscene_manager.active_cutscene:
            uid = self.state.selected_object_uid
            obj = self.state.get_object_by_uid(uid)
            obj_name = obj.name if obj else "Unknown"
            
            new_track = CutsceneTrack(f"Transform - {obj_name}", uid)
            self.cutscene_manager.active_cutscene.tracks[uid] = new_track
            self._update_scrollbar_max()
            FileUtils.log_message(f"Added new track for {obj_name}.")

    def _add_keyframe_at_playhead(self):
        """Action: Adds a keyframe for the selected track at the current playback time."""
        if self.state.selected_object_uid and self.cutscene_manager.active_cutscene:
            track_uid = self.state.selected_object_uid # Simplified: Selected object is the target of the track
            track = self.cutscene_manager.active_cutscene.tracks.get(track_uid)
            obj = self.state.get_object_by_uid(track_uid)

            if track and obj:
                time = self.cutscene_manager.get_playback_time()
                
                # Capture current object state (Position/Rotation mock)
                keyframe_data = {
                    "position": list(obj.position) if hasattr(obj.position, 'to_tuple') else obj.position,
                    "rotation": list(obj.rotation) if hasattr(obj.rotation, 'to_tuple') else obj.rotation
                }
                track.keyframes[time] = keyframe_data
                FileUtils.log_message(f"Keyframe added for {track.name} at {time:.2f}s.")

    def _time_to_x(self, time_seconds: float) -> int:
        """Converts time (seconds) to x-pixel position within the timeline view rect."""
        x = time_seconds * self.pixels_per_second
        x -= self.time_scroll_offset
        return int(self.timeline_view_rect.x + x)

    def _x_to_time(self, x_pixel: int) -> float:
        """Converts x-pixel position to time (seconds)."""
        x_relative = x_pixel - self.timeline_view_rect.x
        x_relative += self.time_scroll_offset
        time_seconds = x_relative / self.pixels_per_second
        return MathUtils.clamp(time_seconds, 0.0, self.cutscene_manager.active_cutscene.length if self.cutscene_manager.active_cutscene else 10.0)


    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.window.is_open(): return False
        
        consumed = super().handle_event(event)
        self._update_ui_rects()
        
        # Pass to controls
        for btn in [self.btn_play, self.btn_stop, self.btn_add_keyframe, self.btn_add_track]:
            if btn.handle_event(event): consumed = True
            
        # Pass to scrollbars
        if self.track_scrollbar.handle_event(event): 
            self.track_scroll_offset = self.track_scrollbar.get_scroll_offset()
            consumed = True
        if self.time_scrollbar.handle_event(event): 
            self.time_scroll_offset = self.time_scrollbar.get_scroll_offset()
            consumed = True
            
        # Dragging logic (Playhead / Keyframe)
        mouse_pos = pygame.mouse.get_pos()
        if self.timeline_view_rect.collidepoint(mouse_pos):
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check for playhead click
                playhead_x = self._time_to_x(self.cutscene_manager.get_playback_time())
                if abs(mouse_pos[0] - playhead_x) < 5:
                    self.dragging_playhead = True
                    return True

            elif event.type == pygame.MOUSEMOTION:
                if self.dragging_playhead:
                    new_time = self._x_to_time(mouse_pos[0])
                    self.cutscene_manager.set_playback_time(new_time)
                    return True
                    
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.dragging_playhead:
                    self.dragging_playhead = False
                    return True
                
        return consumed


    def draw(self, surface: pygame.Surface, theme: str):
        if not self.window.is_open(): return

        super().draw(surface, theme)
        self._update_ui_rects()
        content = self.window.get_content_rect()
        colors = _get_theme_colors(theme)

        # Draw Controls
        self.btn_play.is_toggled = self.cutscene_manager.is_playing()
        for btn in [self.btn_play, self.btn_stop, self.btn_add_keyframe, self.btn_add_track]:
            btn.draw(surface, theme)
            
        # Track Name Background
        pygame.draw.rect(surface, colors['primary'], self.track_name_rect, 0)
        
        # Time Header Background
        time_header_rect = pygame.Rect(self.timeline_view_rect.x, self.timeline_area_rect.y, self.timeline_view_rect.width, self.ITEM_HEIGHT)
        pygame.draw.rect(surface, colors['secondary'], time_header_rect, 0)

        cutscene = self.cutscene_manager.active_cutscene
        
        # 1. Draw Time Ruler/Grid Lines
        surface.set_clip(self.timeline_view_rect)
        if cutscene:
            
            # Time Markers (vertical lines)
            time_step = 1.0 
            first_visible_time = math.floor(self.time_scroll_offset / self.pixels_per_second)
            
            for t in range(int(first_visible_time), int(cutscene.length) + 1):
                x = self._time_to_x(float(t))
                line_color = colors['primary'] if t % 5 != 0 else colors['accent']
                pygame.draw.line(surface, line_color, (x, self.timeline_view_rect.y), (x, self.timeline_view_rect.bottom), 1)
                
                # Draw time label
                text_surface = self.font.render(f"{t}s", True, colors['text'])
                surface.blit(text_surface, (x + 3, time_header_rect.y + 3))

        # 2. Draw Tracks and Keyframes
        if cutscene:
            track_y = self.timeline_view_rect.y
            
            for i, (uid, track) in enumerate(cutscene.tracks.items()):
                current_track_y = track_y + i * self.ITEM_HEIGHT - self.track_scroll_offset
                
                # Draw Track Name (Left side)
                track_name_rect = pygame.Rect(self.track_name_rect.x, current_track_y, self.track_name_rect.width, self.ITEM_HEIGHT)
                if self.track_name_rect.colliderect(track_name_rect):
                    pygame.draw.rect(surface, colors['secondary'], track_name_rect, 0)
                    Label(track_name_rect, track.name, alignment="left").draw(surface, theme)

                # Draw Track Background (Right side)
                track_view_rect = pygame.Rect(self.timeline_view_rect.x, current_track_y, self.timeline_view_rect.width, self.ITEM_HEIGHT)
                if self.timeline_view_rect.colliderect(track_view_rect):
                    pygame.draw.rect(surface, colors['secondary'], track_view_rect, 0)
                    
                    # Draw Keyframes
                    for time_seconds in track.keyframes.keys():
                        kf_x = self._time_to_x(time_seconds)
                        kf_y_center = current_track_y + self.ITEM_HEIGHT // 2
                        pygame.draw.circle(surface, Color.yellow().to_rgb(), (kf_x, kf_y_center), 4)

        surface.set_clip(None)

        # 3. Draw Playhead (Red Line)
        current_time = self.cutscene_manager.get_playback_time()
        playhead_x = self._time_to_x(current_time)
        
        playhead_x = MathUtils.clamp(playhead_x, self.timeline_view_rect.left, self.timeline_view_rect.right)

        pygame.draw.line(surface, Color.red().to_rgb(), (playhead_x, time_header_rect.y), 
                         (playhead_x, self.timeline_view_rect.bottom), 2)
                         
        # 4. Draw Scrollbars
        self.track_scrollbar.draw(surface, theme)
        self.time_scrollbar.draw(surface, theme)