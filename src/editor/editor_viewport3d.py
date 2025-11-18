# editor/editor_viewport3d.py
import pygame
import sys
import copy
import math

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.rendering.renderer3d import Renderer3D
    from engine.managers.camera_manager import CameraManager, CameraObject
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector3 import Vector3
    from engine.utils.math_utils import MathUtils
    from engine.gui.gui_widgets import Button
    from engine.utils.color import Color
except ImportError as e:
    print(f"[EditorViewport3D Import Error] {e}. Using Internal Mocks.")
    class EngineState:
        def get_theme_color(self, k): return (40, 40, 40)
        selected_object_uid = None
        current_scene = None
        ui_state = {"active_tool": "move"}
        def get_object_by_uid(self, uid): return None
        def get_icon(self, name): 
            s = pygame.Surface((24, 24)); s.fill((255, 255, 255)); return s
        def __init__(self): self.input_manager = self
    class Renderer3D:
        def __init__(self, state): pass
        def render(self, surface, scene, camera): surface.fill((10, 10, 50)) # Dark blue/3D mock color
    class CameraManager:
        def __init__(self, state): self.active_cam = self.MockCamera()
        def get_active_camera(self): return self.active_cam
        class MockCamera:
            def __init__(self): self.position = Vector3(0, 0, 0); self.rotation = Vector3(0, 0, 0); self.fov = 60.0
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[EV3D-INFO] {msg}")
    class Vector3:
        def __init__(self, x, y, z): self.x, self.y, self.z = x, y, z
        def __sub__(self, other): return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
        def __add__(self, other): return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
        def __mul__(self, scalar): return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
        def to_tuple(self): return (self.x, self.y, self.z)
        def normalize(self): return self * (1/self.magnitude if self.magnitude > 0 else 0)
        @property
        def magnitude(self): return (self.x**2 + self.y**2 + self.z**2)**0.5
    class MathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))
        @staticmethod
        def deg_to_rad(degrees): return degrees * (math.pi / 180.0)
    class Button:
        def __init__(self, rect, text, icon=None, **kwargs): self.rect = rect
        def handle_event(self, event): return False
        def draw(self, surface, theme): pass
    class Color:
        @staticmethod
        def red(): return (255, 0, 0)
        @staticmethod
        def green(): return (0, 255, 0)
        @staticmethod
        def blue(): return (0, 0, 255)
        @staticmethod
        def yellow(): return (255, 255, 0)
        @staticmethod
        def white(): return (255, 255, 255)


