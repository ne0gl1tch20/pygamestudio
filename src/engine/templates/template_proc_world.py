# engine/templates/template_proc_world.py
import uuid
import sys
import os
import math
import random
from typing import Dict, Any, List

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.vector2 import Vector2
    from engine.utils.vector3 import Vector3
    from engine.utils.color import Color
    from engine.utils.file_utils import FileUtils
    from engine.utils.math_utils import MathUtils
    from engine.rendering.mesh_loader import MockPygame3DMesh, MeshLoader
except ImportError as e:
    print(f"[Template Import Error] {e}. Using Internal Mocks.")
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = x, y
        def to_tuple(self): return (self.x, self.y)
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = x, y, z
    class Color:
        @staticmethod
        def green(): return (0, 255, 0)
        @staticmethod
        def blue(): return (0, 0, 255)
        def to_rgb(self): return (self.r, self.g, self.b)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[TPW-INFO] {msg}")
        @staticmethod
        def write_json(path, data): pass
        @staticmethod
        def create_dirs_if_not_exist(path): os.makedirs(path, exist_ok=True)
    class MathUtils:
        @staticmethod
        def perlin_noise_3d(x, y, z): return random.uniform(-1.0, 1.0) # Mock noise
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))
        @staticmethod
        def lerp(a, b, t): return a + (b - a) * t
    class MockPygame3DMesh:
        def __init__(self, vertices=None, faces=None): self.vertices = vertices; self.faces = faces
        def to_dict(self): return {"vertices": self.vertices, "faces": self.faces}
    class MeshLoader:
        def __init__(self, state): pass
        def save_mesh_to_json(self, mesh, path): FileUtils.write_json(path, mesh.to_dict())
        def _generate_plane_from_heightmap(self, name, heights, size, segments): return MockPygame3DMesh()

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


class ProceduralWorldGenerator:
    """
    Core logic for generating a procedural world (2D Tilemap or 3D Heightmap).
    """
    
    def __init__(self, state):
        self.state = state
        # NOTE: State is needed for MeshLoader/AssetLoader context
        
    def generate_2d_tilemap(self, width: int, height: int, scale: float = 0.1) -> Dict[str, Any]:
        """Generates a 2D tilemap using Perlin noise for terrain type."""
        
        tile_size = 32
        tilemap = {
            "width": width, 
            "height": height, 
            "tile_size": tile_size, 
            "tiles": []
        }
        
        for y in range(height):
            row = []
            for x in range(width):
                # Sample 2D Perlin noise (using Z=0 for the 3D function mock)
                noise_val = MathUtils.perlin_noise_3d(x * scale, y * scale, 0)
                
                # Normalize noise from [-1, 1] to [0, 1]
                normalized_noise = (noise_val + 1) / 2.0
                
                # Determine tile type based on noise level
                tile_type = ""
                if normalized_noise < 0.3:
                    tile_type = "water"
                elif normalized_noise < 0.5:
                    tile_type = "sand"
                elif normalized_noise < 0.8:
                    tile_type = "grass"
                else:
                    tile_type = "mountain"
                    
                row.append({"type": tile_type, "asset": f"{tile_type}_tile.png"})
            tilemap["tiles"].append(row)
            
        FileUtils.log_message(f"Generated 2D Tilemap: {width}x{height}")
        return tilemap

    def generate_3d_heightmap_mesh(self, mesh_name: str, width: int, height: int, scale: float = 0.1, height_multiplier: float = 5.0, mesh_loader: MeshLoader = None) -> MockPygame3DMesh:
        """Generates a 3D mesh (plane) with vertex heights based on Perlin noise."""
        
        # 1. Generate Height Data
        heights = []
        for y in range(height + 1):
            row = []
            for x in range(width + 1):
                # Sample 2D Perlin noise
                noise_val = MathUtils.perlin_noise_3d(x * scale, y * scale, 0)
                
                # Smooth/Normalize and apply multiplier
                normalized_noise = (noise_val + 1) / 2.0
                h = normalized_noise * height_multiplier
                row.append(h)
            heights.append(row)
            
        # 2. Build Mesh (Vertices and Faces)
        # We need a MeshLoader instance to perform the mesh construction
        if not mesh_loader:
             # This will use the MockPygame3DMesh if full MeshLoader is unavailable
             return MockPygame3DMesh() 
             
        # NOTE: Full implementation requires MeshLoader to have a method 
        # to generate a mesh from a grid of heights. We mock the call.
        
        # Mocked generation:
        vertices = []
        faces = []
        
        tile_size = 1.0 # Units per segment
        
        for i in range(height + 1):
            for j in range(width + 1):
                x = j * tile_size
                z = i * tile_size # Z-axis is depth/forward
                y = heights[i][j]
                vertices.append([x - width * tile_size / 2, y, z - height * tile_size / 2])
        
        for i in range(height):
            for j in range(width):
                v1 = i * (width + 1) + j
                v2 = v1 + 1
                v3 = (i + 1) * (width + 1) + j
                v4 = v3 + 1
                
                # Triangles (standard quad tessellation)
                faces.append([v1, v4, v3]) 
                faces.append([v1, v2, v4])
                
        
        mesh = MockPygame3DMesh(vertices, faces)
        
        FileUtils.log_message(f"Generated 3D Heightmap Mesh: {mesh_name} ({width}x{height})")
        return mesh


