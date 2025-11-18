# engine/rendering/renderer2d.py
import pygame
import sys
import math

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.core.scene_manager import SceneObject, Scene
    from engine.managers.camera_manager import CameraObject
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector2 import Vector2
    from engine.utils.color import Color
    from engine.rendering.material import Material # For mock rendering
except ImportError as e:
    print(f"[Renderer2D Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[R2D-INFO] {msg}")
    class Vector2:
        def __init__(self, x, y): self.x, self.y = x, y
        def to_tuple(self): return (self.x, self.y)
    class Color:
        @staticmethod
        def red(): return (255, 0, 0)
        @staticmethod
        def blue(): return (0, 0, 255)
    class SceneObject:
        def __init__(self, pos=(0, 0), rot=0, scale=(1, 1), uid=""): 
            self.position = Vector2(*pos)
            self.rotation = rot
            self.scale = Vector2(*scale)
            self.uid = uid
            self.is_3d = False
        def get_component(self, type): return None
    class Scene:
        def __init__(self): self._objects = []; self.scene_properties = {"background_color": Color.blue()}
        def get_all_objects(self): return self._objects
    class CameraObject:
        def __init__(self): self.position = Vector2(0, 0); self.zoom = 1.0
    class Material: # Mock Material
        def __init__(self): self.color = Color.red()


