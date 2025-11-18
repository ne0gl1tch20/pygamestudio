# engine/gui/panel_timeline.py
import pygame
import sys
import copy
import math

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.managers.cutscene_manager import CutsceneManager, Cutscene, CutsceneTrack
    from engine.utils.file_utils import FileUtils
    from engine.gui.gui_widgets import Window, Label, Scrollbar, Button, Dropdown
    from engine.utils.color import Color
    from engine.utils.math_utils import MathUtils
except ImportError as e:
    print(f"[PanelTimeline Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        def __init__(self): self.cutscene_manager = self
        selected_object_uid = "MOCK_UID"
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[PTL-INFO] {msg}")
    class Window:
        def __init__(self, rect, title, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
        def handle_event(self, event): return False
        def get_content_rect(self): return self.rect
    class Cutscene:
        def __init__(self): self.tracks = {}; self.length = 10.0
    class CutsceneTrack:
        def __init__(self, name, uid): self.name = name; self.target_uid = uid; self.keyframes = {}
    class CutsceneManager:
        def __init__(self): self.active_cutscene = self.Cutscene()
        def set_playback_time(self, t): pass
        def play(self): FileUtils.log_message("Timeline Play")
        def pause(self): FileUtils.log_message("Timeline Pause")
        def stop(self): FileUtils.log_message("Timeline Stop")
        def get_playback_time(self): return 0.0
        def is_playing(self): return False
    class Label:
        def __init__(self, rect, text, **kwargs): self.rect = rect
        def draw(self, surface, theme): pass
    class Scrollbar:
        def __init__(self, rect, max_scroll): self.rect = rect; self.max_scroll = max_scroll
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_scroll_offset(self): return 0
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect; self.text = text
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Dropdown:
        def __init__(self, rect, options, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
        def get_value(self): return options[0]
    class Color:
        @staticmethod
        def white(): return (255, 255, 255)
        @staticmethod
        def black(): return (0, 0, 0)
        @staticmethod
        def yellow(): return (255, 255, 0)
    class MathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))

class PanelTimeline:
    """
    Editor panel for visualizing and editing cutscenes/animations.
    Displays tracks, keyframes, and provides playback controls.
    """
    
    HEADER_HEIGHT = 20
    TRACK_HEIGHT = 24
    TIMELINE_X_START = 150 # Reserved width for track names
    
    def __init__(self, rect: pygame.Rect, state: EngineState, title: str):
        self.state = state
        self.title = title
        self.window = Window(rect, title, closable=False, movable=False, resizeable=False)
        self.rect = rect.copy()
        
        self.font = pygame.font.Font(None, 16)
        
        # State
        self.pixels_per_second = 50.0 # Zoom level (50 pixels per second)
        self.dragging_playhead = False
        self.dragging_keyframe = None # (track_uid, keyframe_time)
        
        # UI Elements
        self.track_scrollbar = None # Vertical scrollbar for tracks
        self.time_scrollbar = None  # Horizontal scrollbar for time view
        
        # Playback Controls
        self.btn_play = Button(pygame.Rect(0, 0, 30, 24), "▶️", action=self.state.cutscene_manager.play)
        self.btn_pause = Button(pygame.Rect(0, 0, 30, 24), "⏸️", action=self.state.cutscene_manager.pause)
        self.btn_stop = Button(pygame.Rect(0, 0, 30, 24), "⏹️", action=self.state.cutscene_manager.stop)
        self.btn_add_track = Button(pygame.Rect(0, 0, 100, 24), "➕ Add Track", action=self._add_track)
        
        self._update_ui_rects()

    def _update_ui_rects(self):
        """Updates the rects of internal UI elements based on window size."""
        self.window.rect = self.rect 
        content_rect = self.window.get_content_rect()
        
        # 1. Playback Controls (Top-left)
        controls_x = content_rect.x + 5
        controls_y = content_rect.y + 2
        
        self.btn_play.rect.topleft = (controls_x, controls_y)
        self.btn_pause.rect.topleft = (controls_x + 35, controls_y)
        self.btn_stop.rect.topleft = (controls_x + 70, controls_y)
        
        # 2. Add Track Button
        self.btn_add_track.rect.topright = (content_rect.right - 5, controls_y)
        
        # 3. Track Name Area (Left)
        self.track_name_rect = pygame.Rect(content_rect.x, content_rect.y + self.HEADER_HEIGHT + self.TRACK_HEIGHT, 
                                           self.TIMELINE_X_START, content_rect.height - self.HEADER_HEIGHT - self.TRACK_HEIGHT - 10) # Reserve bottom for time scrollbar
        
        # 4. Timeline Area (Right)
        self.timeline_view_rect = pygame.Rect(content_rect.x + self.TIMELINE_X_START, self.track_name_rect.y, 
                                              content_rect.width - self.TIMELINE_X_START - 10, self.track_name_rect.height) # Reserve right for track scrollbar
        
        # 5. Vertical Scrollbar (Tracks)
        num_tracks = len(self.state.cutscene_manager.active_cutscene.tracks) if self.state.cutscene_manager.active_cutscene else 0
        total_track_height = num_tracks * self.TRACK_HEIGHT
        max_track_scroll = max(0, total_track_height - self.timeline_view_rect.height)
        self.track_scrollbar = Scrollbar(pygame.Rect(content_rect.right - 10, self.timeline_view_rect.y, 10, self.timeline_view_rect.height), max_track_scroll)
        
        # 6. Horizontal Scrollbar (Time)
        cutscene_length = self.state.cutscene_manager.active_cutscene.length if self.state.cutscene_manager.active_cutscene else 10.0
        total_time_width = int(cutscene_length * self.pixels_per_second)
        max_time_scroll = max(0, total_time_width - self.timeline_view_rect.width)
        self.time_scrollbar = Scrollbar(pygame.Rect(self.timeline_view_rect.x, content_rect.bottom - 10, self.timeline_view_rect.width, 10), 
                                        max_time_scroll, orientation='horizontal')
        

    def _add_track(self):
        """Action: Adds a new track linked to the currently selected object."""
        if self.state.selected_object_uid and self.state.cutscene_manager.active_cutscene:
            uid = self.state.selected_object_uid
            obj_name = self.state.get_object_by_uid(uid).name if self.state.get_object_by_uid(uid) else "Unknown"
            
            # Create a new track
            new_track = CutsceneTrack(f"Transform - {obj_name}", uid)
            self.state.cutscene_manager.active_cutscene.tracks[uid] = new_track
            
            self._update_ui_rects()
            FileUtils.log_message(f"Added new track for {obj_name} to cutscene.")


    def _add_keyframe_at_time(self, track_uid: str, time_seconds: float):
        """Adds a keyframe at the specified time, capturing the current object state."""
        cutscene = self.state.cutscene_manager.active_cutscene
        if not cutscene or track_uid not in cutscene.tracks:
            return
            
        track = cutscene.tracks[track_uid]
        obj = self.state.get_object_by_uid(track.target_uid)
        
        if obj:
            # Simple state capture: position and rotation
            keyframe_data = {
                "position": list(obj.position) if hasattr(obj.position, 'to_tuple') else obj.position,
                "rotation": list(obj.rotation) if hasattr(obj.rotation, 'to_tuple') else obj.rotation
            }
            # Keyframes are stored as {time_seconds: data}
            track.keyframes[time_seconds] = keyframe_data
            FileUtils.log_message(f"Keyframe added for {track.name} at {time_seconds:.2f}s.")
            
    def _time_to_x(self, time_seconds: float) -> int:
        """Converts time (seconds) to x-pixel position within the timeline view rect."""
        x = time_seconds * self.pixels_per_second
        x -= self.time_scrollbar.get_scroll_offset()
        return int(self.timeline_view_rect.x + x)

    def _x_to_time(self, x_pixel: int) -> float:
        """Converts x-pixel position to time (seconds)."""
        x_relative = x_pixel - self.timeline_view_rect.x
        x_relative += self.time_scrollbar.get_scroll_offset()
        time_seconds = x_relative / self.pixels_per_second
        return MathUtils.clamp(time_seconds, 0.0, self.state.cutscene_manager.active_cutscene.length if self.state.cutscene_manager.active_cutscene else 10.0)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles user input for playback, scroll, and keyframe manipulation."""
        consumed = self.window.handle_event(event)
        
        if not self.window.rect.collidepoint(pygame.mouse.get_pos()):
            return consumed # Ignore clicks outside panel

        # Pass event to controls
        for btn in [self.btn_play, self.btn_pause, self.btn_stop, self.btn_add_track]:
            if btn.handle_event(event): consumed = True
            
        # Pass event to scrollbars
        if self.track_scrollbar.handle_event(event): consumed = True
        if self.time_scrollbar.handle_event(event): consumed = True
        
        # --- Playhead Dragging ---
        mouse_pos = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.timeline_view_rect.collidepoint(mouse_pos):
                
                # Check for playhead click (The red line at the top)
                playhead_x = self._time_to_x(self.state.cutscene_manager.get_playback_time())
                if abs(mouse_pos[0] - playhead_x) < 5 and mouse_pos[1] < self.timeline_view_rect.y + self.HEADER_HEIGHT * 2:
                    self.dragging_playhead = True
                    return True

                # Check for keyframe click (The small diamond/circle on the tracks)
                track_y = self.timeline_view_rect.y + self.HEADER_HEIGHT
                track_scroll_offset = self.track_scrollbar.get_scroll_offset()
                
                for track_uid, track in self.state.cutscene_manager.active_cutscene.tracks.items():
                    current_track_y = track_y + (list(self.state.cutscene_manager.active_cutscene.tracks.keys()).index(track_uid) * self.TRACK_HEIGHT) - track_scroll_offset
                    
                    if current_track_y <= mouse_pos[1] < current_track_y + self.TRACK_HEIGHT:
                        # Check for proximity to a keyframe
                        for time in track.keyframes.keys():
                            kf_x = self._time_to_x(time)
                            if abs(mouse_pos[0] - kf_x) < 5:
                                self.dragging_keyframe = (track_uid, time)
                                return True

                # If not dragging playhead or keyframe, insert a keyframe (Ctrl+Click Mock)
                keys = pygame.key.get_pressed()
                if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
                    time = self._x_to_time(mouse_pos[0])
                    # Determine which track row was clicked
                    relative_y = mouse_pos[1] - self.timeline_view_rect.y - self.HEADER_HEIGHT + track_scroll_offset
                    track_index = int(relative_y / self.TRACK_HEIGHT)
                    
                    track_keys = list(self.state.cutscene_manager.active_cutscene.tracks.keys())
                    if 0 <= track_index < len(track_keys):
                        self._add_keyframe_at_time(track_keys[track_index], time)
                        return True
                        
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_playhead:
                new_time = self._x_to_time(mouse_pos[0])
                self.state.cutscene_manager.set_playback_time(new_time)
                return True
            elif self.dragging_keyframe:
                track_uid, old_time = self.dragging_keyframe
                new_time = self._x_to_time(mouse_pos[0])
                
                track = self.state.cutscene_manager.active_cutscene.tracks[track_uid]
                
                # Move keyframe data to the new time slot
                if old_time in track.keyframes:
                    data = track.keyframes.pop(old_time)
                    track.keyframes[new_time] = data
                    self.dragging_keyframe = (track_uid, new_time)
                    
                    # Update playback time to new keyframe time
                    self.state.cutscene_manager.set_playback_time(new_time) 
                    return True
                    
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_playhead or self.dragging_keyframe:
                self.dragging_playhead = False
                self.dragging_keyframe = None
                return True

        return consumed

    def draw(self, surface: pygame.Surface, theme: str):
        """Draws the timeline panel, tracks, and keyframes."""
        
        # 1. Update Layout
        self.rect = self.window.rect 
        self._update_ui_rects()
        
        # 2. Draw Window Frame
        self.window.draw(surface, theme)
        
        # 3. Draw Controls
        self.btn_play.is_toggled = self.state.cutscene_manager.is_playing()
        self.btn_play.draw(surface, theme)
        self.btn_pause.draw(surface, theme)
        self.btn_stop.draw(surface, theme)
        self.btn_add_track.draw(surface, theme)
        
        # 4. Draw Tracks Area (Names + Scrollbar)
        
        # Track Name Background
        pygame.draw.rect(surface, self.state.get_theme_color('primary'), self.track_name_rect)
        
        # Draw Horizontal Time Header Background
        time_header_rect = pygame.Rect(self.timeline_view_rect.x, self.track_name_rect.y - self.TRACK_HEIGHT, 
                                       self.timeline_view_rect.width, self.TRACK_HEIGHT)
        pygame.draw.rect(surface, self.state.get_theme_color('secondary'), time_header_rect)
        
        # 5. Draw Time Ruler/Grid Lines
        surface.set_clip(self.timeline_view_rect)
        cutscene = self.state.cutscene_manager.active_cutscene
        time_scroll_offset = self.time_scrollbar.get_scroll_offset()
        
        if cutscene:
            
            # Time Marker Lines
            time_start_x = self.timeline_view_rect.x
            time_step = 1.0 # 1 second steps
            x_step = int(time_step * self.pixels_per_second)
            
            # Determine the first visible time marker
            first_visible_time = math.floor(time_scroll_offset / self.pixels_per_second)
            
            # Draw Time Markers (vertical lines in timeline view)
            for t in range(int(first_visible_time), int(cutscene.length) + 1):
                x = self._time_to_x(float(t))
                
                if x < self.timeline_view_rect.x or x > self.timeline_view_rect.right:
                    continue
                
                # Draw the vertical grid line
                line_color = self.state.get_theme_color('primary') if t % 5 != 0 else self.state.get_theme_color('accent')
                pygame.draw.line(surface, line_color, (x, self.timeline_view_rect.y), (x, self.timeline_view_rect.bottom), 1)
                
                # Draw the time label in the header
                text_surface = self.font.render(f"{t}s", True, self.state.get_theme_color('text'))
                surface.blit(text_surface, (x + 3, time_header_rect.y + 3))

        # 6. Draw Tracks and Keyframes
        
        if cutscene:
            track_scroll_offset = self.track_scrollbar.get_scroll_offset()
            track_y = self.timeline_view_rect.y
            
            for i, (uid, track) in enumerate(cutscene.tracks.items()):
                current_track_y = track_y + i * self.TRACK_HEIGHT - track_scroll_offset
                
                # Draw Track Name (Left side)
                track_name_rect = pygame.Rect(self.track_name_rect.x, current_track_y, self.track_name_rect.width, self.TRACK_HEIGHT)
                if self.track_name_rect.colliderect(track_name_rect):
                    pygame.draw.rect(surface, self.state.get_theme_color('secondary'), track_name_rect, 0)
                    text_surface = self.font.render(track.name, True, self.state.get_theme_color('text'))
                    surface.blit(text_surface, (track_name_rect.x + 5, track_name_rect.y + 5))

                # Draw Track Background (Right side)
                track_view_rect = pygame.Rect(self.timeline_view_rect.x, current_track_y, self.timeline_view_rect.width, self.TRACK_HEIGHT)
                if self.timeline_view_rect.colliderect(track_view_rect):
                    pygame.draw.rect(surface, self.state.get_theme_color('secondary'), track_view_rect, 0)
                    
                    # Draw Keyframes
                    for time_seconds in track.keyframes.keys():
                        kf_x = self._time_to_x(time_seconds)
                        kf_y_center = current_track_y + self.TRACK_HEIGHT // 2
                        
                        # Draw keyframe diamond/circle
                        kf_color = Color.yellow().to_rgb()
                        if self.dragging_keyframe and self.dragging_keyframe[0] == uid and self.dragging_keyframe[1] == time_seconds:
                            kf_color = Color.red().to_rgb() # Highlight dragging keyframe
                            
                        pygame.draw.circle(surface, kf_color, (kf_x, kf_y_center), 4)

        surface.set_clip(None)

        # 7. Draw Playhead (Red Line - Not clipped)
        current_time = self.state.cutscene_manager.get_playback_time()
        playhead_x = self._time_to_x(current_time)
        
        # Clamp playhead X to the timeline view borders
        playhead_x = MathUtils.clamp(playhead_x, self.timeline_view_rect.left, self.timeline_view_rect.right)

        pygame.draw.line(surface, Color.red().to_rgb(), (playhead_x, time_header_rect.y), 
                         (playhead_x, self.timeline_view_rect.bottom), 2)
                         
        # 8. Draw Scrollbars
        self.track_scrollbar.draw(surface, theme)
        self.time_scrollbar.draw(surface, theme)