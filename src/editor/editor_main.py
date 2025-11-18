# editor/editor_main.py
import pygame
import sys
import os
from typing import Dict, Any, List

# --- Engine Core Imports ---
try:
    from engine.core.engine_config import EngineConfig
    from engine.core.engine_state import EngineState
    from engine.core.scene_manager import SceneManager
    from engine.core.game_manager import GameManager
    from engine.core.asset_loader import AssetLoader
    from engine.core.input_manager import InputManager
    from engine.core.network_manager import NetworkManager
    from engine.core.plugin_manager import PluginManager
    from engine.core.workshop_manager import WorkshopManager
    from engine.core.export_manager import ExportManager
    from engine.managers.save_load_manager import SaveLoadManager
    from engine.managers.camera_manager import CameraManager
    from engine.managers.audio_manager import AudioManager
    from engine.managers.particle_manager import ParticleManager
    from engine.managers.cutscene_manager import CutsceneManager
    from engine.managers.behavior_tree_manager import BehaviorTreeManager
    from engine.rendering.renderer2d import Renderer2D
    from engine.rendering.renderer3d import Renderer3D
    from engine.rendering.mesh_loader import MeshLoader
    from engine.rendering.material import MaterialManager
    from engine.rendering.shader_system import ShaderSystem
    from engine.rendering.csg_modeler import CSGModeler
    from engine.scripting.script_engine import ScriptEngine
    from engine.scripting.visual_script_runtime import VisualScriptRuntime
    from engine.utils.file_utils import FileUtils
    from engine.utils.timer import Timer
    from engine.utils.vector2 import Vector2 # Needed for state.utils population
    from engine.utils.vector3 import Vector3 # Needed for state.utils population
    from engine.utils.color import Color # Needed for state.utils population
    from engine.utils.math_utils import MathUtils # Needed for state.utils population
    from engine.utils.json_schema import JsonSchema # Needed for state.utils population
    
    # --- Editor UI Imports ---
    from editor.editor_ui import EditorUI
    from engine.gui.topbar import TopBar
    from engine.gui.dock_panels import DockPanelManager
    from editor.editor_viewport2d import EditorViewport2D
    from editor.editor_viewport3d import EditorViewport3D

except ImportError as e:
    print(f"[EditorMain CRITICAL Import Error] {e}. Cannot start editor.")
    sys.exit(1)


