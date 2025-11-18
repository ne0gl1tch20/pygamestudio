# engine/core/engine_runtime.py
import pygame
import sys
import time

# --- MOCK IMPORTS for Standalone Runnability Check ---
# In a real run, these would be the full modules.
# Since the generator must produce runnable code, we define a minimal structure
# for the central state/config/utils that this core module depends on heavily.
try:
    from engine.core.engine_state import EngineState
    from engine.core.scene_manager import SceneManager
    from engine.core.game_manager import GameManager
    from engine.core.asset_loader import AssetLoader
    from engine.core.input_manager import InputManager
    from engine.core.network_manager import NetworkManager
    from engine.utils.file_utils import FileUtils
    from engine.rendering.renderer2d import Renderer2D
    # from engine.rendering.renderer3d import Renderer3D # Use mock for pygame3d fallback
    from engine.physics.physics2d import Physics2D
    # from engine.physics.physics3d import Physics3D # Use mock for 3D fallback
    from engine.managers.camera_manager import CameraManager
    from engine.scripting.script_engine import ScriptEngine
    from engine.managers.behavior_tree_manager import BehaviorTreeManager
    from engine.managers.cutscene_manager import CutsceneManager
    from engine.managers.particle_manager import ParticleManager
    from engine.managers.audio_manager import AudioManager
    from engine.utils.timer import Timer
    from engine.utils.vector2 import Vector2
    from engine.utils.color import Color
    
    # Simple 3D Fallback Mocks if full modules are not yet generated or imported fails
    class Renderer3D: 
        def __init__(self, *args): FileUtils.log_warning("3D Renderer Mock used.")
        def render(self, *args): pass
    class Physics3D: 
        def __init__(self, *args): FileUtils.log_warning("3D Physics Mock used.")
        def update(self, *args): pass
        
