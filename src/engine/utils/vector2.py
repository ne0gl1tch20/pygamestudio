# engine/utils/vector2.py
import math

class Vector2:
    """A 2D vector class for position, direction, etc."""
    
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    def __str__(self):
        return f"({self.x:.2f}, {self.y:.2f})"

    def __repr__(self):
        return f"Vector2({self.x}, {self.y})"

    # --- Basic Operations ---
    
    def __add__(self, other):
        """Vector addition: V1 + V2 or V + scalar."""
        if isinstance(other, Vector2):
            return Vector2(self.x + other.x, self.y + other.y)
        # Assuming scalar addition
        return Vector2(self.x + other, self.y + other)

    def __sub__(self, other):
        """Vector subtraction: V1 - V2 or V - scalar."""
        if isinstance(other, Vector2):
            return Vector2(self.x - other.x, self.y - other.y)
        # Assuming scalar subtraction
        return Vector2(self.x - other, self.y - other)

    def __mul__(self, scalar):
        """Scalar multiplication: V * scalar."""
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar):
        """Scalar division: V / scalar."""
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide Vector2 by zero.")
        return Vector2(self.x / scalar, self.y / scalar)
        
    def __rmul__(self, scalar):
        """Reverse scalar multiplication: scalar * V."""
        return self.__mul__(scalar)
        
    def __neg__(self):
        """Negation: -V."""
        return Vector2(-self.x, -self.y)

    def __eq__(self, other):
        """Equality check."""
        if not isinstance(other, Vector2):
            return False
        return self.x == other.x and self.y == other.y
        
    def __iter__(self):
        """Allows unpacking: x, y = vec."""
        return iter((self.x, self.y))

    # --- Properties ---
    
    @property
    def magnitude_sqr(self):
        """The squared length (magnitude) of the vector."""
        return self.x * self.x + self.y * self.y

    @property
    def magnitude(self):
        """The length (magnitude) of the vector."""
        return math.sqrt(self.magnitude_sqr)

    # --- Vector Methods ---

    def copy(self):
        """Returns a new, identical Vector2 instance."""
        return Vector2(self.x, self.y)

    def normalize(self):
        """Returns a new vector with magnitude 1 (normalized)."""
        m = self.magnitude
        if m > 0:
            return Vector2(self.x / m, self.y / m)
        return Vector2(0.0, 0.0)
        
    def normalized(self):
        """Normalizes the vector in-place and returns itself (fluent interface)."""
        m = self.magnitude
        if m > 0:
            self.x /= m
            self.y /= m
        return self

    def dot(self, other):
        """Dot product of this vector and another."""
        return self.x * other.x + self.y * other.y

    def distance_to(self, other):
        """Calculates the Euclidean distance to another vector."""
        return (self - other).magnitude

    def lerp(self, other, t):
        """Linear interpolation between this vector and another."""
        t = MathUtils.clamp(t, 0.0, 1.0) # Assume MathUtils exists
        return self + (other - self) * t

    def to_tuple(self):
        """Returns a tuple representation (x, y)."""
        return (self.x, self.y)

    @classmethod
    def zero(cls):
        """Returns a Vector2 with (0, 0)."""
        return cls(0.0, 0.0)

    @classmethod
    def one(cls):
        """Returns a Vector2 with (1, 1)."""
        return cls(1.0, 1.0)
        
    @classmethod
    def up(cls):
        """Returns the world 'up' vector (0, -1) in Pygame coordinates (Y-down)."""
        return cls(0.0, -1.0) 
        
    @classmethod
    def down(cls):
        """Returns the world 'down' vector (0, 1) in Pygame coordinates (Y-down)."""
        return cls(0.0, 1.0) 
        
    @classmethod
    def left(cls):
        """Returns the world 'left' vector (-1, 0)."""
        return cls(-1.0, 0.0)
        
    @classmethod
    def right(cls):
        """Returns the world 'right' vector (1, 0)."""
        return cls(1.0, 0.0)

# NOTE: The MathUtils.clamp call relies on engine/utils/math_utils.py.
# We trust that the full project generation process will include it.

try:
    from engine.utils.math_utils import MathUtils
except ImportError:
    class MockMathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))
    MathUtils = MockMathUtils