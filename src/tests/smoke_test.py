# tests/smoke_test.py
import pygame
import sys
import os
import unittest
import time

# --- Setup Python Path to include project root ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Attempt to import core engine modules
try:
    import startup
    from engine.core.engine_config import EngineConfig
    from editor.editor_main import EditorMain
    from engine.utils.file_utils import FileUtils
    
    # Check for core dependencies
    # from engine.core.engine_state import EngineState
    # from engine.core.game_manager import GameManager
    # ...
    
except ImportError as e:
    print(f"[SMOKE TEST CRITICAL ERROR] Failed to import core engine modules: {e}")
    print("Ensure all modules are generated and environment setup is correct.")
    sys.exit(1)


class SmokeTest(unittest.TestCase):
    """
    A quick automated test to ensure the engine initializes, loads a sample project,
    runs one frame, and shuts down cleanly without crashing.
    """
    
    def setUp(self):
        """Initializes Pygame and the engine environment for the test."""
        # Suppress standard print output during setup
        self.stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        
        # 1. Initialize Engine Environment
        startup.init_engine_environment()
        config = EngineConfig()

        # 2. Pygame Initialization (minimal)
        pygame.init()
        
        # Create a small, headless/minimal surface for testing
        self.screen = pygame.display.set_mode((100, 100), pygame.HIDDEN)
        self.clock = pygame.time.Clock()
        
        # 3. Instantiate EditorMain (which initializes the whole engine state)
        self.editor = EditorMain(self.screen, self.clock, config)
        
        # Restore stdout
        sys.stdout.close()
        sys.stdout = self.stdout
        FileUtils.log_message("SmokeTest Setup: Engine initialized successfully.")


    def test_run_one_frame(self):
        """Tests the core engine loop by executing a single frame."""
        FileUtils.log_message("SmokeTest: Starting one-frame run...")
        
        # Ensure a project is loaded (the default example project)
        example_path = os.path.join(self.editor.state.config.editor_settings.get('default_project_path'), 'example_project')
        self.editor.game_manager.load_project(example_path)
        
        # Mock the necessary event to keep the loop moving
        events = [pygame.event.Event(pygame.NOEVENT)]
        
        # Suppress all output for the actual frame run
        self.stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        
        # --- EXECUTE SINGLE FRAME ---
        try:
            # 1. Handle Input (just passes the mock event)
            self.editor.input_manager.handle_events(events)
            
            # 2. Editor Update (handles autosave, camera, particles)
            self.editor._editor_update(dt=1/60.0)
            
            # 3. Rendering
            self.editor._render_editor()
            
            # Mock screen flip (no actual change visible since HIDDEN)
            # pygame.display.flip() 

            frame_ran_successfully = True
        except Exception as e:
            frame_ran_successfully = False
            self.fail(f"Engine crashed during single frame execution: {e}")
        finally:
            # Restore stdout
            sys.stdout.close()
            sys.stdout = self.stdout
            
        self.assertTrue(frame_ran_successfully, "Single frame execution failed.")
        FileUtils.log_message("SmokeTest: Single frame run completed successfully.")


    def tearDown(self):
        """Cleans up the Pygame environment."""
        self.editor.cleanup()
        pygame.quit()
        FileUtils.log_message("SmokeTest Teardown: Pygame shut down.")
        
# --- Main Test Runner ---
if __name__ == '__main__':
    # Run the test
    unittest.main(argv=['first-arg-is-ignored'], exit=False)