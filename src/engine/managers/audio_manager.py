# engine/managers/audio_manager.py
import pygame
import sys
import os
import math
import numpy as np
import wave # Standard library for WAV file manipulation
import io # For in-memory sound generation

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
except ImportError as e:
    print(f"[AudioManager Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def __init__(self): 
            self.config = self
            self.editor_settings = {"audio_volume": 0.5}
            self.asset_loader = self
        def get_setting(self, *args): return 0.5 # Mock volume
        def get_asset(self, type, name): return self._create_mock_sound(name)
        def _create_mock_sound(self, name):
            class MockSound:
                def play(self, loops=0): FileUtils.log_message(f"Mock Sound Played: {name}")
                def set_volume(self, vol): pass
            return MockSound()
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[AM-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[AM-ERROR] {msg}", file=sys.stderr)


class AudioManager:
    """
    Manages all audio playback, volume control, and includes 
    a backend for the procedural audio waveform editor.
    """
    
    SAMPLE_RATE = 44100
    CHANNELS = 1 # Mono for generated sounds
    SAMPLE_WIDTH = 2 # 2 bytes = 16-bit audio
    
    def __init__(self, state: EngineState):
        self.state = state
        self.state.audio_manager = self
        self.master_volume = self.state.config.get_setting('editor_settings', 'audio_volume', 0.5)
        self.sound_cache = {} # Reference to loaded pygame.mixer.Sound objects
        
        self._init_mixer()
        
        FileUtils.log_message(f"AudioManager initialized. Master Volume: {self.master_volume:.2f}")

    def _init_mixer(self):
        """Initializes the Pygame mixer module."""
        if not pygame.mixer.get_init():
            try:
                # Use a specific frequency and size for generated audio compatibility
                pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=self.CHANNELS) 
                pygame.mixer.music.set_volume(self.master_volume)
            except pygame.error as e:
                FileUtils.log_error(f"Pygame Mixer failed to initialize: {e}")
                self.is_ready = False
                return
        self.is_ready = True

    # --- Playback Control ---

    def play_sound(self, asset_name: str, loops: int = 0, volume: float = 1.0):
        """Plays a sound asset by name."""
        if not self.is_ready: return

        sound = self.state.asset_loader.get_asset('sound', asset_name)
        
        if sound and hasattr(sound, 'play'):
            try:
                # Set sound volume (relative to master volume)
                final_volume = self.master_volume * volume
                if hasattr(sound, 'set_volume'):
                    sound.set_volume(final_volume)
                
                sound.play(loops)
                return True
            except Exception as e:
                FileUtils.log_error(f"Error playing sound '{asset_name}': {e}")
                return False
        return False

    def set_master_volume(self, volume: float):
        """Sets the global master volume for sounds and music."""
        self.master_volume = MathUtils.clamp(volume, 0.0, 1.0)
        self.state.config.set_setting('editor_settings', 'audio_volume', self.master_volume)
        pygame.mixer.music.set_volume(self.master_volume)
        # NOTE: Individual Sound objects loaded *before* this change might need 
        # their volume reset for the change to take full effect.

    # --- Waveform Generation Backend ---

    def generate_waveform(self, type: str, duration: float, frequency: float, volume: float, adsr: dict = None) -> np.ndarray:
        """
        Generates a 16-bit mono PCM waveform array based on type and parameters.
        Returns a numpy array.
        """
        num_samples = int(self.SAMPLE_RATE * duration)
        time = np.linspace(0, duration, num_samples, endpoint=False)
        
        # Base Waveform Function
        if type == 'sine':
            waveform = np.sin(2 * np.pi * frequency * time)
        elif type == 'square':
            # Simple square wave approximation
            waveform = np.sign(np.sin(2 * np.pi * frequency * time))
        elif type == 'saw':
            # Sawtooth wave (normalized to -1 to 1)
            waveform = 2 * (time * frequency - np.floor(time * frequency + 0.5))
        elif type == 'triangle':
            # Triangle wave (integral of square wave)
            waveform = 2 * (abs(2 * (time * frequency - np.floor(time * frequency + 0.5))) - 0.5)
        else:
            waveform = np.zeros_like(time)
            
        # Apply Volume
        amplitude = volume
        waveform *= amplitude
        
        # Apply ADSR Envelope (Attack, Decay, Sustain, Release)
        if adsr:
            waveform = self._apply_adsr(waveform, duration, adsr)

        # Convert to 16-bit integer PCM format
        # Max 16-bit value is 32767
        max_int_val = 32767 
        int_waveform = (waveform * max_int_val).astype(np.int16)
        
        return int_waveform

    def _apply_adsr(self, waveform: np.ndarray, duration: float, adsr: dict) -> np.ndarray:
        """Applies the ADSR envelope to the waveform array."""
        
        # Ensure times sum up correctly (A+D+S+R <= duration)
        attack_time = adsr.get('attack', 0.1)
        decay_time = adsr.get('decay', 0.1)
        sustain_level = MathUtils.clamp(adsr.get('sustain_level', 0.5), 0.0, 1.0)
        release_time = adsr.get('release', 0.2)
        
        if attack_time + decay_time + release_time > duration:
            # Simple fix: scale times down if they exceed duration
            scale = duration / (attack_time + decay_time + release_time)
            attack_time *= scale
            decay_time *= scale
            release_time *= scale

        # Calculate time points in samples
        sr = self.SAMPLE_RATE
        attack_sample = int(attack_time * sr)
        decay_sample = int(decay_time * sr)
        release_start_time = duration - release_time
        release_sample_start = int(release_start_time * sr)
        
        envelope = np.ones_like(waveform)
        
        # 1. Attack (0 to 1)
        if attack_sample > 0:
            envelope[:attack_sample] = np.linspace(0.0, 1.0, attack_sample)
            
        # 2. Decay (1 to Sustain Level)
        if decay_sample > 0:
            env_decay = np.linspace(1.0, sustain_level, decay_sample)
            envelope[attack_sample:attack_sample + decay_sample] = env_decay
            
        # 3. Sustain (Sustain Level)
        sustain_end_sample = release_sample_start
        envelope[attack_sample + decay_sample:sustain_end_sample] = sustain_level
        
        # 4. Release (Sustain Level to 0)
        if release_time > 0:
            env_release = np.linspace(sustain_level, 0.0, num_samples - release_sample_start)
            envelope[release_sample_start:] = env_release
            
        return waveform * envelope

    def array_to_pygame_sound(self, array: np.ndarray) -> pygame.mixer.Sound:
        """Converts a numpy array (16-bit PCM) into a Pygame Sound object."""
        if not self.is_ready: return None
        
        try:
            # The numpy array must be a buffer of bytes
            buffer = array.tobytes()
            # Create a Pygame Sound object from the buffer
            sound = pygame.mixer.Sound(buffer)
            return sound
        except Exception as e:
            FileUtils.log_error(f"Failed to convert array to Pygame Sound: {e}")
            return None

    def export_waveform_to_wav(self, array: np.ndarray, file_path: str) -> bool:
        """Exports the numpy array waveform to a standard WAV file."""
        try:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(self.SAMPLE_WIDTH)
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(array.tobytes())
            FileUtils.log_message(f"Waveform successfully exported to: {file_path}")
            return True
        except Exception as e:
            FileUtils.log_error(f"Failed to export WAV file {file_path}: {e}")
            return False