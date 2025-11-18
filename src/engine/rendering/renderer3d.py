# engine/rendering/renderer3d.py
import pygame
import sys
import math

# Try to import pygame3d or provide a full mock if not available
try:
    # NOTE: pygame3d is not a standard Pygame dependency and might require installation.
    # We mock its core functionality here to prevent runtime errors.
    # import pygame3d as p3d 
    
    # Simple Mock of Pygame3D/3D Structures
    class MockPygame3D:
        class Camera:
            def __init__(self, pos, rot, fov=60): self.pos, self.rot, self.fov = pos, rot, fov
        class Mesh:
            def __init__(self, vertices, faces): self.vertices, self.faces = vertices, faces
        class Renderer:
            def __init__(self, surface): self.surface = surface
            def render_mesh(self, mesh, pos, rot, scale, material):
                # Simple placeholder for drawing a wireframe triangle
                color = material.color.to_rgb() if material and hasattr(material, 'color') else (255, 255, 255)
                # Mock 3D to 2D projection (extremely simple Z-ignore for mock)
                points2d = []
                for v in mesh.vertices:
                    # Apply scale (mock)
                    scaled_v = [v[i] * scale.x for i in range(3)]
                    # Simple center-based projection
                    screen_x = int(self.surface.get_width() / 2 + pos.x + scaled_v[0])
                    screen_y = int(self.surface.get_height() / 2 + pos.y + scaled_v[1])
                    points2d.append((screen_x, screen_y))
                    
                if len(points2d) >= 3:
                    pygame.draw.polygon(self.surface, color, points2d, 1) # Wireframe

    p3d = MockPygame3D()
    HAS_PYGAME3D = True
    
    # Import core dependencies
    from engine.core.engine_state import EngineState
    from engine.core.scene_manager import SceneObject, Scene
    from engine.managers.camera_manager import CameraObject
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector3 import Vector3
    from engine.utils.color import Color
    from engine.rendering.material import Material 

except ImportError as e:
    print(f"[Renderer3D Import Error] {e}. Falling back to 2D view mock.")
    HAS_PYGAME3D = False
    
    # Minimal mocks for classes needed by the method signatures
    class EngineState: pass
    class SceneObject:
        def __init__(self): self.is_3d = True; self.position = Vector3(0, 0, 0)
        def get_component(self, type): return None
    class Scene:
        def __init__(self): self.scene_properties = {"background_color": (0, 0, 50)}; self.is_3d = True
        def get_all_objects(self): return []
    class CameraObject:
        def __init__(self): self.position = Vector3(0, 0, 0); self.rotation = Vector3(0, 0, 0)
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = x, y, z
    class Color:
        @staticmethod
        def blue(): return (0, 0, 255)
    class Material: 
        def __init__(self): self.color = Color(255, 255, 255)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[R3D-INFO] {msg}")
        @staticmethod
        def log_warning(msg): print(f"[R3D-WARN] {msg}")


