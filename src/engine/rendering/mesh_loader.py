# engine/rendering/mesh_loader.py
import os
import sys
import pygame
import math
import io # Use io.StringIO for procedural generation

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector3 import Vector3
except ImportError as e:
    print(f"[MeshLoader Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[ML-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[ML-ERROR] {msg}", file=sys.stderr)
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = x, y, z
    
# Mock for Pygame3D Mesh Structure (matching the mock in renderer3d.py)
class MockPygame3DMesh:
    def __init__(self, vertices, faces, normals=None, uvs=None):
        self.vertices = vertices # list of [x, y, z]
        self.faces = faces       # list of [v1_index, v2_index, v3_index]
        self.normals = normals
        self.uvs = uvs
        
    def to_dict(self):
        """Minimal serialization for saving procedural mesh data."""
        return {
            "vertices": self.vertices,
            "faces": self.faces,
            "normals": self.normals if self.normals else [],
            "uvs": self.uvs if self.uvs else []
        }
        
    @staticmethod
    def from_dict(data: dict):
        return MockPygame3DMesh(
            data.get("vertices", []), 
            data.get("faces", []), 
            data.get("normals"), 
            data.get("uvs")
        )
        
class MeshLoader:
    """
    Manages loading and procedural generation of 3D meshes.
    Supports loading from files (e.g., OBJ) and generating primitives.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.mesh_cache = {} # {asset_name: MockPygame3DMesh}

    def load_mesh(self, mesh_asset_name: str, file_path: str = None) -> MockPygame3DMesh | None:
        """
        Loads a mesh from file or cache. Assumes a simple OBJ or internal JSON format.
        """
        if mesh_asset_name in self.mesh_cache:
            return self.mesh_cache[mesh_asset_name]
            
        if not file_path:
            # Try to get path from asset loader
            asset_loader = self.state.asset_loader
            if asset_loader:
                file_path = asset_loader.get_asset_path('mesh', mesh_asset_name)
            else:
                FileUtils.log_error("AssetLoader not available. Cannot determine mesh path.")
                return None
                
        if file_path and os.path.exists(file_path):
            try:
                # Determine file type (simple: check extension)
                _, ext = os.path.splitext(file_path)
                if ext.lower() == '.obj':
                    mesh = self._load_from_obj(file_path)
                elif ext.lower() == '.json':
                    mesh = self._load_from_json(file_path)
                else:
                    FileUtils.log_warning(f"Unsupported mesh format: {ext}")
                    mesh = None
                    
                if mesh:
                    self.mesh_cache[mesh_asset_name] = mesh
                    FileUtils.log_message(f"Mesh '{mesh_asset_name}' loaded from file.")
                    return mesh
            except Exception as e:
                FileUtils.log_error(f"Error loading mesh file {file_path}: {e}")
                
        # If file loading fails, attempt procedural generation
        FileUtils.log_warning(f"Mesh file for '{mesh_asset_name}' not found or failed to load. Attempting procedural fallback.")
        return self.generate_primitive(mesh_asset_name.replace(' ', '_'), 'cube', size=1.0)


    def _load_from_obj(self, file_path: str) -> MockPygame3DMesh:
        """Loads a mesh from a simple OBJ file format (minimal implementation)."""
        vertices, faces = [], []
        
        with open(file_path, 'r') as f:
            for line in f:
                parts = line.split()
                if not parts: continue
                
                if parts[0] == 'v': # Vertex
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif parts[0] == 'f': # Face
                    # OBJ indices are 1-based, we convert to 0-based for internal structure
                    face = [int(p.split('/')[0]) - 1 for p in parts[1:]]
                    
                    # Simple triangulation for faces with > 3 vertices (fan triangulation)
                    if len(face) == 3:
                        faces.append(face)
                    elif len(face) > 3:
                        for i in range(1, len(face) - 1):
                            faces.append([face[0], face[i], face[i+1]])

        if not vertices or not faces:
            raise ValueError(f"OBJ file {file_path} is empty or invalid.")
            
        return MockPygame3DMesh(vertices, faces)
        
    def _load_from_json(self, file_path: str) -> MockPygame3DMesh:
        """Loads a mesh from the internal JSON format."""
        data = FileUtils.read_json(file_path)
        if not data: raise ValueError("JSON mesh file is empty or invalid.")
        return MockPygame3DMesh.from_dict(data)

    def save_mesh_to_json(self, mesh: MockPygame3DMesh, file_path: str):
        """Saves a mesh (typically a procedural or CSG result) to the internal JSON format."""
        try:
            data = mesh.to_dict()
            FileUtils.write_json(file_path, data)
            FileUtils.log_message(f"Mesh saved to JSON: {file_path}")
            return True
        except Exception as e:
            FileUtils.log_error(f"Failed to save mesh to JSON {file_path}: {e}")
            return False

    def generate_primitive(self, mesh_name: str, type: str, **kwargs) -> MockPygame3DMesh:
        """
        Procedurally generates a 3D mesh primitive (cube, sphere, plane).
        Caches the result using the mesh_name.
        """
        if type == 'cube':
            mesh = self._generate_cube(**kwargs)
        elif type == 'sphere':
            mesh = self._generate_sphere(**kwargs)
        elif type == 'plane':
            mesh = self._generate_plane(**kwargs)
        else:
            FileUtils.log_error(f"Unknown mesh primitive type: {type}")
            return None
            
        self.mesh_cache[mesh_name] = mesh
        FileUtils.log_message(f"Generated primitive mesh: {mesh_name} ({type})")
        return mesh

    def _generate_cube(self, size=1.0) -> MockPygame3DMesh:
        """Generates a unit cube mesh (1x1x1) centered at the origin."""
        s = size / 2.0
        
        # 8 Vertices
        vertices = [
            [-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s], # Back face (0, 1, 2, 3)
            [-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s]  # Front face (4, 5, 6, 7)
        ]

        # 12 Faces (6 quads, triangulated)
        faces = [
            # Front (4, 5, 6, 7) -> 4, 5, 6 | 4, 6, 7
            [4, 5, 6], [4, 6, 7],
            # Back (0, 3, 2, 1) -> 0, 3, 2 | 0, 2, 1
            [0, 3, 2], [0, 2, 1],
            # Top (3, 7, 6, 2) -> 3, 7, 6 | 3, 6, 2
            [3, 7, 6], [3, 6, 2],
            # Bottom (0, 1, 5, 4) -> 0, 1, 5 | 0, 5, 4
            [0, 1, 5], [0, 5, 4],
            # Right (1, 2, 6, 5) -> 1, 2, 6 | 1, 6, 5
            [1, 2, 6], [1, 6, 5],
            # Left (4, 7, 3, 0) -> 4, 7, 3 | 4, 3, 0
            [4, 7, 3], [4, 3, 0]
        ]
        
        return MockPygame3DMesh(vertices, faces)

    def _generate_sphere(self, radius=1.0, resolution=16) -> MockPygame3DMesh:
        """Generates a UV sphere mesh."""
        vertices = []
        faces = []
        
        # Create vertices
        for i in range(resolution + 1):
            phi = math.pi * i / resolution # Latitude angle (0 to pi)
            sin_phi = math.sin(phi)
            cos_phi = math.cos(phi)
            
            for j in range(resolution + 1):
                theta = 2 * math.pi * j / resolution # Longitude angle (0 to 2pi)
                sin_theta = math.sin(theta)
                cos_theta = math.cos(theta)
                
                x = radius * sin_phi * cos_theta
                y = radius * cos_phi
                z = radius * sin_phi * sin_theta
                vertices.append([x, y, z])
                
        # Create faces (Quads, then triangulated)
        for i in range(resolution):
            for j in range(resolution):
                v1 = i * (resolution + 1) + j
                v2 = v1 + 1
                v3 = (i + 1) * (resolution + 1) + j
                v4 = v3 + 1
                
                # First triangle
                faces.append([v1, v3, v4])
                # Second triangle
                faces.append([v1, v4, v2])
                
        return MockPygame3DMesh(vertices, faces)
        
    def _generate_plane(self, size=10.0, segments=1) -> MockPygame3DMesh:
        """Generates a simple, flat plane mesh in the XY plane (Z=0)."""
        vertices = []
        faces = []
        s = size / 2.0
        step = size / segments
        
        # Vertices
        for i in range(segments + 1):
            for j in range(segments + 1):
                x = -s + j * step
                y = -s + i * step
                # Note: Pygame3D/OpenGL standard often uses Y-up, Z-forward. 
                # We'll use X/Z for ground plane (typical 3D setup)
                vertices.append([x, 0.0, y]) 
                
        # Faces
        for i in range(segments):
            for j in range(segments):
                v1 = i * (segments + 1) + j
                v2 = v1 + 1
                v3 = (i + 1) * (segments + 1) + j
                v4 = v3 + 1
                
                # Triangles for the quad (v1-v2-v4-v3)
                faces.append([v1, v4, v3]) # Triangle 1
                faces.append([v1, v2, v4]) # Triangle 2
                
        return MockPygame3DMesh(vertices, faces)