# engine/rendering/mesh_utils.py
import math
import sys

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.vector3 import Vector3
    from engine.utils.math_utils import MathUtils
    from engine.utils.file_utils import FileUtils
except ImportError as e:
    print(f"[MeshUtils Import Error] {e}. Using Internal Mocks.")
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = x, y, z
        def __sub__(self, other): return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
        def cross(self, other): return Vector3(self.y * other.z - self.z * other.y, self.z * other.x - self.x * other.z, self.x * other.y - self.y * other.x)
        def normalize(self): return self # Mock normalize
    class MathUtils:
        @staticmethod
        def deg_to_rad(degrees): return degrees * (math.pi / 180.0)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[MU-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[MU-ERROR] {msg}", file=sys.stderr)


class MeshUtils:
    """
    Utility class containing static methods for manipulating and calculating 
    mesh data (normals, bounding boxes, transformations).
    """

    @staticmethod
    def calculate_face_normal(v1: list, v2: list, v3: list) -> Vector3:
        """
        Calculates the normal vector for a single triangle face.
        Uses the cross product of two edge vectors (v2-v1 and v3-v1).
        """
        try:
            vec1 = Vector3(*v1)
            vec2 = Vector3(*v2)
            vec3 = Vector3(*v3)

            edge1 = vec2 - vec1
            edge2 = vec3 - vec1

            normal = edge1.cross(edge2)
            # Normalize the normal vector
            return normal.normalize()
        except Exception as e:
            FileUtils.log_error(f"Error calculating face normal: {e}")
            return Vector3(0, 1, 0) # Default upward normal

    @staticmethod
    def calculate_smooth_normals(vertices: list[list], faces: list[list]) -> list[list]:
        """
        Calculates smooth vertex normals by averaging the normals of all 
        faces that share each vertex.
        Returns a list of Vector3 (or list[float]) for each vertex.
        """
        # Initialize an accumulator for each vertex
        vertex_normals = [Vector3(0, 0, 0) for _ in vertices]
        
        # 1. Calculate and accumulate face normals
        for face in faces:
            if len(face) < 3: continue
            
            # Get the vertices of the face (assuming triangular/triangulated faces)
            v1_idx, v2_idx, v3_idx = face[0], face[1], face[2]
            v1 = vertices[v1_idx]
            v2 = vertices[v2_idx]
            v3 = vertices[v3_idx]
            
            face_normal = MeshUtils.calculate_face_normal(v1, v2, v3)
            
            # Accumulate the face normal for each vertex in the face
            vertex_normals[v1_idx] += face_normal
            vertex_normals[v2_idx] += face_normal
            vertex_normals[v3_idx] += face_normal
            
        # 2. Normalize the accumulated vectors
        final_normals = []
        for normal in vertex_normals:
            final_normals.append(normal.normalize().to_tuple() if hasattr(normal, 'to_tuple') else normal.to_tuple())
            
        return final_normals

    @staticmethod
    def get_aabb(vertices: list[list]) -> tuple[Vector3, Vector3] | tuple[None, None]:
        """
        Calculates the Axis-Aligned Bounding Box (AABB) of a mesh.
        Returns (min_corner, max_corner) as Vector3.
        """
        if not vertices:
            return None, None
            
        # Initialize min/max with the first vertex
        min_x, max_x = vertices[0][0], vertices[0][0]
        min_y, max_y = vertices[0][1], vertices[0][1]
        min_z, max_z = vertices[0][2], vertices[0][2]
        
        for v in vertices[1:]:
            x, y, z = v[0], v[1], v[2]
            
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            
            min_z = min(min_z, z)
            max_z = max(max_z, z)
            
        min_corner = Vector3(min_x, min_y, min_z)
        max_corner = Vector3(max_x, max_y, max_z)
        
        return min_corner, max_corner

    @staticmethod
    def transform_vertex(vertex: Vector3 | list, position: Vector3, rotation: Vector3, scale: Vector3) -> Vector3:
        """
        Applies position, rotation, and scale transforms to a single vertex.
        This is a basic implementation of 3D affine transformation.
        """
        v_vec = Vector3(*vertex) if isinstance(vertex, list) else vertex

        # 1. Scale
        v_vec.x *= scale.x
        v_vec.y *= scale.y
        v_vec.z *= scale.z

        # 2. Rotate (Using Euler angles - Order ZYX for simplicity)
        # Note: Proper implementation uses Quaternion or a full 4x4 matrix.
        
        # Z-rotation
        if rotation.z != 0.0:
            rad = MathUtils.deg_to_rad(rotation.z)
            cos_r = math.cos(rad)
            sin_r = math.sin(rad)
            x_temp = v_vec.x * cos_r - v_vec.y * sin_r
            y_temp = v_vec.x * sin_r + v_vec.y * cos_r
            v_vec.x, v_vec.y = x_temp, y_temp
            
        # Y-rotation
        if rotation.y != 0.0:
            rad = MathUtils.deg_to_rad(rotation.y)
            cos_r = math.cos(rad)
            sin_r = math.sin(rad)
            x_temp = v_vec.x * cos_r + v_vec.z * sin_r
            z_temp = v_vec.z * cos_r - v_vec.x * sin_r
            v_vec.x, v_vec.z = x_temp, z_temp
            
        # X-rotation
        if rotation.x != 0.0:
            rad = MathUtils.deg_to_rad(rotation.x)
            cos_r = math.cos(rad)
            sin_r = math.sin(rad)
            y_temp = v_vec.y * cos_r - v_vec.z * sin_r
            z_temp = v_vec.y * sin_r + v_vec.z * cos_r
            v_vec.y, v_vec.z = y_temp, z_temp

        # 3. Translate
        v_vec += position
        
        return v_vec
        
    @staticmethod
    def triangulate_polygon(indices: list[int]) -> list[list[int]]:
        """
        Converts a list of polygon vertex indices (len > 3) into a list of 
        triangle index lists using a simple fan triangulation.
        Assumes the polygon is convex and planar.
        """
        if len(indices) < 3:
            return []
        if len(indices) == 3:
            return [indices]
            
        triangles = []
        v0 = indices[0] # Anchor the fan at the first vertex
        for i in range(1, len(indices) - 1):
            v1 = indices[i]
            v2 = indices[i+1]
            triangles.append([v0, v1, v2])
            
        return triangles