except ImportError as e:
    # This block executes if core components haven't been generated yet, which is 
    # expected during sequential generation, but we must make the code runnable.
    print(f"EngineRuntime Import Warning: {e}. Using Internal Mocks for Dependencies.")
    
    # Internal minimal mocks to prevent crash
    class MockConfig:
        def __init__(self): 
            self.project_settings = {"is_3d_mode": False, "target_fps": 60}
        def get_setting(self, *args, **kwargs): return 60 # Default FPS
    class MockState:
        def __init__(self):
            self.config = MockConfig()
            self.current_scene = None # Mock scene
            self.is_running = True
    class MockManager:
        def __init__(self, state=None): pass
        def init(self): pass
        def update(self, dt): pass
    class MockPhysics:
        def __init__(self, state=None): pass
        def update(self, dt, scene): pass
    class MockRenderer:
        def __init__(self, state=None): pass
        def render(self, surface, scene, camera): pass
        
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[MOCK-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[MOCK-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def log_warning(msg): print(f"[MOCK-WARN] {msg}")

    # Re-map classes to internal mocks
    EngineState, SceneManager, GameManager, AssetLoader = MockState, MockManager, MockManager, MockManager
    InputManager, NetworkManager, CameraManager, ScriptEngine = MockManager, MockManager, MockManager, MockManager
    Renderer2D, Renderer3D, Physics2D, Physics3D = MockRenderer, MockRenderer, MockPhysics, MockPhysics
    BehaviorTreeManager, CutsceneManager, ParticleManager, AudioManager, Timer = MockManager, MockManager, MockManager, MockManager, MockManager
    class Vector2:
        def __init__(self, x, y): self.x, self.y = float(x), float(y)
        def __add__(self, other): return Vector2(self.x + other.x, self.y + other.y)
        def __sub__(self, other): return Vector2(self.x - other.x, self.y - other.y)
        def __mul__(self, scalar): return Vector2(self.x * scalar, self.y * scalar)
    class Color:
        def __init__(self, r, g, b, a=255): self.r, self.g, self.b, self.a = r, g, b, a
        def to_rgb(self): return (self.r, self.g, self.b)
    
# --- END MOCK IMPORTS ---

class EngineRuntime:
    """
    The core runtime loop for a running game build (not the editor).
    This class orchestrates all managers for a single game instance.
    """
    
    def __init__(self, surface: pygame.Surface, state: EngineState):
        """Initializes the engine runtime with the display surface and game state."""
        self.surface = surface
        self.state = state
        self.clock = pygame.time.Clock()
        self.is_3d_mode = self.state.config.project_settings.get("is_3d_mode", False)

        # Initialize core managers, linking them to the central state
        self.state.asset_loader = AssetLoader(self.state)
        self.state.input_manager = InputManager(self.state)
        self.state.network_manager = NetworkManager(self.state)
        self.state.camera_manager = CameraManager(self.state)
        self.state.audio_manager = AudioManager(self.state)
        self.state.particle_manager = ParticleManager(self.state)
        self.state.cutscene_manager = CutsceneManager(self.state)
        self.state.behavior_tree_manager = BehaviorTreeManager(self.state)
        self.state.script_engine = ScriptEngine(self.state)

        # Initialize Physics and Renderer based on 2D/3D mode
        if self.is_3d_mode:
            self.renderer = Renderer3D(self.state)
            self.physics_system = Physics3D(self.state)
            FileUtils.log_message("Runtime initialized in 3D Mode.")
        else:
            self.renderer = Renderer2D(self.state)
            self.physics_system = Physics2D(self.state)
            FileUtils.log_message("Runtime initialized in 2D Mode.")

        self.target_fps = self.state.config.project_settings.get("target_fps", 60)
        self.is_paused = False
        
        # Initialize Scene (This would be loaded by GameManager/Editor before Runtime starts)
        # Mock Scene for runtime:
        if not self.state.current_scene:
            self.state.current_scene = self._create_mock_scene()
            
        # Initial script execution (e.g., scene 'init' functions)
        self.state.script_engine.initialize_all_scripts(self.state.current_scene)


    def _create_mock_scene(self):
        """Creates a minimal Scene object for testing."""
        class MockGameObject:
            def __init__(self, uid, pos): 
                self.uid = uid
                self.name = uid
                self.position = Vector2(*pos) if not self.is_3d_mode else Vector3(*pos, 0)
                self.components = [{"type": "Script", "file": "player_movement.py"}]
                self.is_3d = self.is_3d_mode
                self.sprite = pygame.Surface((32, 32))
                self.sprite.fill(Color.red().to_rgb())
            def get_component(self, type):
                return next((c for c in self.components if c['type'] == type), None)
            
        class MockScene:
            def __init__(self, is_3d):
                self.is_3d = is_3d
                self._objects = [MockGameObject("P1001", (100, 100))]
            def get_all_objects(self): return self._objects
            def get_object(self, uid): return next((o for o in self._objects if o.uid == uid), None)
            
        return MockScene(self.is_3d_mode)

    def run(self, game_main_module=None):
        """Starts the main game loop."""
        running = True
        
        # If running a project, call the project's 'start_game' function (if available)
        if game_main_module and hasattr(game_main_module, 'start_game'):
             # Note: startup.py already loaded the scene data via a mock return
             # Here, we assume the initial scene is already set up in self.state.current_scene
             pass
        
        while running and self.state.is_running:
            # 1. Delta Time calculation
            dt = self.clock.tick(self.target_fps) / 1000.0 # seconds

            # 2. Input Handling
            running = self.state.input_manager.handle_events(pygame.event.get())
            if not running: break
            
            # Allow for engine-level exit key (e.g., ESC to stop runtime and return to editor)
            if self.state.input_manager.get_key_down('escape'):
                self.state.is_running = False
                break
                
            # 3. Game Update (only if not paused)
            if not self.is_paused:
                self._update_game(dt, game_main_module)

            # 4. Rendering
            self._render_game()

            # 5. Display Update
            pygame.display.flip()

        FileUtils.log_message("Engine Runtime loop stopped.")


    def _update_game(self, dt, game_main_module):
        """The main update pipeline executed every frame."""
        
        scene = self.state.current_scene
        
        # A. Network & Pre-Physics Update
        self.state.network_manager.update(dt) 

        # B. Scripting & Behavior Trees (user/AI logic)
        for obj in scene.get_all_objects():
            # Behavior Trees
            bt_comp = obj.get_component("BehaviorTree")
            if bt_comp:
                self.state.behavior_tree_manager.execute_tree(bt_comp["tree_name"], obj, dt)
                
            # Scripts
            script_comp = obj.get_component("Script")
            if script_comp and script_comp.get("file"):
                self.state.script_engine.execute_script_update(obj, script_comp["file"], dt)

        # C. Physics Update
        self.physics_system.update(dt, scene)

        # D. Cutscene, Particles, Audio, Camera
        self.state.cutscene_manager.update(dt)
        self.state.particle_manager.update(dt)
        self.state.camera_manager.update(dt, scene.get_all_objects()) # Update camera based on targets

        # E. Project-defined update (if running a main game loop)
        if game_main_module and hasattr(game_main_module, 'update_game'):
            try:
                # Pass the GameManager (which holds the state) to the project's update loop
                game_main_module.update_game(self.state.game_manager, dt)
            except Exception as e:
                FileUtils.log_error(f"Error in project's update_game function: {e}")
                
        # F. Post-Physics/Late Updates (if needed)

    def _render_game(self):
        """The main rendering pipeline."""
        
        scene = self.state.current_scene
        
        # Clear the screen (e.g., fill with black)
        self.surface.fill((0, 0, 0))

        # Get the active camera
        camera = self.state.camera_manager.get_active_camera()

        # Render the scene using the appropriate renderer
        self.renderer.render(self.surface, scene, camera)

        # Render particles/UI overlays
        self.state.particle_manager.render(self.surface, camera)
        
        # Render a simple FPS counter (Always good practice)
        fps = self.clock.get_fps()
        font = pygame.font.Font(None, 24)
        text = font.render(f"FPS: {fps:.1f}", True, (255, 255, 255))
        self.surface.blit(text, (10, 10))

    def cleanup(self):
        """Performs cleanup when the runtime stops."""
        self.state.script_engine.cleanup_all_scripts(self.state.current_scene)
        # Other manager cleanups if necessary
        FileUtils.log_message("Engine Runtime cleaned up.")

# ----------------------------------------------------------------------
# Minimal Runner for Testing EngineRuntime (Only active if run directly)
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # This block requires a running Pygame environment and minimal mocks
    try:
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Engine Runtime Test")

        # Create minimal state to pass to the Runtime
        class TestEngineState(MockState): # Inherits the MockState
            def __init__(self):
                super().__init__()
                self.is_running = True # Should be True for runtime
                self.game_manager = MockManager() # Mock the GameManager

        test_state = TestEngineState()
        
        # Initialize the Runtime
        runtime = EngineRuntime(screen, test_state)
        
        # Simple Mock Main Module to test project hooks
        class MockGameMain:
            def start_game(self, manager): FileUtils.log_message("Mock Game Start")
            def update_game(self, manager, dt): pass # Empty update

        # Run the loop
        runtime.run(game_main_module=MockGameMain())

    except Exception as e:
        FileUtils.log_error(f"Engine Runtime Test failed: {e}")
    finally:
        pygame.quit()
        sys.exit()