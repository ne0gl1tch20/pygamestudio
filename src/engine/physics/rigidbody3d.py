# engine/physics/rigidbody3d.py
import math
import sys

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.vector3 import Vector3
    from engine.utils.file_utils import FileUtils
except ImportError as e:
    print(f"[Rigidbody3D Import Error] {e}. Using Internal Mocks.")
    class Vector3:
        def __init__(self, x=0, y=0, z=0): self.x, self.y, self.z = float(x), float(y), float(z)
        def __add__(self, other): return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
        def __mul__(self, scalar): return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
        def copy(self): return Vector3(self.x, self.y, self.z)
        def to_tuple(self): return (self.x, self.y, self.z)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[RB3D-INFO] {msg}")


class Rigidbody3D:
    """
    Represents the physical state and properties of a 3D game object, 
    used by the Physics3D system for integration and collision response.
    """
    
    def __init__(self, position: Vector3, rotation: Vector3, mass: float = 1.0, is_dynamic: bool = True):
        # --- State ---
        self.position = position.copy()       # Current world position (Vector3)
        self.velocity = Vector3(0, 0, 0)      # Linear velocity (Vector3)
        self.rotation = rotation.copy()       # Current rotation (Vector3 - Euler angles, generally unstable)
        self.angular_velocity = Vector3(0, 0, 0) # Angular velocity (Vector3)
        
        self.force_accumulator = Vector3(0, 0, 0) # Sum of all forces applied this frame
        self.torque_accumulator = Vector3(0, 0, 0) # Sum of all torques applied this frame
        
        # --- Properties ---
        self.mass = max(0.001, mass)           # Mass (cannot be zero or negative for dynamic)
        self.inv_mass = 1.0 / self.mass if self.mass > 0 else 0.0
        # NOTE: 3D Inertia is a 3x3 tensor. We mock a simple scalar for a spherical/cubical object.
        self.inertia = Vector3(1.0, 1.0, 1.0)  # Rotational inertia (Vector3 diagonal of tensor)
        self.inv_inertia = Vector3(1.0 / self.inertia.x, 1.0 / self.inertia.y, 1.0 / self.inertia.z)
        
        self.is_dynamic = is_dynamic           # Whether forces/gravity affect it
        self.is_kinematic = not is_dynamic and mass > 0 # Controlled by user, not physics
        
        self.restitution = 0.3                 # Bounciness (0=no bounce, 1=perfect bounce)
        self.linear_damping = 0.01             # Linear drag (0=none, 1=max)
        self.angular_damping = 0.05            # Angular drag
        
        # --- Runtime Flags ---
        self.is_grounded = False               # Useful for game logic

    @classmethod
    def from_component(cls, component_data: dict, initial_position: Vector3, initial_rotation: Vector3):
        """
        Creates a Rigidbody3D instance from a SceneObject's component dictionary.
        """
        mass = component_data.get("mass", 1.0)
        is_dynamic = component_data.get("is_dynamic", True)
        
        rb = cls(initial_position, initial_rotation, mass, is_dynamic)
        
        rb.velocity = Vector3(*component_data.get("initial_velocity", [0, 0, 0]))
        rb.angular_velocity = Vector3(*component_data.get("initial_angular_velocity", [0, 0, 0]))
        rb.restitution = component_data.get("restitution", rb.restitution)
        rb.linear_damping = component_data.get("linear_damping", rb.linear_damping)
        rb.angular_damping = component_data.get("angular_damping", rb.angular_damping)
        
        # Mock inertia setup for BoxCollider3D
        # For a solid cuboid of size w, h, d: I_xx = m/12 * (h^2 + d^2)
        collider_comp = component_data.get("collider_data") # Mock way to get collider info
        if collider_comp and collider_comp.get("type") == "BoxCollider3D":
            extents = collider_comp.get("half_extents", [1, 1, 1])
            w, h, d = extents[0] * 2, extents[1] * 2, extents[2] * 2
            
            # Simple box inertia tensor diagonals
            rb.inertia.x = mass / 12.0 * (h**2 + d**2)
            rb.inertia.y = mass / 12.0 * (w**2 + d**2)
            rb.inertia.z = mass / 12.0 * (w**2 + h**2)
            rb.inv_inertia = Vector3(1.0/rb.inertia.x, 1.0/rb.inertia.y, 1.0/rb.inertia.z)
        
        return rb

    def add_force(self, force: Vector3, point_of_impact: Vector3 = None):
        """
        Adds a linear force vector to the accumulator.
        If point_of_impact is provided (local space), it also calculates torque.
        """
        if self.is_dynamic:
            self.force_accumulator += force
            
            # Simplified torque calculation (Torque = r x F, where r = point - center)
            if point_of_impact:
                # Assuming point_of_impact is world space and we translate it to a vector relative to center
                relative_vector = point_of_impact - self.position 
                torque = relative_vector.cross(force)
                self.torque_accumulator += torque

    def add_torque(self, torque: Vector3):
        """Adds rotational force vector (torque) to the accumulator."""
        if self.is_dynamic:
            self.torque_accumulator += torque
            
    def set_position(self, new_position: Vector3):
        """Sets the position and updates internal state."""
        self.position = new_position.copy()
        
    def set_rotation(self, new_rotation: Vector3):
        """Sets the rotation and updates internal state."""
        self.rotation = new_rotation.copy()

    def to_dict(self):
        """Converts the Rigidbody state to a serializable component dictionary."""
        return {
            "type": "Rigidbody3D",
            "mass": self.mass,
            "is_dynamic": self.is_dynamic,
            "restitution": self.restitution,
            "linear_damping": self.linear_damping,
            "angular_damping": self.angular_damping,
            "initial_velocity": self.velocity.to_tuple(), 
            "initial_angular_velocity": self.angular_velocity.to_tuple(),
            # NOTE: Inertia/InvMass are calculated from Mass/Collider and are not serialized directly.
        }

    # --- Editor/Inspector Schema (for gui/panel_inspector.py) ---
    
    @staticmethod
    def get_schema():
        """Returns the schema definition for the Rigidbody3D component."""
        return {
            "mass": {"type": "float", "label": "Mass (kg)", "min": 0.01, "max": 1000.0},
            "is_dynamic": {"type": "boolean", "label": "Is Dynamic"},
            "restitution": {"type": "float", "label": "Restitution (Bounciness)", "min": 0.0, "max": 1.0},
            "linear_damping": {"type": "float", "label": "Linear Damping", "min": 0.0, "max": 1.0},
            "angular_damping": {"type": "float", "label": "Angular Damping", "min": 0.0, "max": 1.0},
            "initial_velocity": {"type": "vector3", "label": "Initial Velocity"},
            "initial_angular_velocity": {"type": "vector3", "label": "Initial Angular Velocity (Euler)"}
        }