class Renderer2D:
    """
    Handles all 2D rendering operations using Pygame.
    Renders the scene from the perspective of the active Camera.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.state.renderer_2d = self
        self.font = pygame.font.Font(None, 24)
        FileUtils.log_message("Renderer2D initialized.")
        
        # Performance/Optimizations
        self.render_cache = {} # Cache for scaled/rotated sprites

    def render(self, surface: pygame.Surface, scene: Scene, camera: CameraObject):
        """
        Main render loop: Clears the screen and draws all scene objects.
        """
        
        # 1. Clear Screen
        bg_color = scene.scene_properties.get("background_color", Color(30, 30, 30).to_rgb())
        surface.fill(bg_color)
        
        # 2. Render all objects in the scene
        for obj in scene.get_all_objects():
            if obj.is_3d: continue # Skip 3D objects in 2D render
            
            # Simple sorting by Y-position for Z-depth (painter's algorithm mock)
            # A full engine would use an explicit Z-index or layer system.
            
            self._render_scene_object(surface, obj, camera)
            
        # 3. Render Editor Overlays (e.g., selection box, gizmos)
        if self.state.is_editor_mode:
            self._render_editor_overlays(surface, scene, camera)


    def _world_to_screen(self, world_pos: Vector2, camera: CameraObject, surface_rect: pygame.Rect) -> tuple[int, int]:
        """Converts world coordinates to screen pixel coordinates, accounting for camera and zoom."""
        
        # Camera offset
        relative_pos = world_pos - camera.position
        
        # Apply zoom
        zoom = camera.zoom
        zoomed_pos_x = relative_pos.x * zoom
        zoomed_pos_y = relative_pos.y * zoom
        
        # Center on screen
        screen_x = int(zoomed_pos_x + surface_rect.width / 2)
        screen_y = int(zoomed_pos_y + surface_rect.height / 2)
        
        return (screen_x, screen_y)
        
    def _render_scene_object(self, surface: pygame.Surface, obj: SceneObject, camera: CameraObject):
        """Renders a single SceneObject."""
        
        # --- Transform to Screen Space ---
        screen_pos = self._world_to_screen(obj.position, camera, surface.get_rect())
        
        # --- Get Visual Asset (Sprite/Surface) ---
        render_comp = obj.get_component("SpriteRenderer")
        
        # Fallback to simple box if no SpriteRenderer component or asset
        if not render_comp or not render_comp.get("asset"):
            # Render a placeholder rect
            size = 32 * camera.zoom
            rect = pygame.Rect(0, 0, size * obj.scale.x, size * obj.scale.y)
            rect.center = screen_pos
            pygame.draw.rect(surface, Color.red().to_rgb(), rect, 1) # Outline
            text = self.font.render(obj.name, True, Color.white().to_rgb())
            surface.blit(text, text.get_rect(midtop=rect.midbottom))
            return
            
        # 1. Load Sprite
        asset_name = render_comp["asset"]
        sprite = self.state.asset_loader.get_asset('image', asset_name)
        if not isinstance(sprite, pygame.Surface):
            sprite = self.state.asset_loader._create_placeholder('image', asset_name) # Use fallback
            
        # 2. Apply Scale, Rotation, and Zoom (Caching optimization is crucial here)
        
        # Calculate combined scaling factor
        scale_x = obj.scale.x * camera.zoom
        scale_y = obj.scale.y * camera.zoom
        
        # Resize/Scale
        original_size = sprite.get_size()
        new_size = (int(original_size[0] * scale_x), int(original_size[1] * scale_y))
        
        # Use cache key: (asset_name, scale_x, scale_y, rotation)
        cache_key = (asset_name, new_size, obj.rotation) 
        
        if cache_key not in self.render_cache:
            # Scale
            if new_size[0] > 0 and new_size[1] > 0:
                scaled_sprite = pygame.transform.scale(sprite, new_size)
            else:
                scaled_sprite = sprite # Or a 1x1 surface if too small

            # Rotate
            rotated_sprite = pygame.transform.rotate(scaled_sprite, -obj.rotation) # Pygame uses counter-clockwise
            self.render_cache[cache_key] = rotated_sprite
        else:
            rotated_sprite = self.render_cache[cache_key]
            
        # 3. Blit to Screen
        sprite_rect = rotated_sprite.get_rect(center=screen_pos)
        surface.blit(rotated_sprite, sprite_rect)
        
        # 4. Debug/Collision Shape Render (if in editor)
        if self.state.is_editor_mode:
            self._render_collision_shape(surface, obj, camera, screen_pos, new_size, obj.rotation)

    def _render_collision_shape(self, surface, obj, camera, screen_pos, sprite_size, rotation):
        """Helper to draw collision shapes in the editor."""
        
        # Get Rigidbody Component
        rb_comp = obj.get_component("Rigidbody2D")
        if not rb_comp: return
        
        # Get Collider Component (BoxCollider2D assumed for simplicity)
        col_comp = obj.get_component("BoxCollider2D") 
        if not col_comp: return
        
        # Collision data (local to object)
        width = col_comp.get("width", 1.0)
        height = col_comp.get("height", 1.0)
        offset = col_comp.get("offset", [0, 0])
        
        # Apply camera zoom and scale
        zoom = camera.zoom
        
        # Half-extents in screen space
        half_w = width * obj.scale.x * zoom / 2.0
        half_h = height * obj.scale.y * zoom / 2.0
        
        # Draw the unrotated collision box (Screen-space rect)
        # Note: Proper rotated rect rendering is complex (polygon drawing is needed)
        
        # Draw a simple AABB bounding box for now
        aabb_rect = pygame.Rect(0, 0, half_w * 2, half_h * 2)
        aabb_rect.center = screen_pos
        pygame.draw.rect(surface, (0, 255, 0), aabb_rect, 2) # Green outline
        
        # NOTE: To draw a rotated box, you'd need the four corner points, 
        # rotate them around screen_pos, and use pygame.draw.polygon.
        
    def _render_editor_overlays(self, surface: pygame.Surface, scene: Scene, camera: CameraObject):
        """Renders editor-specific overlays like grid, selection box, and gizmos."""
        
        # 1. Render Grid (Mock for simplicity)
        grid_step = 64 * camera.zoom
        screen_rect = surface.get_rect()
        grid_color = (70, 70, 70)
        
        # Draw vertical lines
        start_x = int((screen_rect.centerx - camera.position.x * camera.zoom) % grid_step)
        for x in range(start_x, screen_rect.width, int(grid_step)):
            pygame.draw.line(surface, grid_color, (x, 0), (x, screen_rect.height))
            
        # Draw horizontal lines
        start_y = int((screen_rect.centery - camera.position.y * camera.zoom) % grid_step)
        for y in range(start_y, screen_rect.height, int(grid_step)):
            pygame.draw.line(surface, grid_color, (0, y), (screen_rect.width, y))


        # 2. Render Selection Box and Gizmo
        if self.state.selected_object_uid:
            selected_obj = scene.get_object(self.state.selected_object_uid)
            if selected_obj:
                screen_pos = self._world_to_screen(selected_obj.position, camera, surface.get_rect())
                
                # Selection box (simple fixed size for now)
                select_rect = pygame.Rect(0, 0, 40, 40)
                select_rect.center = screen_pos
                pygame.draw.rect(surface, Color(255, 255, 0).to_rgb(), select_rect, 3) # Yellow

                # Gizmo (small cross)
                pygame.draw.line(surface, (255, 0, 0), (screen_pos[0] - 10, screen_pos[1]), (screen_pos[0] + 10, screen_pos[1]), 2) # Red X-axis
                pygame.draw.line(surface, (0, 0, 255), (screen_pos[0], screen_pos[1] - 10), (screen_pos[0], screen_pos[1] + 10), 2) # Blue Y-axis