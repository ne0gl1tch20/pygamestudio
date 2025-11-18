# engine/managers/cutscene_manager.py
import pygame
import sys
import copy
import json
import math
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.utils.vector3 import Vector3
    from engine.utils.math_utils import MathUtils
except ImportError as e:
    print(f"[CutsceneManager Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def __init__(self): self.audio_manager = self
        def get_object_by_uid(self, uid): return None
        def get_theme_color(self, k): return (40, 40, 40)
        selected_object_uid = None
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[CSM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[CSM-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def write_json(path, data): pass
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = float(x), float(y)
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = float(x), float(y), float(z)
    class MathUtils:
        @staticmethod
        def lerp(a, b, t): return a + (b - a) * t
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))
    class MockAudioManager:
        def play_sound(self, asset): FileUtils.log_message(f"Mock Audio: Play {asset}")
    EngineState.audio_manager = MockAudioManager()

# --- Data Structures ---

class CutsceneTrack:
    """Represents a sequence of keyframes for a single target property."""
    def __init__(self, name: str, target_uid: str):
        self.name = name                 # e.g., "Player Position Track"
        self.target_uid = target_uid     # UID of the SceneObject/Camera being animated
        self.keyframes: Dict[float, Dict[str, Any]] = {} # {time_seconds: {property_name: value}}
        
    def to_dict(self):
        return {"name": self.name, "target_uid": self.target_uid, "keyframes": self.keyframes}

class Cutscene:
    """Represents a full cinematic timeline."""
    def __init__(self, name: str, length: float):
        self.name = name
        self.length = length             # Total duration in seconds
        self.tracks: Dict[str, CutsceneTrack] = {} # {target_uid: CutsceneTrack}
        
    @classmethod
    def from_dict(cls, data: dict):
        cutscene = cls(data.get("name", "New Cutscene"), data.get("length", 10.0))
        for uid, track_data in data.get("tracks", {}).items():
            track = CutsceneTrack(track_data["name"], track_data["target_uid"])
            track.keyframes = {float(t): d for t, d in track_data["keyframes"].items()} # Ensure time keys are floats
            cutscene.tracks[uid] = track
        return cutscene
        
    def to_dict(self):
        return {
            "name": self.name, 
            "length": self.length, 
            "tracks": {uid: track.to_dict() for uid, track in self.tracks.items()}
        }

# --- Manager Core ---

class CutsceneManager:
    """
    Manages loading, playing, and editing the active cutscene timeline.
    """

    def __init__(self, state: EngineState):
        self.state = state
        self.state.cutscene_manager = self
        
        # State
        self.active_cutscene: Cutscene = self._create_default_cutscene()
        self.playback_time = 0.0
        self.is_playing_flag = False
        self.is_editor_preview = True # True if running in editor, False if in game runtime

        self.cutscene_files = {} # {name: path} - Cache of available cutscene files
        FileUtils.log_message("CutsceneManager initialized.")

    def _create_default_cutscene(self) -> Cutscene:
        """Creates a default, simple cutscene for immediate use/testing."""
        default_cutscene = Cutscene("IntroCutscene", 10.0)
        
        # Mock track for a camera (CAM_001 assumed to exist in scene)
        cam_track = CutsceneTrack("Camera Position", "CAM_001")
        
        # Keyframe 1: Start at (0, 0, -10) at t=0.0
        cam_track.keyframes[0.0] = {"position": [0, 0, -10], "rotation": [0, 0, 0]}
        
        # Keyframe 2: Move to (10, 5, -5) at t=5.0
        cam_track.keyframes[5.0] = {"position": [10, 5, -5], "rotation": [0, 15, 0]}
        
        # Keyframe 3: Return to (0, 0, -10) and trigger an event at t=9.5
        cam_track.keyframes[9.5] = {
            "position": [0, 0, -10], 
            "rotation": [0, 0, 0],
            "event": {"type": "PlaySound", "data": {"asset": "explosion_sound"}}
        }
        
        default_cutscene.tracks["CAM_001"] = cam_track
        return default_cutscene

    # --- Playback Controls ---

    def play(self):
        """Starts cutscene playback from current time."""
        if not self.active_cutscene: return
        self.is_playing_flag = True
        FileUtils.log_message(f"Cutscene '{self.active_cutscene.name}' START.")

    def pause(self):
        """Pauses cutscene playback."""
        self.is_playing_flag = False
        FileUtils.log_message(f"Cutscene '{self.active_cutscene.name}' PAUSED.")

    def stop(self):
        """Stops cutscene playback and resets time to 0.0."""
        self.is_playing_flag = False
        self.playback_time = 0.0
        self.set_playback_time(0.0) # Apply reset immediately
        FileUtils.log_message(f"Cutscene '{self.active_cutscene.name}' STOPPED.")
        
    def is_playing(self):
        return self.is_playing_flag

    def get_playback_time(self):
        return self.playback_time
        
    def set_playback_time(self, time: float):
        """Sets the current playback time, clamping it to the cutscene length."""
        if self.active_cutscene:
            self.playback_time = MathUtils.clamp(time, 0.0, self.active_cutscene.length)
            # Force an immediate update to apply the state at the new time
            self._apply_state_at_time(self.playback_time, is_jump=True)
            
    # --- Main Update Loop ---

    def update(self, dt: float):
        """Advances the timeline and applies state changes if playing."""
        if not self.is_playing_flag or not self.active_cutscene:
            return

        new_time = self.playback_time + dt
        
        # Check for end of cutscene
        if new_time >= self.active_cutscene.length:
            self.playback_time = self.active_cutscene.length
            self._apply_state_at_time(self.playback_time, is_jump=False) # Final update
            self.stop()
            FileUtils.log_message(f"Cutscene '{self.active_cutscene.name}' FINISHED.")
            return

        # Apply state for the time delta
        self._apply_state_at_time(new_time, is_jump=False)
        self.playback_time = new_time

    def _apply_state_at_time(self, current_time: float, is_jump: bool):
        """
        Iterates over all tracks and applies the interpolated or event state 
        at the current time.
        """
        if not self.active_cutscene: return
        
        for uid, track in self.active_cutscene.tracks.items():
            
            # Find the two keyframes that bracket the current time
            times = sorted(track.keyframes.keys())
            
            kf_prev = None
            kf_next = None
            
            for t in times:
                if t <= current_time:
                    kf_prev = t
                elif t > current_time:
                    kf_next = t
                    break
            
            if kf_prev is None and kf_next is None:
                continue # Track has no keyframes
                
            # Find the target object
            target_obj = self.state.get_object_by_uid(track.target_uid)
            if not target_obj: continue

            # --- 1. Apply Interpolated State (if bracketed by two keyframes) ---
            if kf_prev is not None and kf_next is not None:
                t_prev = kf_prev
                t_next = kf_next
                data_prev = track.keyframes[t_prev]
                data_next = track.keyframes[t_next]
                
                # Calculate the interpolation factor (0.0 to 1.0)
                t_factor = (current_time - t_prev) / (t_next - t_prev)
                
                # Interpolate Position
                if "position" in data_prev and "position" in data_next:
                    pos_prev = Vector3(*data_prev["position"]) if target_obj.is_3d else Vector2(*data_prev["position"])
                    pos_next = Vector3(*data_next["position"]) if target_obj.is_3d else Vector2(*data_next["position"])
                    
                    # NOTE: Assuming Vector classes have a static lerp method or property access
                    new_pos = Vector2(MathUtils.lerp(pos_prev.x, pos_next.x, t_factor), MathUtils.lerp(pos_prev.y, pos_next.y, t_factor))
                    if target_obj.is_3d:
                        new_pos = Vector3(new_pos.x, new_pos.y, MathUtils.lerp(pos_prev.z, pos_next.z, t_factor))
                    
                    target_obj.position = new_pos
                    
                # Interpolate Rotation (Simplified Lerp of scalar or Euler components)
                if "rotation" in data_prev and "rotation" in data_next:
                    rot_prev = data_prev["rotation"]
                    rot_next = data_next["rotation"]
                    
                    if target_obj.is_3d:
                        new_rot = [MathUtils.lerp(rot_prev[i], rot_next[i], t_factor) for i in range(3)]
                        target_obj.rotation = Vector3(*new_rot)
                    else:
                        target_obj.rotation = MathUtils.lerp(rot_prev, rot_next, t_factor)

            # --- 2. Apply Static State or Event (if only a previous keyframe exists) ---
            elif kf_prev is not None:
                # If we've passed the last keyframe, hold its state
                data = track.keyframes[kf_prev]
                
                if "position" in data:
                    pos_data = data["position"]
                    if target_obj.is_3d:
                        target_obj.position = Vector3(*pos_data)
                    else:
                        target_obj.position = Vector2(*pos_data[:2])
                
                if "rotation" in data:
                    rot_data = data["rotation"]
                    if target_obj.is_3d:
                        target_obj.rotation = Vector3(*rot_data)
                    else:
                        target_obj.rotation = rot_data
                        
                # --- Event Triggering ---
                if "event" in data and not is_jump: # Only trigger events when advancing time naturally
                    event_time = kf_prev
                    # Check if the event time was crossed this frame (a simple check)
                    # NOTE: This requires storing the *previous* frame's time, 
                    # but for this simple implementation, we assume the keyframe time is the trigger.
                    
                    # We will log the event and call the mock audio manager directly
                    event_type = data["event"]["type"]
                    event_data = data["event"]["data"]
                    
                    if event_type == "PlaySound":
                        self.state.audio_manager.play_sound(event_data["asset"])
                        
                    FileUtils.log_message(f"Cutscene Event Triggered: {event_type} at {event_time:.2f}s")

    # --- Persistence ---
    
    def save_cutscene(self, name: str, file_path: str) -> bool:
        """Saves the active cutscene to a JSON file."""
        if not self.active_cutscene:
            FileUtils.log_warning("No active cutscene to save.")
            return False
            
        data = self.active_cutscene.to_dict()
        try:
            FileUtils.write_json(file_path, data)
            FileUtils.log_message(f"Cutscene '{name}' saved to {file_path}.")
            return True
        except Exception as e:
            FileUtils.log_error(f"Error saving cutscene to {file_path}: {e}")
            return False
            
    def load_cutscene(self, name: str, file_path: str) -> bool:
        """Loads a cutscene from a JSON file and sets it as active."""
        try:
            data = FileUtils.read_json(file_path)
            if data:
                self.active_cutscene = Cutscene.from_dict(data)
                self.playback_time = 0.0
                self.is_playing_flag = False
                FileUtils.log_message(f"Cutscene '{name}' loaded from {file_path}.")
                return True
        except Exception as e:
            FileUtils.log_error(f"Error loading cutscene from {file_path}: {e}")
            return False