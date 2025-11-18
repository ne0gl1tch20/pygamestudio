# engine/physics/collision3d.py
import math
import sys

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.vector3 import Vector3
    from engine.utils.file_utils import FileUtils
    from engine.core.scene_manager import SceneObject
    from engine.rendering.mesh_utils import MeshUtils
except ImportError as e:
    print(f"[Collision3D Import Error] {e}. Using Internal Mocks.")
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = x, y, z
        def __sub__(self, other): return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
        def dot(self, other): return self.x * other.x + self.y * other.y + self.z * other.z
        @property
        def magnitude(self): return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[C3D-INFO] {msg}")
    class SceneObject:
        def __init__(self, pos, scale): self.position = Vector3(*pos); self.scale = Vector3(*scale)
        def get_component(self, type): return {"half_extents": [1, 1, 1]} # Mock
    class MeshUtils:
        @staticmethod
        def get_aabb(vertices):
            # Mock AABB based on half_extents * 2
            return Vector3(-1, -1, -1), Vector3(1, 1, 1)


# --- Collision Data Structure ---
class CollisionInfo3D:
    """Stores the result of a 3D collision check."""
    def __init__(self, collided: bool, normal: Vector3 = None, penetration: float = 0.0, obj_a: SceneObject = None, obj_b: SceneObject = None, contacts: list = None):
        self.collided = collided
        self.normal = normal # Minimum Translation Vector (MTV) direction
        self.penetration = penetration # Depth of penetration
        self.obj_a = obj_a
        self.obj_b = obj_b
        self.contacts = contacts if contacts is not None else [] # List of contact points


# --- Collision 3D System ---
class Collision3D:
    """
    Handles 3D collision detection (e.g., AABB, Sphere, OBB).
    This is a mock implementation focusing on AABB for simplicity.
    A real 3D engine would use GJK or a dedicated physics library.
    """
    
    def __init__(self):
        FileUtils.log_message("Collision3D system ready (Mock).")

    def check_collision(self, obj_a: SceneObject, obj_b: SceneObject) -> CollisionInfo3D:
        """
        Main entry point for 3D collision detection.
        Assumes BoxCollider3D components are used for AABB checks.
        """
        col_a = self._get_collider_data(obj_a)
        col_b = self._get_collider_data(obj_b)
        
        if not col_a or not col_b:
            return CollisionInfo3D(False)

        # Only implement AABB vs AABB for this minimal system
        if col_a["type"] == "BoxCollider3D" and col_b["type"] == "BoxCollider3D":
            # NOTE: This AABB check ignores object rotation. A rotated box needs an OBB check.
            return self._test_aabb_vs_aabb(obj_a, col_a, obj_b, col_b)
        
        # Add logic for Sphere vs Sphere, Sphere vs Box, etc.
        
        return CollisionInfo3D(False)

    def _get_collider_data(self, obj: SceneObject) -> dict | None:
        """Extracts and standardizes 3D collider data from a SceneObject."""
        # Prioritize BoxCollider3D
        col_data = obj.get_component("BoxCollider3D")
        if col_data:
            # Use half_extents directly if available, otherwise default to a size 2 box (extents 1)
            extents_data = col_data.get("half_extents", [1.0, 1.0, 1.0])
            if isinstance(obj.scale, Vector3):
                half_extents = Vector3(extents_data[0] * obj.scale.x, extents_data[1] * obj.scale.y, extents_data[2] * obj.scale.z)
            else:
                 # Fallback for scale type mismatch
                 half_extents = Vector3(extents_data[0], extents_data[1], extents_data[2])
                 
            return {
                "type": "BoxCollider3D",
                "half_extents": half_extents,
                "center_offset": Vector3(*col_data.get("offset", [0, 0, 0])),
            }
            
        # Add checks for SphereCollider3D, etc.
        
        return None

    def _test_aabb_vs_aabb(self, obj_a: SceneObject, col_a: dict, obj_b: SceneObject, col_b: dict) -> CollisionInfo3D:
        """
        Performs 3D Axis-Aligned Bounding Box (AABB) check.
        """
        
        ext_a = col_a["half_extents"]
        ext_b = col_b["half_extents"]
        
        center_a = obj_a.position + col_a["center_offset"]
        center_b = obj_b.position + col_b["center_offset"]
        
        # Calculate distance between centers
        dist = center_b - center_a
        
        # Sum of half-extents
        sum_half_x = ext_a.x + ext_b.x
        sum_half_y = ext_a.y + ext_b.y
        sum_half_z = ext_a.z + ext_b.z
        
        # Calculate overlap on each axis
        x_overlap = sum_half_x - abs(dist.x)
        y_overlap = sum_half_y - abs(dist.y)
        z_overlap = sum_half_z - abs(dist.z)
        
        if x_overlap <= 0 or y_overlap <= 0 or z_overlap <= 0:
            return CollisionInfo3D(False) # No collision
            
        # Collision detected. Calculate MTV (Minimum Translation Vector)
        
        # Find the minimum overlap axis
        min_overlap = min(x_overlap, y_overlap, z_overlap)
        
        normal = Vector3(0, 0, 0)
        penetration = min_overlap
        
        if min_overlap == x_overlap:
            normal.x = 1.0 if dist.x < 0 else -1.0
        elif min_overlap == y_overlap:
            normal.y = 1.0 if dist.y < 0 else -1.0
        elif min_overlap == z_overlap:
            normal.z = 1.0 if dist.z < 0 else -1.0
            
        return CollisionInfo3D(True, normal, penetration, obj_a, obj_b)

    # NOTE: Resolution logic is typically handled by the physics engine 
    # (Physics3D.update) using the info returned here.
    # The resolution function is placed in Physics3D to centralize integration.