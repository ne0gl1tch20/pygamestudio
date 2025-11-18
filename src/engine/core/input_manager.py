# engine/core/input_manager.py
import pygame
import sys
import copy

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
except ImportError as e:
    print(f"[InputManager Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[IM-INFO] {msg}")


class InputManager:
    """
    Handles all user input (keyboard, mouse, joystick) and provides 
    stateful query methods (e.g., get_key_down, get_key).
    It manages input consumption for UI vs. Game.
    """

    # Map common strings to Pygame key constants (for easier user/script access)
    KEY_MAP = {
        'a': pygame.K_a, 'b': pygame.K_b, 'c': pygame.K_c, 'd': pygame.K_d, 
        'e': pygame.K_e, 'f': pygame.K_f, 'g': pygame.K_g, 'h': pygame.K_h, 
        'i': pygame.K_i, 'j': pygame.K_j, 'k': pygame.K_k, 'l': pygame.K_l, 
        'm': pygame.K_m, 'n': pygame.K_n, 'o': pygame.K_o, 'p': pygame.K_p, 
        'q': pygame.K_q, 'r': pygame.K_r, 's': pygame.K_s, 't': pygame.K_t, 
        'u': pygame.K_u, 'v': pygame.K_v, 'w': pygame.K_w, 'x': pygame.K_x, 
        'y': pygame.K_y, 'z': pygame.K_z, 'space': pygame.K_SPACE, 
        'return': pygame.K_RETURN, 'escape': pygame.K_ESCAPE, 'lshift': pygame.K_LSHIFT,
        'rshift': pygame.K_RSHIFT, 'lctrl': pygame.K_LCTRL, 'rctrl': pygame.K_RCTRL,
        'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT,
        # F keys for editor shortcuts
        'f1': pygame.K_F1, 'f2': pygame.K_F2, 'f3': pygame.K_F3, 'f4': pygame.K_F4, 
        'f5': pygame.K_F5, 'f6': pygame.K_F6, 'f7': pygame.K_F7, 'f8': pygame.K_F8,
        'delete': pygame.K_DELETE, 'tab': pygame.K_TAB
        # ... add more keys as needed
    }

    def __init__(self, state: EngineState):
        self.state = state
        self.state.input_manager = self # Link back to state
        
        # Keyboard State
        self._key_current = set()  # Keys currently held down (constants)
        self._key_down = set()     # Keys pressed this frame (constants)
        self._key_up = set()       # Keys released this frame (constants)

        # Mouse State
        self.mouse_pos = (0, 0)
        self.mouse_delta = (0, 0)
        self._mouse_current = [False, False, False] # [LMB, MMB, RMB]
        self._mouse_down = [False, False, False]
        self._mouse_up = [False, False, False]
        self.scroll_y = 0

        # Input Consumption (for editor/ui logic)
        self.ui_consumes_input = False # True if UI element has focus/hover (e.g., text box)
        self.game_events = [] # Events that weren't consumed by the UI/Editor

        # Joystick/Gamepad Support (Basic mock/stub)
        self.joysticks = []
        self._init_joysticks()
        
    def _init_joysticks(self):
        """Initializes Pygame joysticks."""
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            self.joysticks.append(joystick)
            FileUtils.log_message(f"Initialized Joystick: {joystick.get_name()}")
            
    def _reset_frame_state(self):
        """Resets the state that only lasts for a single frame (e.g., *_down, *_up)."""
        self._key_down.clear()
        self._key_up.clear()
        self._mouse_down = [False, False, False]
        self._mouse_up = [False, False, False]
        self.scroll_y = 0
        self.mouse_delta = (0, 0)
        self.game_events.clear()
        self.ui_consumes_input = False
        
    def handle_events(self, events: list[pygame.event.Event]) -> bool:
        """
        Processes all Pygame events. 
        Returns False if a QUIT event is found, True otherwise.
        """
        self._reset_frame_state()
        
        quit_flag = False
        last_mouse_pos = self.mouse_pos
        
        for event in events:
            # 1. System Events
            if event.type == pygame.QUIT:
                quit_flag = True
            elif event.type == pygame.VIDEORESIZE:
                self.state.set_viewport_size(event.size[0], event.size[1])
                
            # 2. Mouse Events
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
                self.mouse_delta = (event.pos[0] - last_mouse_pos[0], event.pos[1] - last_mouse_pos[1])
            elif event.type == pygame.MOUSEBUTTONDOWN:
                button = event.button
                if 1 <= button <= 3: # 1:LMB, 2:MMB, 3:RMB
                    idx = button - 1
                    self._mouse_current[idx] = True
                    self._mouse_down[idx] = True
                elif button == 4: # Scroll up
                    self.scroll_y = 1
                elif button == 5: # Scroll down
                    self.scroll_y = -1
            elif event.type == pygame.MOUSEBUTTONUP:
                button = event.button
                if 1 <= button <= 3:
                    idx = button - 1
                    self._mouse_current[idx] = False
                    self._mouse_up[idx] = True
                    
            # 3. Keyboard Events
            elif event.type == pygame.KEYDOWN:
                self._key_current.add(event.key)
                self._key_down.add(event.key)
            elif event.type == pygame.KEYUP:
                if event.key in self._key_current:
                    self._key_current.remove(event.key)
                self._key_up.add(event.key)
                
            # 4. Joystick Events (Basic Stub)
            elif event.type == pygame.JOYAXISMOTION:
                # Handle joystick axis movement
                if not self.ui_consumes_input:
                    self.game_events.append(event)
            elif event.type == pygame.JOYBUTTONDOWN or event.type == pygame.JOYBUTTONUP:
                # Handle joystick button press/release
                if not self.ui_consumes_input:
                    self.game_events.append(event)
            
            # 5. Events not consumed by UI/Editor (always pass to game in runtime)
            if not self.state.is_editor_mode or not self.ui_consumes_input:
                # Note: In Editor mode, the EditorUI handles consumption first.
                # If the UI doesn't consume it, it becomes a 'game' event
                self.game_events.append(event)

        return not quit_flag

    # --- Public Query Methods (for scripts/game objects) ---

    def get_key(self, key_name: str) -> bool:
        """Returns True if the specified key is currently held down."""
        key_constant = self.KEY_MAP.get(key_name.lower())
        if key_constant is None:
            # Check if it's already a constant (e.g., from direct Pygame event key)
            key_constant = key_name if isinstance(key_name, int) else None
            
        return key_constant in self._key_current if key_constant else False

    def get_key_down(self, key_name: str) -> bool:
        """Returns True only on the frame the specified key was pressed."""
        key_constant = self.KEY_MAP.get(key_name.lower())
        key_constant = key_constant if key_constant else key_name if isinstance(key_name, int) else None
        return key_constant in self._key_down if key_constant else False

    def get_key_up(self, key_name: str) -> bool:
        """Returns True only on the frame the specified key was released."""
        key_constant = self.KEY_MAP.get(key_name.lower())
        key_constant = key_constant if key_constant else key_name if isinstance(key_name, int) else None
        return key_constant in self._key_up if key_constant else False

    def get_mouse_pos(self) -> tuple[int, int]:
        """Returns the current mouse X, Y position."""
        return self.mouse_pos

    def get_mouse_delta(self) -> tuple[int, int]:
        """Returns the change in mouse X, Y position this frame."""
        return self.mouse_delta

    def get_mouse_button(self, button: int) -> bool:
        """Returns True if the mouse button (1=LMB, 2=MMB, 3=RMB) is held down."""
        if 1 <= button <= 3:
            return self._mouse_current[button - 1]
        return False

    def get_mouse_button_down(self, button: int) -> bool:
        """Returns True only on the frame the mouse button was pressed."""
        if 1 <= button <= 3:
            return self._mouse_down[button - 1]
        return False

    def get_mouse_button_up(self, button: int) -> bool:
        """Returns True only on the frame the mouse button was released."""
        if 1 <= button <= 3:
            return self._mouse_up[button - 1]
        return False

    def get_scroll_y(self) -> int:
        """Returns the mouse scroll wheel delta (1=up, -1=down, 0=none)."""
        return self.scroll_y
        
    def get_all_game_events(self):
        """Returns a list of all Pygame events passed to the game layer this frame."""
        return self.game_events

    # --- Consumption/UI Management ---
    
    def consume_input(self):
        """
        Signals that a UI element has consumed the input for this frame.
        Prevents game logic (like camera movement or player input) from processing.
        """
        self.ui_consumes_input = True