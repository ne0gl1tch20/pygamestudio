# engine/core/engine_state.py
from engine.core.engine_config import EngineConfig
import pygame # Used for display and event handling reference

class EngineState:
    """
    Central repository for the engine's current state, global variables,
    and references to all core managers. This object is passed around to 
    all subsystems to ensure centralized access to shared data.
    """
    
    def __init__(self, config: EngineConfig):
        """Initializes the engine state with core data."""
        
        # --- Core Engine State ---
        self.config = config                  # EngineConfig instance (persistent settings)
        self.is_running = True                # Main loop status (True=running, False=quit)
        self.is_editor_mode = False           # True if in editor, False if in game runtime
        self.is_game_paused = False           # Game play pause state
        self.current_project_path = config.editor_settings.get('last_opened_project')
        self.current_scene = None             # The currently loaded Scene object
        self.selected_object_uid = None       # UID of the object selected in the editor/inspector
        
        # --- Engine Managers (Populated by EditorMain or EngineRuntime) ---
        self.scene_manager = None             # engine.core.scene_manager
        self.game_manager = None              # engine.core.game_manager
        self.asset_loader = None              # engine.core.asset_loader
        self.input_manager = None             # engine.core.input_manager
        self.network_manager = None           # engine.core.network_manager (Client/Server state)
        self.plugin_manager = None            # engine.core.plugin_manager
        self.workshop_manager = None          # engine.core.workshop_manager
        self.export_manager = None            # engine.core.export_manager

        # --- Sub-System Managers ---
        self.audio_manager = None             # engine.managers.audio_manager
        self.particle_manager = None          # engine.managers.particle_manager
        self.save_load_manager = None         # engine.managers.save_load_manager
        self.camera_manager = None            # engine.managers.camera_manager
        self.cutscene_manager = None          # engine.managers.cutscene_manager
        self.behavior_tree_manager = None     # engine.managers.behavior_tree_manager
        self.script_engine = None             # engine.scripting.script_engine
        self.visual_script_runtime = None     # engine.scripting.visual_script_runtime
        
        # --- Physics and Rendering System References ---
        self.physics_system_2d = None         # engine.physics.physics2d
        self.physics_system_3d = None         # engine.physics.physics3d
        self.renderer_2d = None               # engine.rendering.renderer2d
        self.renderer_3d = None               # engine.rendering.renderer3d
        self.csg_modeler = None               # engine.rendering.csg_modeler
        
        # --- Pygame/Display References ---
        self.surface = None                   # Pygame display Surface (main window)
        self.clock = None                     # Pygame Clock object
        self.screen_rect = pygame.Rect(0, 0, config.editor_settings.get('screen_width', 1280), config.editor_settings.get('screen_height', 720))
        
        # --- Editor UI State ---
        # The editor UI state is managed by editor_ui.py, but essential flags are here
        self.ui_state = {
            "show_hierarchy": True,
            "show_inspector": True,
            "show_console": True,
            "show_assets": True,
            "show_settings": False,
            "show_help": False,
            "show_tutorial": False,
            "show_export": False,
            "show_workshop": False,
            "show_plugins": False,
            "show_network": False,
            "active_viewport": "2D", # "2D", "3D", "Cutscene", "VisualScript", "CSG"
            "active_tool": "move" # "move", "scale", "rotate"
        }
        
        # --- Utility Classes Reference (for easy access in scripts/managers) ---
        # NOTE: Utility classes are referenced here for runtime-script access (e.g., self.state.utils.Vector2)
        # They will be populated once the utils modules are imported in EditorMain/EngineRuntime.
        self.utils = {
            "Vector2": None, "Vector3": None, "Color": None, "MathUtils": None,
            "Timer": None, "FileUtils": None, "JsonSchema": None
        }

    def set_viewport_size(self, width, height):
        """Updates the internal screen dimensions."""
        self.screen_rect = pygame.Rect(0, 0, width, height)

    def get_object_by_uid(self, uid):
        """Helper to retrieve an object from the current scene by its UID."""
        if self.current_scene:
            return self.current_scene.get_object(uid)
        return None
        
    def get_theme_color(self, key):
        """
        Retrieves a color from the current theme (mocked until themes are fully implemented).
        EditorUI will eventually handle this via a ThemeManager.
        """
        theme = self.config.editor_settings.get('theme', 'dark')
        
        if theme == 'dark':
            colors = {
                "background": (30, 30, 30),
                "primary": (50, 50, 50), # Panel background
                "secondary": (70, 70, 70), # Button/Input background
                "accent": (50, 150, 255), # Blue for highlights
                "text": (200, 200, 200),
                "error": (255, 50, 50),
                "success": (50, 255, 50),
                "topbar_bg": (40, 40, 40)
            }
        else: # light theme mock
            colors = {
                "background": (200, 200, 200),
                "primary": (230, 230, 230),
                "secondary": (210, 210, 210),
                "accent": (0, 100, 200),
                "text": (50, 50, 50),
                "error": (200, 0, 0),
                "success": (0, 200, 0),
                "topbar_bg": (220, 220, 220)
            }
            
        return colors.get(key, (100, 100, 100))