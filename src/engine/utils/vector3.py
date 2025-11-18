# engine/utils/vector3.py
import math

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.utils.math_utils import MathUtils
except ImportError:
    class MockMathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))
    MathUtils = MockMathUtils


class Vector3:
    """A 3D vector class for position, direction, etc."""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __str__(self):
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

    def __repr__(self):
        return f"Vector3({self.x}, {self.y}, {self.z})"

    # --- Basic Operations ---
    
    def __add__(self, other):
        """Vector addition: V1 + V2 or V + scalar."""
        if isinstance(other, Vector3):
            return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
        # Assuming scalar addition
        return Vector3(self.x + other, self.y + other, self.z + other)

    def __sub__(self, other):
        """Vector subtraction: V1 - V2 or V - scalar."""
        if isinstance(other, Vector3):
            return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
        # Assuming scalar subtraction
        return Vector3(self.x - other, self.y - other, self.z - other)

    def __mul__(self, scalar):
        """Scalar multiplication: V * scalar."""
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar):
        """Scalar division: V / scalar."""
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide Vector3 by zero.")
        return Vector3(self.x / scalar, self.y / scalar, self.z / scalar)
        
    def __rmul__(self, scalar):
        """Reverse scalar multiplication: scalar * V."""
        return self.__mul__(scalar)
        
    def __neg__(self):
        """Negation: -V."""
        return Vector3(-self.x, -self.y, -self.z)

    def __eq__(self, other):
        """Equality check."""
        if not isinstance(other, Vector3):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z
        
    def __iter__(self):
        """Allows unpacking: x, y, z = vec."""
        return iter((self.x, self.y, self.z))

    # --- Properties ---
    
    @property
    def magnitude_sqr(self):
        """The squared length (magnitude) of the vector."""
        return self.x * self.x + self.y * self.y + self.z * self.z

    @property
    def magnitude(self):
        """The length (magnitude) of the vector."""
        return math.sqrt(self.magnitude_sqr)

    # --- Vector Methods ---

    def copy(self):
        """Returns a new, identical Vector3 instance."""
        return Vector3(self.x, self.y, self.z)

    def normalize(self):
        """Returns a new vector with magnitude 1 (normalized)."""
        m = self.magnitude
        if m > 0:
            return Vector3(self.x / m, self.y / m, self.z / m)
        return Vector3(0.0, 0.0, 0.0)
        
    def normalized(self):
        """Normalizes the vector in-place and returns itself (fluent interface)."""
        m = self.magnitude
        if m > 0:
            self.x /= m
            self.y /= m
            self.z /= m
        return self

    def dot(self, other):
        """Dot product of this vector and another."""
        return self.x * other.x + self.y * other.y + self.z * other.z
        
    def cross(self, other):
        """Cross product of this vector and another."""
        x = self.y * other.z - self.z * other.y
        y = self.z * other.x - self.x * other.z
        z = self.x * other.y - self.y * other.x
        return Vector3(x, y, z)

    def distance_to(self, other):
        """Calculates the Euclidean distance to another vector."""
        return (self - other).magnitude

    def lerp(self, other, t):
        """Linear interpolation between this vector and another."""
        t = MathUtils.clamp(t, 0.0, 1.0)
        return self + (other - self) * t

    def to_tuple(self):
        """Returns a tuple representation (x, y, z)."""
        return (self.x, self.y, self.z)

    @classmethod
    def zero(cls):
        """Returns a Vector3 with (0, 0, 0)."""
        return cls(0.0, 0.0, 0.0)

    @classmethod
    def one(cls):
        """Returns a Vector3 with (1, 1, 1)."""
        return cls(1.0, 1.0, 1.0)
        
    @classmethod
    def up(cls):
        """Returns the world 'up' vector (0, 1, 0) (Y-up convention)."""
        return cls(0.0, 1.0, 0.0)
        
    @classmethod
    def down(cls):
        """Returns the world 'down' vector (0, -1, 0) (Y-up convention)."""
        return cls(0.0, -1.0, 0.0)
        
    @classmethod
    def forward(cls):
        """Returns the world 'forward' vector (0, 0, 1) (Z-forward convention)."""
        return cls(0.0, 0.0, 1.0)
        
    @classmethod
    def back(cls):
        """Returns the world 'back' vector (0, 0, -1) (Z-forward convention)."""
        return cls(0.0, 0.0, -1.0)
        
    @classmethod
    def left(cls):
        """Returns the world 'left' vector (-1, 0, 0)."""
        return cls(-1.0, 0.0, 0.0)
        
    @classmethod
    def right(cls):
        """Returns the world 'right' vector (1, 0, 0)."""
        return cls(1.0, 0.0, 0.0)