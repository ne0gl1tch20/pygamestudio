# editor/editor_viewport2d.py
import pygame
import sys
import copy
import math

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.rendering.renderer2d import Renderer2D
    from engine.managers.camera_manager import CameraManager, CameraObject
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.utils.math_utils import MathUtils
    from engine.gui.gui_widgets import Button # For gizmo buttons
    from engine.utils.color import Color
except ImportError as e:
    print(f"[EditorViewport2D Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        selected_object_uid = None
        current_scene = None
        ui_state = {"active_tool": "move"}
        def get_object_by_uid(self, uid): return None
        def get_icon(self, name): 
            s = pygame.Surface((24, 24)); s.fill((255, 255, 255)); return s
        def __init__(self): self.input_manager = self
    class Renderer2D:
        def __init__(self, state): pass
        def render(self, surface, scene, camera): surface.fill((10, 10, 10))
        def _world_to_screen(self, pos, cam, rect): return (pos.x + rect.width // 2, pos.y + rect.height // 2)
    class CameraManager:
        def __init__(self, state): self.active_cam = self.MockCamera()
        def get_active_camera(self): return self.active_cam
        class MockCamera:
            def __init__(self): self.position = Vector2(0, 0); self.zoom = 1.0
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[EV2D-INFO] {msg}")
    class Vector2:
        def __init__(self, x, y): self.x, self.y = x, y
        def __sub__(self, other): return Vector2(self.x - other.x, self.y - other.y)
        def __add__(self, other): return Vector2(self.x + other.x, self.y + other.y)
        def __mul__(self, scalar): return Vector2(self.x * scalar, self.y * scalar)
        def to_tuple(self): return (self.x, self.y)
        @property
        def magnitude(self): return (self.x**2 + self.y**2)**0.5
    class MathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Color:
        @staticmethod
        def red(): return (255, 0, 0)
        @staticmethod
        def blue(): return (0, 0, 255)
        @staticmethod
        def yellow(): return (255, 255, 0)


class EditorViewport2D:
    """
    Manages the 2D viewport, including rendering, camera manipulation, 
    gizmos, and object selection.
    """
    GIZMO_SIZE = 15 # Radius/half-size of the gizmo visual
    
    def __init__(self, state: EngineState, renderer: Renderer2D, camera_manager: CameraManager):
        self.state = state
        self.renderer = renderer
        self.camera_manager = camera_manager
        
        # Interaction State
        self.is_panning = False
        self.is_gizmo_dragging = False
        self.gizmo_axis = None # 'x', 'y', 'rot'
        self.drag_start_world_pos = None
        self.drag_start_object_pos = None
        self.viewport_rect = pygame.Rect(0, 0, 1, 1) # Updated by EditorUI
        
        # UI Elements for Gizmo Switching
        self.btn_move = Button(pygame.Rect(0, 0, 30, 30), "↔️",  action=lambda: self._set_tool('move'))
        self.btn_rotate = Button(pygame.Rect(0, 0, 30, 30), "🔃",  action=lambda: self._set_tool('rotate'))
        self.btn_scale = Button(pygame.Rect(0, 0, 30, 30), "⤢", action=lambda: self._set_tool('scale'))
        
        FileUtils.log_message("EditorViewport2D initialized.")

    def _set_tool(self, tool_name: str):
        """Sets the active manipulation tool."""
        self.state.ui_state['active_tool'] = tool_name
        FileUtils.log_message(f"Viewport tool set to: {tool_name}")

    # --- Coordinate Conversion ---

    def _screen_to_world(self, screen_pos: tuple[int, int], camera: CameraObject, viewport_rect: pygame.Rect) -> Vector2:
        """Converts screen pixel coordinates to world coordinates."""
        
        cam_pos = camera.position
        zoom = camera.zoom
        
        # Center of the viewport (in screen space)
        center_x = viewport_rect.width / 2
        center_y = viewport_rect.height / 2
        
        # Relative position from viewport center
        rel_x = screen_pos[0] - center_x
        rel_y = screen_pos[1] - center_y
        
        # Apply inverse zoom and add camera position
        world_x = rel_x / zoom + cam_pos.x
        world_y = rel_y / zoom + cam_pos.y
        
        return Vector2(world_x, world_y)

    # --- Event Handling ---

    def handle_events(self, events: list[pygame.event.Event], dt: float, viewport_rect: pygame.Rect) -> bool:
        """Handles mouse/keyboard input for the viewport."""
        self.viewport_rect = viewport_rect
        consumed = False
        
        # 1. Update Gizmo Button Rects (relative to viewport)
        self.btn_move.rect.topleft = (viewport_rect.x + 10, viewport_rect.y + 10)
        self.btn_rotate.rect.topleft = (viewport_rect.x + 45, viewport_rect.y + 10)
        self.btn_scale.rect.topleft = (viewport_rect.x + 80, viewport_rect.y + 10)
        
        # 2. Check if mouse is over the viewport area
        mouse_pos = pygame.mouse.get_pos()
        is_over_viewport = self.viewport_rect.collidepoint(mouse_pos)
        
        # 3. Gizmo Button Events
        for btn in [self.btn_move, self.btn_rotate, self.btn_scale]:
            if btn.handle_event(events[0] if events else None): # Pass first event only
                consumed = True

        camera = self.camera_manager.get_active_camera()
        if not camera: return consumed

        # Translate mouse position to viewport-relative
        viewport_mouse_pos = (mouse_pos[0] - viewport_rect.x, mouse_pos[1] - viewport_rect.y)

        for event in events:
            # --- Camera Panning (MMB/Shift+LMB) ---
            if is_over_viewport and not self.is_gizmo_dragging:
                if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 2) or \
                   (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and pygame.key.get_pressed()[pygame.K_LSHIFT]):
                    self.is_panning = True
                    self.drag_start_world_pos = self._screen_to_world(viewport_mouse_pos, camera, viewport_rect)
                    self.state.input_manager.consume_input()
                    return True
                
            if event.type == pygame.MOUSEBUTTONUP and (event.button == 2 or self.is_panning):
                self.is_panning = False
                if consumed: return True
                
            if event.type == pygame.MOUSEMOTION and self.is_panning:
                current_world_pos = self._screen_to_world(viewport_mouse_pos, camera, viewport_rect)
                
                # Calculate movement delta in world space and move camera
                delta_world = current_world_pos - self.drag_start_world_pos
                camera.position -= delta_world
                self.state.input_manager.consume_input()
                return True
                
            # --- Zooming (Mouse Wheel) ---
            if is_over_viewport and event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: # Scroll up (Zoom in)
                    camera.zoom = MathUtils.clamp(camera.zoom * 1.1, 0.1, 5.0)
                    self.state.input_manager.consume_input()
                    return True
                elif event.button == 5: # Scroll down (Zoom out)
                    camera.zoom = MathUtils.clamp(camera.zoom / 1.1, 0.1, 5.0)
                    self.state.input_manager.consume_input()
                    return True
                    
            # --- Gizmo Dragging / Object Selection (LMB) ---
            if is_over_viewport:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    
                    selected_obj = self.state.get_object_by_uid(self.state.selected_object_uid)
                    
                    # 1. Try to start dragging the gizmo if an object is selected
                    if selected_obj:
                        gizmo_axis = self._check_gizmo_hit(selected_obj, camera, viewport_rect, viewport_mouse_pos)
                        if gizmo_axis:
                            self.is_gizmo_dragging = True
                            self.gizmo_axis = gizmo_axis
                            self.drag_start_object_pos = selected_obj.position.copy()
                            self.drag_start_world_pos = self._screen_to_world(viewport_mouse_pos, camera, viewport_rect)
                            self.state.input_manager.consume_input()
                            return True
                    
                    # 2. If not dragging gizmo, try to select an object
                    if not self.is_gizmo_dragging:
                        self._select_object_at_point(viewport_mouse_pos, camera, viewport_rect)
                        self.state.input_manager.consume_input()
                        return True

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_gizmo_dragging:
                    self.is_gizmo_dragging = False
                    self.gizmo_axis = None
                    return True

                elif event.type == pygame.MOUSEMOTION and self.is_gizmo_dragging:
                    self._apply_gizmo_drag(selected_obj, camera, viewport_rect, viewport_mouse_pos)
                    return True
                    
        return consumed

    # --- Selection Logic ---

    def _select_object_at_point(self, mouse_pos: tuple[int, int], camera: CameraObject, viewport_rect: pygame.Rect):
        """Performs a hit test to select a SceneObject."""
        
        scene = self.state.current_scene
        if not scene: return
        
        # Reverse iterate (higher layers/later drawn objects on top)
        for obj in reversed(scene.get_all_objects()):
            if obj.is_3d: continue # Skip 3D in 2D viewport

            # Mock check: Check if mouse hits the object's scaled/zoomed AABB/Sprite Rect
            # NOTE: Renderer2D needs to expose the screen rect of the object for proper picking
            
            # Use the renderer's world-to-screen to get object's center
            screen_center = self.renderer._world_to_screen(obj.position, camera, viewport_rect)
            
            # Mock screen AABB (based on a fixed size/scale/zoom)
            size = 32 # Mock base size
            w = size * obj.scale.x * camera.zoom
            h = size * obj.scale.y * camera.zoom
            
            obj_rect = pygame.Rect(0, 0, w, h)
            obj_rect.center = screen_center
            
            # Offset mouse pos to account for viewport rect (already done by caller)
            local_mouse_pos = (mouse_pos[0] + viewport_rect.x, mouse_pos[1] + viewport_rect.y)
            
            if obj_rect.collidepoint(local_mouse_pos):
                self.state.selected_object_uid = obj.uid
                FileUtils.log_message(f"Selected: {obj.name}")
                return
                
        self.state.selected_object_uid = None # Deselect
        
    # --- Gizmo Logic ---

    def _check_gizmo_hit(self, obj: any, camera: CameraObject, viewport_rect: pygame.Rect, mouse_pos: tuple[int, int]) -> str | None:
        """Checks if the mouse is hovering over an axis of the current gizmo."""
        
        tool = self.state.ui_state.get('active_tool')
        if not obj or tool not in ['move', 'rotate', 'scale']: return None
        
        # Object center in screen space
        screen_center = self.renderer._world_to_screen(obj.position, camera, viewport_rect)
        
        # Check X-axis (Move/Scale)
        if tool in ['move', 'scale']:
            x_gizmo_rect = pygame.Rect(screen_center[0], screen_center[1] - 5, 2 * self.GIZMO_SIZE, 10)
            x_gizmo_rect.center = (screen_center[0] + self.GIZMO_SIZE, screen_center[1])
            if x_gizmo_rect.collidepoint(mouse_pos): return 'x'
            
            y_gizmo_rect = pygame.Rect(screen_center[0] - 5, screen_center[1], 10, 2 * self.GIZMO_SIZE)
            y_gizmo_rect.center = (screen_center[0], screen_center[1] - self.GIZMO_SIZE)
            if y_gizmo_rect.collidepoint(mouse_pos): return 'y'
            
        # Check Rotation Gizmo (Mock circle)
        elif tool == 'rotate':
            dist = MathUtils.distance(mouse_pos, screen_center)
            if abs(dist - self.GIZMO_SIZE * 2) < 5: # Close to the circle edge
                return 'rot'
                
        return None

    def _apply_gizmo_drag(self, obj: any, camera: CameraObject, viewport_rect: pygame.Rect, current_mouse_pos: tuple[int, int]):
        """Calculates the world-space delta and applies the transformation to the object."""
        if not obj or not self.drag_start_world_pos: return

        current_world_pos = self._screen_to_world(current_mouse_pos, camera, viewport_rect)
        
        # Delta in world space
        delta_world = current_world_pos - self.drag_start_world_pos
        
        tool = self.state.ui_state.get('active_tool')
        
        if tool == 'move':
            # Position = Drag Start Object Position + Delta World
            
            if self.gizmo_axis == 'x':
                obj.position.x = self.drag_start_object_pos.x + delta_world.x
            elif self.gizmo_axis == 'y':
                obj.position.y = self.drag_start_object_pos.y + delta_world.y
            
            # Apply grid snap if enabled (Mock)
            if self.state.config.editor_settings.get('grid_snap', True):
                 snap_size = 32.0 / camera.zoom # Base grid size in world units
                 obj.position.x = round(obj.position.x / snap_size) * snap_size
                 obj.position.y = round(obj.position.y / snap_size) * snap_size
            
        elif tool == 'scale':
            # Scale = Drag Start Scale * (1 + Drag Amount)
            
            # Simple linear scale change based on drag distance (very rough mock)
            scale_factor = 1.0 + delta_world.magnitude / 100.0 * (1 if delta_world.x > 0 else -1)
            scale_factor = MathUtils.clamp(scale_factor, 0.1, 10.0)
            
            if self.gizmo_axis == 'x':
                obj.scale.x = MathUtils.clamp(obj.scale.x * scale_factor, 0.1, 10.0)
            elif self.gizmo_axis == 'y':
                obj.scale.y = MathUtils.clamp(obj.scale.y * scale_factor, 0.1, 10.0)
                
            # NOTE: Re-set drag starting point to current to avoid exponential scaling
            self.drag_start_world_pos = current_world_pos
            
        elif tool == 'rotate':
            # Rotation change based on mouse movement's angle relative to center
            # Mock: Change rotation by horizontal delta only (simple rotation)
            angle_delta = delta_world.x * 0.5 # 0.5 is sensitivity
            obj.rotation += angle_delta
            obj.rotation %= 360.0

    # --- Rendering ---

    def draw(self, surface: pygame.Surface):
        """Renders the 2D scene, gizmos, and viewport UI."""
        
        scene = self.state.current_scene
        camera = self.camera_manager.get_active_camera()
        theme = self.state.config.editor_settings.get('theme', 'dark')
        
        # 1. Render the actual scene via Renderer2D
        if scene and camera:
            self.renderer.render(surface, scene, camera) # Renders scene and grid/selection box
        else:
            surface.fill(self.state.get_theme_color('primary'))
        
        # 2. Render Gizmos and Tools
        self._draw_viewport_ui(surface, camera, theme)
        
        # 3. Draw active Gizmo (over selected object)
        if self.state.selected_object_uid:
            selected_obj = self.state.get_object_by_uid(self.state.selected_object_uid)
            if selected_obj:
                self._draw_gizmo(surface, selected_obj, camera)

    def _draw_viewport_ui(self, surface: pygame.Surface, camera: CameraObject, theme: str):
        """Renders the top-left tool buttons and debug info."""
        
        # 1. Tool Buttons
        active_tool = self.state.ui_state.get('active_tool', 'move')
        
        self.btn_move.is_toggled = (active_tool == 'move')
        self.btn_rotate.is_toggled = (active_tool == 'rotate')
        self.btn_scale.is_toggled = (active_tool == 'scale')

        self.btn_move.draw(surface, theme)
        self.btn_rotate.draw(surface, theme)
        self.btn_scale.draw(surface, theme)
        
        # 2. Debug Info (Camera position, Zoom)
        font = pygame.font.Font(None, 18)
        text_color = self.state.get_theme_color('text')
        
        if camera:
            pos_text = f"Cam: ({camera.position.x:.1f}, {camera.position.y:.1f})"
            zoom_text = f"Zoom: {camera.zoom:.2f}x"
            
            pos_surf = font.render(pos_text, True, text_color)
            zoom_surf = font.render(zoom_text, True, text_color)
            
            surface.blit(pos_surf, (self.viewport_rect.width - pos_surf.get_width() - 5, 5))
            surface.blit(zoom_surf, (self.viewport_rect.width - zoom_surf.get_width() - 5, 25))

    def _draw_gizmo(self, surface: pygame.Surface, obj: any, camera: CameraObject):
        """Draws the selected gizmo (Move, Rotate, Scale) over the selected object."""
        
        # Get screen center of the object (already done by the renderer but for clarity)
        screen_center = self.renderer._world_to_screen(obj.position, camera, self.viewport_rect)
        
        tool = self.state.ui_state.get('active_tool', 'move')
        
        # Common constants
        axis_length = self.GIZMO_SIZE * 3
        axis_width = 3
        
        # Highlight color if dragging
        highlight_color = Color.yellow().to_rgb()
        
        if tool == 'move':
            # X-Axis (Red)
            x_end = (screen_center[0] + axis_length, screen_center[1])
            x_color = Color.red().to_rgb() if self.is_gizmo_dragging and self.gizmo_axis == 'x' else Color.red().to_rgb()
            pygame.draw.line(surface, x_color, screen_center, x_end, axis_width)
            
            # Y-Axis (Blue/Green - Pygame Y-down makes Y-axis Downward)
            y_end = (screen_center[0], screen_center[1] - axis_length) # Draw upwards
            y_color = Color.blue().to_rgb() if self.is_gizmo_dragging and self.gizmo_axis == 'y' else Color.blue().to_rgb()
            pygame.draw.line(surface, y_color, screen_center, y_end, axis_width)
            
        elif tool == 'scale':
            # Draw lines similarly to move, but with end caps (mock)
            # X-Axis (Red with a square cap)
            x_end = (screen_center[0] + axis_length, screen_center[1])
            x_color = Color.red().to_rgb() if self.is_gizmo_dragging and self.gizmo_axis == 'x' else Color.red().to_rgb()
            pygame.draw.line(surface, x_color, screen_center, x_end, axis_width)
            pygame.draw.rect(surface, x_color, pygame.Rect(x_end[0] - 5, x_end[1] - 5, 10, 10))
            
            # Y-Axis (Blue with a square cap)
            y_end = (screen_center[0], screen_center[1] - axis_length)
            y_color = Color.blue().to_rgb() if self.is_gizmo_dragging and self.gizmo_axis == 'y' else Color.blue().to_rgb()
            pygame.draw.line(surface, y_color, screen_center, y_end, axis_width)
            pygame.draw.rect(surface, y_color, pygame.Rect(y_end[0] - 5, y_end[1] - 5, 10, 10))
            
        elif tool == 'rotate':
            # Draw a circle around the object for rotation (Green)
            radius = axis_length * 1.5
            rot_color = highlight_color if self.is_gizmo_dragging and self.gizmo_axis == 'rot' else Color.green().to_rgb()
            pygame.draw.circle(surface, rot_color, screen_center, int(radius), 2)