class Renderer3D:
    """
    Handles all 3D rendering operations. Mocks Pygame3D if not available.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.state.renderer_3d = self
        self.has_hardware = HAS_PYGAME3D
        self.p3d_renderer = None # The actual Pygame3D Renderer instance
        self.mesh_cache = {} # Cache for loaded p3d.Mesh objects

        if self.has_hardware:
            FileUtils.log_message("Renderer3D initialized with Pygame3D mock/support.")
        else:
            FileUtils.log_warning("Renderer3D initialized in FALLBACK MODE (Pygame3D not found).")

    def init_display(self, surface: pygame.Surface):
        """Initializes the underlying 3D context, usually tied to the surface."""
        if self.has_hardware:
            # self.p3d_renderer = p3d.Renderer(surface)
            self.p3d_renderer = p3d.MockPygame3D.Renderer(surface)
            
    def load_mesh(self, asset_name: str, asset_path: str = None):
        """Mocks loading a 3D mesh (e.g., OBJ file)."""
        if asset_name in self.mesh_cache:
            return self.mesh_cache[asset_name]
            
        # Mock mesh structure (a simple triangle)
        vertices = [[-1, -1, 0], [1, -1, 0], [0, 1, 0]]
        faces = [[0, 1, 2]]
        
        # Create a p3d.Mesh mock object
        # loaded_mesh = p3d.Mesh(vertices, faces)
        loaded_mesh = p3d.MockPygame3D.Mesh(vertices, faces)
        self.mesh_cache[asset_name] = loaded_mesh
        return loaded_mesh

    def render(self, surface: pygame.Surface, scene: Scene, camera: CameraObject):
        """
        Main render loop: Clears the screen, sets camera, and draws all 3D scene objects.
        """
        if not scene.is_3d: 
            FileUtils.log_error("Attempted to run 3D renderer on a 2D scene.")
            return

        # 1. Clear Screen
        bg_color = scene.scene_properties.get("background_color", Color(0, 0, 50).to_rgb())
        surface.fill(bg_color)
        
        if not self.has_hardware:
            self._render_fallback(surface)
            return
            
        # Ensure the renderer is initialized
        if not self.p3d_renderer:
            self.init_display(surface)

        # 2. Setup Camera
        # p3d_camera = p3d.Camera(camera.position, camera.rotation, camera.fov)
        
        # 3. Render Objects (Basic implementation drawing mock meshes)
        for obj in scene.get_all_objects():
            if not obj.is_3d: continue
            
            mesh_comp = obj.get_component("MeshRenderer")
            if not mesh_comp:
                self._render_placeholder(surface, obj, camera)
                continue
            
            # Get Mesh (from cache or load mock)
            mesh = self.load_mesh(mesh_comp.get("mesh_asset", "default_cube_mock"))
            
            # Get Material (mock or from asset loader)
            material_asset_name = mesh_comp.get("material_asset", "default_material")
            # In a full setup, this would load a Material class instance
            # material = self.state.asset_loader.get_asset('material', material_asset_name) 
            # Mock material
            material = Material() 
            material.color = Color(200, 200, 200) # Simple light gray color
            
            # Render call (uses the p3d_renderer mock)
            self.p3d_renderer.render_mesh(
                mesh, 
                obj.position, 
                obj.rotation, 
                obj.scale, 
                material
            )

        # 4. Render Editor Overlays (Grid, Gizmos)
        if self.state.is_editor_mode:
            self._render_editor_overlays(surface, camera)
            
    def _render_placeholder(self, surface, obj, camera):
        """Draws a simple red box for a 3D object missing a mesh/renderer."""
        # Simple center point projection mock
        center_x = surface.get_width() // 2 + int(obj.position.x - camera.position.x)
        center_y = surface.get_height() // 2 + int(obj.position.y - camera.position.y)
        
        size = 20
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (center_x, center_y)
        pygame.draw.rect(surface, Color.red().to_rgb(), rect, 1)
        
    def _render_fallback(self, surface: pygame.Surface):
        """Rendered when Pygame3D is unavailable."""
        rect = surface.get_rect()
        font = pygame.font.Font(None, 48)
        text = font.render("3D Fallback Mode (No Pygame3D)", True, (255, 100, 100))
        surface.blit(text, text.get_rect(center=rect.center))
        
    def _render_editor_overlays(self, surface: pygame.Surface, camera: CameraObject):
        """Renders editor-specific overlays in 3D space (mocked as 2D lines)."""
        # 1. World Origin Axes (Mock)
        center_x = surface.get_width() // 2 - int(camera.position.x)
        center_y = surface.get_height() // 2 - int(camera.position.y)
        
        # Red X-axis
        pygame.draw.line(surface, (255, 0, 0), (center_x, center_y), (center_x + 50, center_y), 2) 
        # Green Y-axis
        pygame.draw.line(surface, (0, 255, 0), (center_x, center_y), (center_x, center_y - 50), 2) 
        # Blue Z-axis (Mock: Render slightly offset Y to distinguish)
        pygame.draw.line(surface, (0, 0, 255), (center_x, center_y), (center_x + 10, center_y - 10), 2)