import pygame
import os
import sys

# Ensure the root directory is in the Python path for internal imports
# This is crucial for running from a subdirectory structure
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Import essential engine parts
try:
    import startup
    from engine.core.engine_config import EngineConfig
    from editor.editor_main import EditorMain
except ImportError as e:
    print(f"FATAL ERROR: Could not import core components. Check project structure and dependencies. Error: {e}")
    sys.exit(1)

def main():
    """
    Main entry point for the Pygame Studio Engine.
    Initializes the environment, Pygame, and starts the Editor loop.
    """
    
    # 1. Initialize Engine Environment (creates folders, loads config, etc.)
    startup.init_engine_environment()
    config = EngineConfig()

    # 2. Pygame Initialization
    try:
        pygame.init()
    except Exception as e:
        print(f"Error initializing Pygame: {e}")
        sys.exit(1)

    # 3. Setup Display and Clock
    screen_width = config.editor_settings.get('screen_width', 1280)
    screen_height = config.editor_settings.get('screen_height', 720)
    
    pygame.display.set_caption("Pygame Studio Engine V4 - GODMODE PLUS")
    
    # Pygame flags: HWSURFACE for hardware acceleration, DOUBLEBUF for smooth rendering, RESIZABLE for editor features
    flags = pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE
    
    try:
        screen = pygame.display.set_mode((screen_width, screen_height), flags)
    except pygame.error as e:
        print(f"Error setting display mode: {e}. Trying default resolution.")
        screen = pygame.display.set_mode((1280, 720), flags)
        
    clock = pygame.time.Clock()

    # 4. Start the Editor
    editor = None
    try:
        # Instantiate the main Editor class and pass control to its run loop
        editor = EditorMain(screen, clock, config)
        editor.run()
        
    except Exception as e:
        # Critical error during editor runtime
        print("\n" + "="*50)
        print("CRITICAL ENGINE ERROR ENCOUNTERED:")
        import traceback
        traceback.print_exc(file=sys.stdout)
        print("="*50 + "\n")
    finally:
        # 5. Cleanup
        if editor:
            editor.cleanup() # Editor specific cleanup
        pygame.quit()
        print("Engine Shutdown Complete.")
        sys.exit(0)

if __name__ == "__main__":
    main()