class EditorMain:
    """
    The main class for the Pygame Studio Editor Interface.
    It orchestrates all managers and the UI drawing loop.
    """
    
    def __init__(self, surface: pygame.Surface, clock: pygame.time.Clock, config: EngineConfig):
        # Core Pygame components
        self.surface = surface
        self.clock = clock

        # --- 1. Core State & Configuration ---
        self.state = EngineState(config)
        self.state.surface = surface
        self.state.clock = clock
        self.state.is_editor_mode = True

        # Setup screen_rect for TopBar & layout calculations
        self.state.screen_rect = pygame.Rect(
            0, 0,
            config.editor_settings.get('screen_width', 1280),
            config.editor_settings.get('screen_height', 720)
        )

        # Static reference for FileUtils logging fallback (if needed)
        EngineState.instance = self.state

        # --- 2. Initialize Managers (Order is important for dependencies) ---
        self._populate_state_utils()

        # IO / Persistence / Project
        self.save_load_manager = SaveLoadManager(self.state)
        self.game_manager = GameManager(self.state)
        self.asset_loader = AssetLoader(self.state)
        self.input_manager = InputManager(self.state)
        self.plugin_manager = PluginManager(self.state)
        self.export_manager = ExportManager(self.state)
        self.workshop_manager = WorkshopManager(self.state)
        self.network_manager = NetworkManager(self.state)

        # Rendering / Modeling
        self.mesh_loader = MeshLoader(self.state)
        self.material_manager = MaterialManager(self.state)
        self.shader_system = ShaderSystem(self.state)
        self.csg_modeler = CSGModeler(self.state)
        self.renderer2d = Renderer2D(self.state)
        self.renderer3d = Renderer3D(self.state)

        # Physics
        self.physics2d = self._mock_physics_init("Physics2D")
        self.physics3d = self._mock_physics_init("Physics3D")

        # Game Systems
        self.audio_manager = AudioManager(self.state)
        self.particle_manager = ParticleManager(self.state)
        self.camera_manager = CameraManager(self.state)
        self.cutscene_manager = CutsceneManager(self.state)
        self.behavior_tree_manager = BehaviorTreeManager(self.state)
        self.script_engine = ScriptEngine(self.state)
        self.visual_script_runtime = VisualScriptRuntime(self.state)
        self.scene_manager = SceneManager(self.state)

        # --- 3. UI and Viewport ---
        self.dock_manager = DockPanelManager(self.state, topbar_height=TopBar.HEIGHT)
        self.topbar = TopBar(self.state, self.dock_manager)  # <-- fixed, removed rect, text
        self.editor_ui = EditorUI(self.state, self.topbar, self.dock_manager)

        self.viewport_2d = EditorViewport2D(self.state, self.renderer2d, self.camera_manager)
        self.viewport_3d = EditorViewport3D(self.state, self.renderer3d, self.camera_manager)

        # --- 4. Load Project ---
        last_project = config.editor_settings.get('last_opened_project')
        if last_project and os.path.exists(last_project):
            self.game_manager.load_project(last_project)
        else:
            # Create a default empty scene if no project is loaded
            self.scene_manager.create_new_scene(
                "New Empty Scene",
                is_3d=config.project_settings.get("is_3d_mode", False)
            )

        # Autosave Timer
        self.autosave_timer = Timer(
            duration=self.state.config.editor_settings.get('autosave_interval_minutes', 5) * 60,
            is_looping=True
        )
        self.autosave_timer.start()

        FileUtils.log_message("EditorMain initialization complete. Entering main loop.")


    def _populate_state_utils(self):
        """Populates the state.utils dictionary with core utility classes."""
        self.state.utils['Vector2'] = Vector2
        self.state.utils['Vector3'] = Vector3
        self.state.utils['Color'] = Color
        self.state.utils['MathUtils'] = MathUtils
        self.state.utils['Timer'] = Timer
        self.state.utils['FileUtils'] = FileUtils
        self.state.utils['JsonSchema'] = JsonSchema
        
    def _mock_physics_init(self, name):
        """Mocks initialization of physics system that isn't fully required in editor's main loop."""
        try:
            if name == "Physics2D":
                 from engine.physics.physics2d import Physics2D
                 return Physics2D(self.state)
            elif name == "Physics3D":
                 from engine.physics.physics3d import Physics3D
                 return Physics3D(self.state)
        except ImportError:
            FileUtils.log_warning(f"Failed to fully initialize {name}.")
            return None
        return None

    def run(self):
        """The main editor loop."""
        while self.state.is_running:
            
            # --- 1. Delta Time & Clock ---
            dt = self.clock.tick(60) / 1000.0 # Cap editor FPS at 60

            # --- 2. Input Handling ---
            events = pygame.event.get()
            self.state.is_running = self.input_manager.handle_events(events)
            if not self.state.is_running: break
            
            # --- 3. UI and Event Processing ---
            if self.state.is_editor_mode:
                self._handle_editor_input(events, dt)
            
            # --- 4. Game Runtime Simulation (Only if game is running) ---
            if self.state.game_manager.is_game_running:
                # The game_manager.start_game() call runs a blocking loop (EngineRuntime.run), 
                # so this block is skipped until EngineRuntime returns control.
                # When control is returned, is_game_running is False and is_editor_mode is True.
                pass 
                
            # --- 5. Editor Update ---
            if self.state.is_editor_mode:
                self._editor_update(dt)

            # --- 6. Rendering ---
            self._render_editor()

            # --- 7. Display Update ---
            pygame.display.flip()

    def _handle_editor_input(self, events: list[pygame.event.Event], dt: float):
        """Handles events specific to the editor UI and viewport."""
        
        # 1. UI (TopBar, Docked Panels) - Highest Priority
        consumed_by_ui = self.editor_ui.handle_events(events)
        
        # 2. Viewport (Handles gizmos, camera movement, object selection) - Lower Priority
        if not consumed_by_ui:
            if self.state.ui_state.get('active_viewport') == '3D':
                 self.viewport_3d.handle_events(events, dt, self.dock_manager.viewport_rect)
            else: # Defaults to 2D
                 self.viewport_2d.handle_events(events, dt, self.dock_manager.viewport_rect)


    def _editor_update(self, dt: float):
        """Update logic for non-rendering editor components."""
        
        # 1. Autosave Check
        self.save_load_manager.autosave_check()
        
        # 2. Viewport Update (Camera movement)
        self.camera_manager.update(dt, self.state.current_scene.get_all_objects() if self.state.current_scene else [])
        
        # 3. Particle System (For editor preview)
        self.particle_manager.update(dt)


    def _render_editor(self):
        """Renders the entire editor interface."""
        
        # 1. Clear Screen
        self.surface.fill(self.state.get_theme_color('background'))
        
        # 2. Render Main Viewport Content
        viewport_rect = self.dock_manager.viewport_rect
        viewport_surface = self.surface.subsurface(viewport_rect)
        
        if self.state.current_scene:
            if self.state.ui_state.get('active_viewport') == '3D' and self.state.current_scene.is_3d:
                self.viewport_3d.draw(viewport_surface)
            else:
                self.viewport_2d.draw(viewport_surface)
        else:
            # Draw empty scene placeholder
            viewport_surface.fill(self.state.get_theme_color('primary'))
            font = pygame.font.Font(None, 48)
            text = font.render("NO SCENE LOADED", True, self.state.get_theme_color('text_disabled'))
            viewport_surface.blit(text, text.get_rect(center=viewport_surface.get_rect().center))


        # 3. Render Editor UI (TopBar and Docked Panels)
        self.editor_ui.draw(self.surface)


    def cleanup(self):
        """Performs cleanup upon editor exit."""
        # Save current config settings
        self.state.config.save_config()
        FileUtils.log_message("EditorMain cleanup complete.")