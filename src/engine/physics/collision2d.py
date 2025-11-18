# engine/physics/collision2d.py
import math
import sys

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.vector2 import Vector2
    from engine.utils.file_utils import FileUtils
    from engine.core.scene_manager import SceneObject
except ImportError as e:
    print(f"[Collision2D Import Error] {e}. Using Internal Mocks.")
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = x, y
        def __sub__(self, other): return Vector2(self.x - other.x, self.y - other.y)
        def dot(self, other): return self.x * other.x + self.y * other.y
        @property
        def magnitude(self): return math.sqrt(self.x**2 + self.y**2)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[C2D-INFO] {msg}")
    class SceneObject:
        def __init__(self, pos, scale): self.position = Vector2(*pos); self.scale = Vector2(*scale)
        def get_component(self, type): return {"width": 32, "height": 32} # Mock


# --- Collision Data Structure ---
class CollisionInfo:
    """Stores the result of a collision check."""
    def __init__(self, collided: bool, normal: Vector2 = None, penetration: float = 0.0, obj_a: SceneObject = None, obj_b: SceneObject = None):
        self.collided = collided
        self.normal = normal # Minimum Translation Vector (MTV) direction
        self.penetration = penetration # Depth of penetration
        self.obj_a = obj_a
        self.obj_b = obj_b


# --- Collision 2D System ---
class Collision2D:
    """
    Handles 2D collision detection (e.g., AABB, Circle, Polygon vs Polygon).
    Uses SAT (Separating Axis Theorem) or simpler methods for primitive collisions.
    """
    
    def __init__(self):
        FileUtils.log_message("Collision2D system ready.")

    def check_collision(self, obj_a: SceneObject, obj_b: SceneObject) -> CollisionInfo:
        """
        Main entry point for collision detection between two SceneObjects.
        Determines the appropriate collision function based on collider components.
        """
        col_a = self._get_collider_data(obj_a)
        col_b = self._get_collider_data(obj_b)
        
        if not col_a or not col_b:
            return CollisionInfo(False)

        # For this minimal implementation, we only support Box-Box AABB for now.
        if col_a["type"] == "BoxCollider2D" and col_b["type"] == "BoxCollider2D":
            # NOTE: We skip rotation handling for this simplified AABB check.
            return self._test_aabb_vs_aabb(obj_a, col_a, obj_b, col_b)
        
        # Add logic for Circle vs Circle, Box vs Circle, Polygon vs Polygon (using SAT)
        
        return CollisionInfo(False)

    def _get_collider_data(self, obj: SceneObject) -> dict | None:
        """Extracts and standardizes collider data from a SceneObject."""
        # Prioritize BoxCollider2D for this demo
        col_data = obj.get_component("BoxCollider2D")
        if col_data:
            return {
                "type": "BoxCollider2D",
                "width": col_data.get("width", 1.0) * obj.scale.x,
                "height": col_data.get("height", 1.0) * obj.scale.y,
                "offset": col_data.get("offset", [0, 0])
            }
            
        # Add checks for other types here (e.g., CircleCollider2D, PolygonCollider2D)
        
        return None

    def _test_aabb_vs_aabb(self, obj_a: SceneObject, col_a: dict, obj_b: SceneObject, col_b: dict) -> CollisionInfo:
        """
        Performs Axis-Aligned Bounding Box (AABB) check. 
        Ignores rotation of the objects.
        """
        
        # Calculate half-extents (half width/height)
        half_w_a = col_a["width"] / 2.0
        half_h_a = col_a["height"] / 2.0
        half_w_b = col_b["width"] / 2.0
        half_h_b = col_b["height"] / 2.0
        
        # Calculate centers (including offset, though we ignore offset for this simple demo)
        center_a = obj_a.position
        center_b = obj_b.position
        
        # Calculate distance between centers
        dist_x = center_b.x - center_a.x
        dist_y = center_b.y - center_a.y
        
        # Sum of half-extents
        sum_half_w = half_w_a + half_w_b
        sum_half_h = half_h_a + half_h_b
        
        # Check for non-overlap
        x_overlap = sum_half_w - abs(dist_x)
        y_overlap = sum_half_h - abs(dist_y)
        
        if x_overlap <= 0 or y_overlap <= 0:
            return CollisionInfo(False) # No collision
            
        # Collision detected. Calculate Minimum Translation Vector (MTV)
        
        if x_overlap < y_overlap:
            # Separation required on X-axis (MTV is horizontal)
            penetration = x_overlap
            normal_x = 1.0 if dist_x > 0 else -1.0
            normal = Vector2(normal_x, 0)
        else:
            # Separation required on Y-axis (MTV is vertical)
            penetration = y_overlap
            normal_y = 1.0 if dist_y > 0 else -1.0
            normal = Vector2(0, normal_y)
            
        return CollisionInfo(True, normal, penetration, obj_a, obj_b)

    def resolve_collision(self, info: CollisionInfo, rb_a, rb_b) -> bool:
        """
        Resolves the collision by separating the objects (position correction) 
        and applying impulse (velocity change).
        """
        if not info.collided:
            return False
            
        obj_a, obj_b = info.obj_a, info.obj_b
        normal = info.normal
        penetration = info.penetration
        
        # Check if both rigidbodies exist (for dynamic response)
        has_rb_a = rb_a is not None
        has_rb_b = rb_b is not None
        
        # --- 1. Positional Correction (Separation) ---
        
        # Determine movement percentages (assuming inverse mass weighting)
        total_inv_mass = (rb_a.inv_mass if has_rb_a else 0) + (rb_b.inv_mass if has_rb_b else 0)
        
        if total_inv_mass == 0:
            # Both objects are static/kinematic. Cannot resolve position.
            return False
            
        percent_a = (rb_a.inv_mass / total_inv_mass) if has_rb_a else 0
        percent_b = (rb_b.inv_mass / total_inv_mass) if has_rb_b else 0
        
        # Apply slight bias (e.g., 0.8) to penetration correction to prevent sinking
        correction = normal * (penetration / total_inv_mass) * 0.8 
        
        if has_rb_a:
            obj_a.position -= correction * percent_a 
        if has_rb_b:
            obj_b.position += correction * percent_b 

        # --- 2. Impulse (Velocity Correction) ---
        
        # Relative velocity (Vb - Va)
        v_a = rb_a.velocity if has_rb_a else Vector2(0, 0)
        v_b = rb_b.velocity if has_rb_b else Vector2(0, 0)
        v_rel = v_b - v_a
        
        # Calculate impulse j (dot product of V_rel with normal)
        v_normal = v_rel.dot(normal)
        
        # Do not resolve if velocities are separating
        if v_normal > 0:
            return True 
            
        # Combined restitution (e = min(e_a, e_b))
        e = min(rb_a.restitution if has_rb_a else 1.0, rb_b.restitution if has_rb_b else 1.0)
        
        # Impulse scalar: j = -(1+e) * v_normal / (inv_mass_a + inv_mass_b)
        j = -(1.0 + e) * v_normal / total_inv_mass
        
        # Apply impulse J = j * normal
        impulse = normal * j
        
        if has_rb_a:
            rb_a.velocity -= impulse * rb_a.inv_mass
        if has_rb_b:
            rb_b.velocity += impulse * rb_b.inv_mass
            
        return True