def get_proc_world_template_data(is_3d: bool, width: int = 50, height: int = 50) -> Dict[str, Any]:
    """
    Generates the scene data based on the procedural generator's output.
    """
    
    # Mock EngineState for generator usage
    class MockEngineState: 
        def __init__(self): self.asset_loader = None; self.renderer_3d = None
    mock_state = MockEngineState()
    
    generator = ProceduralWorldGenerator(mock_state)
    
    if is_3d:
        # 1. Generate 3D Heightmap Mesh
        mesh_loader = MeshLoader(mock_state)
        heightmap_mesh = generator.generate_3d_heightmap_mesh("procedural_terrain", width, height, scale=0.05, height_multiplier=10.0, mesh_loader=mesh_loader)
        
        scene_data = {
            "name": "Procedural_3D_Scene",
            "is_3d": True,
            "scene_properties": {
                "gravity": [0, -9.8, 0],
                "ambient_light": [80, 80, 80]
            },
            "objects": [
                {
                    "uid": "TERRAIN_MESH",
                    "name": "ProceduralTerrain",
                    "type": "mesh",
                    "position": [0, 0, 0],
                    "rotation": [0, 0, 0],
                    "scale": [1.0, 1.0, 1.0],
                    "components": [
                        {"type": "MeshRenderer", "mesh_asset": "procedural_terrain", "material_asset": "terrain_mat"},
                        {"type": "BoxCollider3D", "half_extents": [width / 2, 0.01, height / 2]} # Simplified box collider
                    ]
                },
                # Default Camera
                {
                    "uid": "CAM_001", "name": "Main Camera", "type": "camera", "position": [0, 10, -20], "rotation": [15, 0, 0],
                    "components": [{"type": "CameraComponent", "is_active": True, "projection": "perspective", "fov": 60.0}]
                }
            ]
        }
        
        # Store mesh data for saving
        scene_data['assets_to_save'] = {"meshes/procedural_terrain.json": heightmap_mesh}
        
    else:
        # 1. Generate 2D Tilemap Data
        tilemap_data = generator.generate_2d_tilemap(width, height)
        
        scene_data = {
            "name": "Procedural_2D_Scene",
            "is_3d": False,
            "scene_properties": {
                "gravity": [0, 0], 
                "background_color": Color(50, 50, 100).to_rgb()
            },
            "objects": [
                {
                    "uid": "TILEMAP_01",
                    "name": "ProceduralTilemap",
                    "type": "tilemap",
                    "position": [0, 0],
                    "scale": [1.0, 1.0],
                    "components": [
                        {"type": "TilemapRenderer", "tilemap_data": tilemap_data},
                        # Mock collision component for tilemap
                        {"type": "TilemapCollider"} 
                    ]
                },
                # Default Camera
                {
                    "uid": "CAM_001", "name": "Main Camera", "type": "camera", "position": [width * tilemap_data['tile_size']/4, height * tilemap_data['tile_size']/4], "rotation": 0,
                    "components": [{"type": "CameraComponent", "is_active": True, "projection": "orthographic", "zoom": 1.0}]
                }
            ]
        }
        
    return scene_data


def create_project(project_path: str, game_manager, is_3d: bool = False):
    """
    The function called by the Editor/Template Manager to generate the project files.
    """
    
    template_data = get_proc_world_template_data(is_3d)
    scene_data = {k: v for k, v in template_data.items() if k != 'assets_to_save'}
    assets_to_save = template_data.get('assets_to_save', {})
    
    # 1. Create project folder structure
    FileUtils.create_dirs_if_not_exist(project_path)
    assets_dir = os.path.join(project_path, 'assets')
    FileUtils.create_dirs_if_not_exist(assets_dir)
    FileUtils.create_dirs_if_not_exist(os.path.join(assets_dir, 'meshes'))
    FileUtils.create_dirs_if_not_exist(os.path.join(assets_dir, 'materials'))

    # 2. Create main.py (Project entry point)
    main_py_content = f"""
# {os.path.basename(project_path)}/main.py
# Automatically generated entry script from Procedural World Template.

def start_game(game_manager):
    print("--- Procedural World Game Start ({'3D' if {is_3d} else '2D'}) ---")
    game_manager.state.config.set_setting('project_settings', 'is_3d_mode', {is_3d})
    return {scene_data} 

def update_game(game_manager, dt):
    pass
"""
    FileUtils.write_text(os.path.join(project_path, 'main.py'), main_py_content)
    
    # 3. Create project.json
    project_json_content = {
        "name": os.path.basename(project_path),
        "main_scene": "main_scene.json",
        "is_3d": is_3d,
        "assets_path": "assets/",
        "scripts_path": "scripts/",
        "startup_script": "main.py"
    }
    FileUtils.write_json(os.path.join(project_path, 'project.json'), project_json_content)

    # 4. Save initial scene data to main_scene.json
    FileUtils.write_json(os.path.join(project_path, project_json_content['main_scene']), scene_data)

    # 5. Save generated assets
    for rel_path, asset_data in assets_to_save.items():
        full_path = os.path.join(project_path, 'assets', rel_path)
        FileUtils.create_dirs_if_not_exist(os.path.dirname(full_path))
        
        # Assuming asset_data has a to_dict method (like MockPygame3DMesh)
        if hasattr(asset_data, 'to_dict'):
            FileUtils.write_json(full_path, asset_data.to_dict())
            
    # 6. Mock Material (Terrain Mat)
    terrain_mat = {"name": "terrain_mat", "shader_name": "default_lit" if is_3d else "default_unlit", "color": [100, 100, 100], "roughness": 0.8}
    FileUtils.write_json(os.path.join(assets_dir, 'materials', 'terrain_mat.json'), terrain_mat)


    FileUtils.log_message(f"Procedural World Template ({'3D' if is_3d else '2D'}) created in {project_path}")
    return True