class EditorViewport3D:
    """
    Manages the 3D viewport, including rendering, free-look camera, 
    gizmos, and object selection.
    """
    GIZMO_SIZE = 0.5 # Gizmo size in world units (will be projected)
    
    def __init__(self, state: EngineState, renderer: Renderer3D, camera_manager: CameraManager):
        self.state = state
        self.renderer = renderer
        self.camera_manager = camera_manager
        
        # Interaction State
        self.is_panning = False         # MMB/Shift+LMB for horizontal/vertical move
        self.is_rotating = False        # RMB/Alt+LMB for orbit/free look
        self.is_gizmo_dragging = False
        self.gizmo_axis = None          # 'x', 'y', 'z', 'rot_x', etc.
        self.drag_start_world_pos = None # World position at the start of drag
        self.drag_start_object_pos = None # Object position at the start of drag
        self.viewport_rect = pygame.Rect(0, 0, 1, 1) # Updated by EditorUI
        
        # Cached UI Elements (Mock)
        self.btn_move = Button(pygame.Rect(0, 0, 30, 30), "↔️",  action=lambda: self._set_tool('move'))
        self.btn_rotate = Button(pygame.Rect(0, 0, 30, 30), "🔃",  action=lambda: self._set_tool('rotate'))
        self.btn_scale = Button(pygame.Rect(0, 0, 30, 30), "⤢",  action=lambda: self._set_tool('scale'))

        FileUtils.log_message("EditorViewport3D initialized.")

    def _set_tool(self, tool_name: str):
        """Sets the active manipulation tool."""
        self.state.ui_state['active_tool'] = tool_name
        FileUtils.log_message(f"3D Viewport tool set to: {tool_name}")

    # --- 3D Camera / Coordinate Conversion Mocks ---

    def _screen_to_world_ray(self, screen_pos: tuple[int, int], camera: CameraObject, viewport_rect: pygame.Rect) -> tuple[Vector3, Vector3]:
        """
        Mocks casting a ray from screen space into world space.
        Returns (ray_origin, ray_direction).
        """
        # This is highly complex and depends on the projection matrix.
        # We return a simple mock ray: Camera position and a straight forward vector.
        
        # Simple Ray Mock: Origin is camera, direction is "forward"
        # In a real engine, the direction is calculated from screen_pos, FOV, and aspect ratio.
        
        # Mock Camera Forward vector (simplified from rotation.y)
        yaw_rad = MathUtils.deg_to_rad(camera.rotation.y)
        forward_x = -math.sin(yaw_rad)
        forward_z = math.cos(yaw_rad)
        forward = Vector3(forward_x, 0.0, forward_z).normalize()
        
        return camera.position, forward
        
    def _world_to_screen_mock(self, world_pos: Vector3, camera: CameraObject, viewport_rect: pygame.Rect) -> tuple[int, int]:
        """
        Mocks the projection of a world coordinate to a screen coordinate.
        Returns (screen_x, screen_y).
        """
        # Simple projection: ignores Z, just centers the X/Y difference
        rel_pos = world_pos - camera.position
        
        # Z-depth scaling (simple perspective mock)
        z_scale = 1.0 / max(0.1, rel_pos.z) if camera.rotation.z == 0 else 1.0
        
        screen_x = int(rel_pos.x * z_scale * 50 + viewport_rect.width / 2)
        screen_y = int(-rel_pos.y * z_scale * 50 + viewport_rect.height / 2)
        
        return (screen_x, screen_y)


    # --- Event Handling ---

    def handle_events(self, events: list[pygame.event.Event], dt: float, viewport_rect: pygame.Rect) -> bool:
        """Handles mouse/keyboard input for the 3D viewport (Free Look, Gizmos)."""
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
            if btn.handle_event(events[0] if events else None): 
                consumed = True

        camera = self.camera_manager.get_active_camera()
        if not camera: return consumed

        # Translate mouse position to viewport-relative
        viewport_mouse_pos = (mouse_pos[0] - viewport_rect.x, mouse_pos[1] - viewport_rect.y)

        for event in events:
            # --- Camera Free Look / Orbit (RMB) ---
            if is_over_viewport and event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self.is_rotating = True
                self.state.input_manager.consume_input()
                return True
                
            if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                self.is_rotating = False
                return True
                
            if event.type == pygame.MOUSEMOTION and self.is_rotating:
                # Apply rotation delta to camera (simple Euler rotation)
                mouse_dx, mouse_dy = self.state.input_manager.mouse_delta
                sensitivity = 0.15 * dt * 60 # Framerate independent scaling
                
                camera.rotation.y -= mouse_dx * sensitivity # Yaw
                camera.rotation.x += mouse_dy * sensitivity # Pitch
                
                # Clamp Pitch
                camera.rotation.x = MathUtils.clamp(camera.rotation.x, -89.0, 89.0)
                self.state.input_manager.consume_input()
                return True
                
            # --- Camera Movement (WASDQE) ---
            if self.is_rotating or (is_over_viewport and pygame.key.get_pressed()[pygame.K_LALT]):
                move_speed = 5.0 * dt
                
                # Calculate camera's forward/right/up vectors
                yaw_rad = MathUtils.deg_to_rad(camera.rotation.y)
                pitch_rad = MathUtils.deg_to_rad(camera.rotation.x)
                
                # Forward/Backward
                forward_x = -math.sin(yaw_rad) * math.cos(pitch_rad)
                forward_y = math.sin(pitch_rad)
                forward_z = math.cos(yaw_rad) * math.cos(pitch_rad)
                forward_vec = Vector3(forward_x, -forward_y, forward_z).normalize() # Y-up engine convention
                
                # Right/Left (perpendicular to forward on the XZ plane)
                right_x = math.cos(yaw_rad)
                right_z = math.sin(yaw_rad)
                right_vec = Vector3(right_x, 0.0, right_z).normalize()

                # Movement keys
                if self.state.input_manager.get_key('w'): camera.position += forward_vec * move_speed
                if self.state.input_manager.get_key('s'): camera.position -= forward_vec * move_speed
                if self.state.input_manager.get_key('a'): camera.position -= right_vec * move_speed
                if self.state.input_manager.get_key('d'): camera.position += right_vec * move_speed
                
                # Up/Down (E/Q or Space/Ctrl)
                if self.state.input_manager.get_key('e'): camera.position.y += move_speed # Up
                if self.state.input_manager.get_key('q'): camera.position.y -= move_speed # Down
                
                if (self.state.input_manager.get_key('w') or self.state.input_manager.get_key('s') or 
                    self.state.input_manager.get_key('a') or self.state.input_manager.get_key('d') or 
                    self.state.input_manager.get_key('e') or self.state.input_manager.get_key('q')):
                    self.state.input_manager.consume_input()
                    return True
                    
            # --- Gizmo Dragging / Object Selection (LMB) ---
            if is_over_viewport:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    
                    selected_obj = self.state.get_object_by_uid(self.state.selected_object_uid)
                    
                    # 1. Try to start dragging the gizmo
                    if selected_obj:
                        gizmo_axis = self._check_gizmo_hit_mock(selected_obj, camera, viewport_rect, viewport_mouse_pos)
                        if gizmo_axis:
                            self.is_gizmo_dragging = True
                            self.gizmo_axis = gizmo_axis
                            self.drag_start_object_pos = selected_obj.position.copy()
                            # World-space position of the drag start point (usually intersection with a plane)
                            # Mock it as object position for simplicity
                            self.drag_start_world_pos = selected_obj.position.copy() 
                            self.state.input_manager.consume_input()
                            return True
                    
                    # 2. If not dragging gizmo, try to select an object
                    if not self.is_gizmo_dragging:
                        self._select_object_at_point_mock(viewport_mouse_pos, camera, viewport_rect)
                        self.state.input_manager.consume_input()
                        return True

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_gizmo_dragging:
                    self.is_gizmo_dragging = False
                    self.gizmo_axis = None
                    return True

                elif event.type == pygame.MOUSEMOTION and self.is_gizmo_dragging:
                    self._apply_gizmo_drag_mock(selected_obj, camera, viewport_rect, viewport_mouse_pos)
                    return True
                    
        return consumed

    # --- Selection and Gizmo Mocks ---

    def _select_object_at_point_mock(self, mouse_pos: tuple[int, int], camera: CameraObject, viewport_rect: pygame.Rect):
        """Mocks raycasting for object selection."""
        scene = self.state.current_scene
        if not scene: return
        
        # Simple proximity check in 2D screen space projection
        for obj in reversed(scene.get_all_objects()):
            if not obj.is_3d: continue

            screen_center = self._world_to_screen_mock(obj.position, camera, viewport_rect)
            
            # Simple 10-pixel proximity radius check
            if MathUtils.distance(mouse_pos, screen_center) < 10:
                self.state.selected_object_uid = obj.uid
                FileUtils.log_message(f"3D Selected: {obj.name}")
                return
                
        self.state.selected_object_uid = None # Deselect

    def _check_gizmo_hit_mock(self, obj: any, camera: CameraObject, viewport_rect: pygame.Rect, mouse_pos: tuple[int, int]) -> str | None:
        """Mocks checking if the mouse is hovering over an axis of the current gizmo (in screen space)."""
        
        screen_center = self._world_to_screen_mock(obj.position, camera, viewport_rect)
        if MathUtils.distance(mouse_pos, screen_center) < 5:
            return 'x' # Always return 'x' for a simple hit on the center point mock

        return None

    def _apply_gizmo_drag_mock(self, obj: any, camera: CameraObject, viewport_rect: pygame.Rect, current_mouse_pos: tuple[int, int]):
        """Mocks drag application: uses horizontal mouse movement for X-axis translation."""
        
        # Convert drag delta in screen space to a mock world-space delta
        mouse_dx, mouse_dy = self.state.input_manager.mouse_delta
        
        # Mock world-space movement calculation (simple)
        world_move_scale = 0.01 # Mock conversion factor
        
        if self.gizmo_axis == 'x':
            obj.position.x += mouse_dx * world_move_scale
        elif self.gizmo_axis == 'y':
            obj.position.y -= mouse_dy * world_move_scale # Y-up in 3D
        elif self.gizmo_axis == 'z':
            # Use vertical mouse movement for Z (depth) translation
            obj.position.z += mouse_dy * world_move_scale
            
        # Mock rotation change
        elif self.gizmo_axis == 'rot':
            obj.rotation.y -= mouse_dx * 0.5 # Simple horizontal mouse rotation

    # --- Rendering ---

    def draw(self, surface: pygame.Surface):
        """Renders the 3D scene, gizmos, and viewport UI."""
        
        scene = self.state.current_scene
        camera = self.camera_manager.get_active_camera()
        theme = self.state.config.editor_settings.get('theme', 'dark')
        
        # 1. Render the actual scene via Renderer3D
        if scene and camera:
            self.renderer.render(surface, scene, camera) 
        else:
            surface.fill(self.state.get_theme_color('primary'))
            font = pygame.font.Font(None, 48)
            text = font.render("3D Scene - NO RENDERER/SCENE", True, self.state.get_theme_color('text'))
            surface.blit(text, text.get_rect(center=surface.get_rect().center))
        
        # 2. Render Gizmos and Tools
        self._draw_viewport_ui(surface, camera, theme)
        
        # 3. Draw active Gizmo (over selected object)
        if self.state.selected_object_uid:
            selected_obj = self.state.get_object_by_uid(self.state.selected_object_uid)
            if selected_obj:
                self._draw_gizmo_mock(surface, selected_obj, camera)

    def _draw_viewport_ui(self, surface: pygame.Surface, camera: CameraObject, theme: str):
        """Renders the top-left tool buttons and debug info."""
        
        active_tool = self.state.ui_state.get('active_tool', 'move')
        
        # 1. Tool Buttons (positioned relative to the surface/viewport)
        self.btn_move.rect.topleft = (10, 10)
        self.btn_rotate.rect.topleft = (45, 10)
        self.btn_scale.rect.topleft = (80, 10)
        
        self.btn_move.is_toggled = (active_tool == 'move')
        self.btn_rotate.is_toggled = (active_tool == 'rotate')
        self.btn_scale.is_toggled = (active_tool == 'scale')

        self.btn_move.draw(surface, theme)
        self.btn_rotate.draw(surface, theme)
        self.btn_scale.draw(surface, theme)
        
        # 2. Debug Info (Camera position, Rotation)
        font = pygame.font.Font(None, 18)
        text_color = self.state.get_theme_color('text')
        
        if camera:
            pos_text = f"Cam: ({camera.position.x:.1f}, {camera.position.y:.1f}, {camera.position.z:.1f})"
            rot_text = f"Rot: ({camera.rotation.x:.1f}, {camera.rotation.y:.1f})"
            
            pos_surf = font.render(pos_text, True, text_color)
            rot_surf = font.render(rot_text, True, text_color)
            
            surface.blit(pos_surf, (surface.get_width() - pos_surf.get_width() - 5, 5))
            surface.blit(rot_surf, (surface.get_width() - rot_surf.get_width() - 5, 25))

    def _draw_gizmo_mock(self, surface: pygame.Surface, obj: any, camera: CameraObject):
        """Draws a simplified 3D gizmo (Move, Rotate, Scale) in 2D screen space."""
        
        # Get screen center of the object
        screen_center = self._world_to_screen_mock(obj.position, camera, surface.get_rect())
        
        tool = self.state.ui_state.get('active_tool', 'move')
        
        # Common constants
        axis_length = 40
        axis_width = 3
        
        if tool == 'move':
            # X-Axis (Red)
            x_end = (screen_center[0] + axis_length, screen_center[1])
            pygame.draw.line(surface, Color.red().to_rgb(), screen_center, x_end, axis_width)
            
            # Y-Axis (Green - Upwards)
            y_end = (screen_center[0], screen_center[1] - axis_length) 
            pygame.draw.line(surface, Color.green().to_rgb(), screen_center, y_end, axis_width)
            
            # Z-Axis (Blue - Into the screen, drawn diagonally mock)
            z_end = (screen_center[0] - axis_length // 2, screen_center[1] + axis_length // 2)
            pygame.draw.line(surface, Color.blue().to_rgb(), screen_center, z_end, axis_width)
            
        # Draw a small yellow circle for selection highlight
        pygame.draw.circle(surface, Color.yellow().to_rgb(), screen_center, 8, 2)