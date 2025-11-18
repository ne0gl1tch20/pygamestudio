# engine/rendering/csg_modeler.py
import sys
import copy
import math

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.utils.vector3 import Vector3
    from engine.rendering.mesh_loader import MockPygame3DMesh, MeshLoader
    from engine.utils.math_utils import MathUtils
except ImportError as e:
    print(f"[CSGModeler Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[CSG-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[CSG-ERROR] {msg}", file=sys.stderr)
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = x, y, z
    class MathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))
    class MockPygame3DMesh:
        def __init__(self, vertices=None, faces=None, **kwargs): self.vertices, self.faces = vertices if vertices else [], faces if faces else []
        def to_dict(self): return {"vertices": self.vertices, "faces": self.faces}
    class MeshLoader:
        def __init__(self, state): pass
        def generate_primitive(self, mesh_name, type, **kwargs):
            # Simple cube mock for primitives
            if type == 'cube':
                s = kwargs.get('size', 1.0) / 2.0
                vertices = [[-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s], [-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s]]
                faces = [[4, 5, 6], [4, 6, 7], [0, 3, 2], [0, 2, 1], [3, 7, 6], [3, 6, 2], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [4, 7, 3], [4, 3, 0]]
                return MockPygame3DMesh(vertices, faces)
            return MockPygame3DMesh()

# --- CSG Node Data Structure (For Editor) ---
class CSGNode:
    """Represents a single operation or primitive in the CSG tree."""
    def __init__(self, type: str, name: str, op_type: str = 'primitive', children: list = None, params: dict = None, transform: dict = None):
        self.type = type          # e.g., 'cube', 'sphere', 'union', 'subtract'
        self.name = name
        self.op_type = op_type    # 'primitive' or 'boolean'
        self.children = children if children is not None else []
        self.params = params if params is not None else {}
        self.transform = transform if transform is not None else {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}
        self.uid = str(hash(self)) # Simple unique ID based on hash

    def to_dict(self):
        return {
            "uid": self.uid,
            "type": self.type,
            "name": self.name,
            "op_type": self.op_type,
            "children": [c.to_dict() for c in self.children],
            "params": self.params,
            "transform": self.transform
        }
    
# --- CSG Modeler Core ---

