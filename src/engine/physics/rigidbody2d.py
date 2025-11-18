# engine/physics/rigidbody2d.py
import math
import sys

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.vector2 import Vector2
    from engine.utils.file_utils import FileUtils
except ImportError as e:
    print(f"[Rigidbody2D Import Error] {e}. Using Internal Mocks.")
    class Vector2:
        def __init__(self, x=0, y=0): self.x, self.y = float(x), float(y)
        def __add__(self, other): return Vector2(self.x + other.x, self.y + other.y)
        def __mul__(self, scalar): return Vector2(self.x * scalar, self.y * scalar)
        def copy(self): return Vector2(self.x, self.y)
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[RB2D-INFO] {msg}")


class Rigidbody2D:
    """
    Represents the physical state and properties of a 2D game object, 
    used by the Physics2D system for integration and collision response.
    """
    
    def __init__(self, position: Vector2, mass: float = 1.0, is_dynamic: bool = True):
        # --- State ---
        self.position = position.copy() # Current world position (Vector2)
        self.velocity = Vector2(0, 0)   # Linear velocity (Vector2)
        self.rotation = 0.0             # Current rotation (float, Z-axis)
        self.angular_velocity = 0.0     # Angular velocity (float)
        
        self.force_accumulator = Vector2(0, 0) # Sum of all forces applied this frame
        self.torque_accumulator = 0.0          # Sum of all torques applied this frame
        
        # --- Properties ---
        self.mass = max(0.001, mass)           # Mass (cannot be zero or negative for dynamic)
        self.inv_mass = 1.0 / self.mass if self.mass > 0 else 0.0
        self.inertia = 1.0                     # Rotational inertia (simplified)
        self.inv_inertia = 1.0 / self.inertia if self.inertia > 0 else 0.0
        
        self.is_dynamic = is_dynamic           # Whether forces/gravity affect it
        self.is_kinematic = not is_dynamic and mass > 0 # Controlled by user, not physics
        
        self.restitution = 0.3                 # Bounciness (0=no bounce, 1=perfect bounce)
        self.linear_damping = 0.01             # Linear drag (0=none, 1=max)
        self.angular_damping = 0.05            # Angular drag
        
        # --- Runtime Flags ---
        self.is_grounded = False               # Useful for game logic (e.g., can jump)

    @classmethod
    def from_component(cls, component_data: dict, initial_position: Vector2):
        """
        Creates a Rigidbody2D instance from a SceneObject's component dictionary.
        """
        mass = component_data.get("mass", 1.0)
        is_dynamic = component_data.get("is_dynamic", True)
        
        rb = cls(initial_position, mass, is_dynamic)
        
        rb.velocity = Vector2(*component_data.get("initial_velocity", [0, 0]))
        rb.angular_velocity = component_data.get("initial_angular_velocity", 0.0)
        rb.restitution = component_data.get("restitution", rb.restitution)
        rb.linear_damping = component_data.get("linear_damping", rb.linear_damping)
        rb.angular_damping = component_data.get("angular_damping", rb.angular_damping)
        
        return rb

    def add_force(self, force: Vector2):
        """Adds a linear force vector to the accumulator for the current frame."""
        if self.is_dynamic:
            self.force_accumulator += force

    def add_torque(self, torque: float):
        """Adds rotational force to the torque accumulator."""
        if self.is_dynamic:
            self.torque_accumulator += torque
            
    def set_position(self, new_position: Vector2):
        """Sets the position and updates internal state."""
        self.position = new_position.copy()

    def to_dict(self):
        """Converts the Rigidbody state to a serializable component dictionary."""
        return {
            "type": "Rigidbody2D",
            "mass": self.mass,
            "is_dynamic": self.is_dynamic,
            "restitution": self.restitution,
            "linear_damping": self.linear_damping,
            "angular_damping": self.angular_damping,
            "initial_velocity": self.velocity.to_tuple(), # Saves current as initial for persistence
            "initial_angular_velocity": self.angular_velocity
            # NOTE: Runtime state (position, accumulators) is not saved here, as it belongs to the scene object/physics integration.
        }

    # --- Editor/Inspector Schema (for gui/panel_inspector.py) ---
    
    @staticmethod
    def get_schema():
        """Returns the schema definition for the Rigidbody2D component."""
        return {
            "mass": {"type": "float", "label": "Mass (kg)", "min": 0.01, "max": 1000.0},
            "is_dynamic": {"type": "boolean", "label": "Is Dynamic"},
            "restitution": {"type": "float", "label": "Restitution (Bounciness)", "min": 0.0, "max": 1.0},
            "linear_damping": {"type": "float", "label": "Linear Damping", "min": 0.0, "max": 1.0},
            "angular_damping": {"type": "float", "label": "Angular Damping", "min": 0.0, "max": 1.0},
            "initial_velocity": {"type": "vector2", "label": "Initial Velocity"},
            "initial_angular_velocity": {"type": "float", "label": "Initial Angular Velocity"}
        }