class CSGModeler:
    """
    Implements the logic for Constructive Solid Geometry (CSG) modeling.
    NOTE: Full, robust CSG (mesh boolean operations) is extremely complex.
    This implementation uses a simplified, approximate, or mock geometry approach.
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        # Assume MeshLoader is available
        self.mesh_loader = MeshLoader(state)
        self.active_tree_root: CSGNode = self._create_default_tree()

    def _create_default_tree(self) -> CSGNode:
        """Creates a default CSG tree (e.g., a simple cutout)."""
        
        # Cube (Base shape)
        cube = CSGNode('cube', 'BaseCube', 'primitive', params={'size': 2.0})
        
        # Sphere (Tool shape for subtraction)
        sphere = CSGNode('sphere', 'CutoutSphere', 'primitive', params={'radius': 0.8})
        
        # Subtract operation (Root)
        subtract_op = CSGNode('subtract', 'Cutout_Result', 'boolean', children=[cube, sphere])
        
        FileUtils.log_message("CSG Modeler initialized with a default tree (Cube - Sphere).")
        return subtract_op
        
    def rebuild_mesh(self, csg_node: CSGNode = None) -> MockPygame3DMesh | None:
        """
        Traverses the CSG tree and performs boolean operations to generate the final mesh.
        """
        node = csg_node if csg_node else self.active_tree_root
        
        if node.op_type == 'primitive':
            # 1. Generate the primitive mesh
            mesh = self._generate_primitive_mesh(node.type, **node.params)
            
            # 2. Apply transform to vertices
            mesh = self._apply_transform_to_mesh(mesh, node.transform)
            
            return mesh
            
        elif node.op_type == 'boolean':
            if len(node.children) < 2:
                FileUtils.log_error(f"Boolean operation '{node.type}' requires at least two children.")
                return None
                
            # Recursively build meshes for children
            mesh_a = self.rebuild_mesh(node.children[0])
            mesh_b = self.rebuild_mesh(node.children[1]) # Only handles two operands for simplicity
            
            if not mesh_a or not mesh_b:
                return None
            
            # Perform the boolean operation (MOCK/APPROXIMATION)
            if node.type == 'union':
                return self._approximate_union(mesh_a, mesh_b)
            elif node.type == 'subtract':
                return self._approximate_subtract(mesh_a, mesh_b)
            elif node.type == 'intersect':
                return self._approximate_intersect(mesh_a, mesh_b)
            else:
                FileUtils.log_error(f"Unknown boolean operation type: {node.type}")
                return None

        return None

    def _generate_primitive_mesh(self, type: str, **params) -> MockPygame3DMesh:
        """Wrapper for MeshLoader primitives."""
        # Use node type as mesh name for cache
        mesh_name = f"csg_primitive_{type}_{hash(frozenset(params.items()))}"
        return self.mesh_loader.generate_primitive(mesh_name, type, **params)

    def _apply_transform_to_mesh(self, mesh: MockPygame3DMesh, transform: dict) -> MockPygame3DMesh:
        """Applies position, rotation, and scale to a mesh's vertices."""
        
        pos = Vector3(*transform.get('position', [0, 0, 0]))
        rot = Vector3(*transform.get('rotation', [0, 0, 0])) # Euler angles
        scale = Vector3(*transform.get('scale', [1, 1, 1]))
        
        new_vertices = []
        for v in mesh.vertices:
            v_vec = Vector3(*v)
            
            # 1. Apply Scale
            v_vec.x *= scale.x
            v_vec.y *= scale.y
            v_vec.z *= scale.z
            
            # 2. Apply Rotation (Simplified Z-axis rotation mock)
            # Full 3D rotation requires rotation matrices (not implemented in simple Vector3)
            # For this mock, we only apply Z-rotation for demonstrative purpose
            if rot.z != 0.0:
                 rad = MathUtils.deg_to_rad(rot.z)
                 cos_r = math.cos(rad)
                 sin_r = math.sin(rad)
                 new_x = v_vec.x * cos_r - v_vec.y * sin_r
                 new_y = v_vec.x * sin_r + v_vec.y * cos_r
                 v_vec.x, v_vec.y = new_x, new_y
            
            # 3. Apply Position (Translation)
            v_vec += pos
            
            new_vertices.append(v_vec.to_tuple())
            
        return MockPygame3DMesh(new_vertices, mesh.faces, mesh.normals, mesh.uvs)

    # --- Boolean Operation Mock/Approximation ---

    def _approximate_union(self, mesh_a: MockPygame3DMesh, mesh_b: MockPygame3DMesh) -> MockPygame3DMesh:
        """
        Mocks the Union operation: combines vertices and faces of A and B. 
        Note: This creates non-manifold geometry in most cases (not a real CSG result).
        """
        # 1. Combine Vertices
        offset = len(mesh_a.vertices)
        new_vertices = mesh_a.vertices + mesh_b.vertices
        
        # 2. Combine Faces (offsetting B's indices)
        new_faces = mesh_a.faces + [[f[i] + offset for i in range(len(f))] for f in mesh_b.faces]
        
        FileUtils.log_message(f"CSG Union (Mock): Combined {len(mesh_a.vertices)} + {len(mesh_b.vertices)} vertices.")
        return MockPygame3DMesh(new_vertices, new_faces)

    def _approximate_subtract(self, mesh_a: MockPygame3DMesh, mesh_b: MockPygame3DMesh) -> MockPygame3DMesh:
        """
        Mocks the Subtract operation (A - B). For this simple mock, we just return A.
        Real subtraction requires finding intersections and flipping faces.
        """
        # NOTE: A robust CSG library (e.g., python-occ or pycgal) is required for real mesh boolean operations.
        # This is a stub for the logic flow, returning only the first operand as a visual cue.
        FileUtils.log_warning("CSG Subtract (Mock): Returning only Mesh A. Real boolean operations are complex.")
        return mesh_a

    def _approximate_intersect(self, mesh_a: MockPygame3DMesh, mesh_b: MockPygame3DMesh) -> MockPygame3DMesh:
        """
        Mocks the Intersect operation (A ∩ B). Returns a simple placeholder.
        """
        FileUtils.log_warning("CSG Intersect (Mock): Returning a simple Cube Placeholder.")
        return self._generate_cube(size=0.5)

    # --- Editor Tools ---
    
    def get_primitive_types(self):
        """Returns list of supported primitive types for the UI."""
        return ['cube', 'sphere', 'cylinder', 'plane']
        
    def get_boolean_ops(self):
        """Returns list of supported boolean operations for the UI."""
        return ['union', 'subtract', 'intersect']

    def export_mesh(self, mesh: MockPygame3DMesh, file_path: str):
        """Exports the final mesh to a file (e.g., OBJ)."""
        # Delegate to MeshLoader to save
        self.mesh_loader.save_mesh_to_json(mesh, file_path) # Save as our internal JSON for ease
        
    def get_active_tree_dict(self):
        """Returns the serializable dictionary representation of the active tree."""
        return self.active_tree_root.to_dict()