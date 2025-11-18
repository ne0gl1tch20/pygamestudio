# engine/utils/math_utils.py
import math
import random
import sys

# Attempt to import Vector3 for Perlin Noise gradient calculation (Mock if failed)
try:
    from engine.utils.vector3 import Vector3
except ImportError:
    class Vector3:
        def __init__(self, x, y, z): self.x, self.y, self.z = x, y, z
    

class MathUtils:
    """A collection of useful mathematical utilities."""

    @staticmethod
    def clamp(value, min_val, max_val):
        """Clamps a value between a minimum and maximum."""
        return max(min_val, min(max_val, value))

    @staticmethod
    def lerp(a, b, t):
        """Linear interpolation between two values a and b."""
        t = MathUtils.clamp(t, 0.0, 1.0)
        return a + (b - a) * t

    @staticmethod
    def smoothstep(edge0, edge1, x):
        """
        Smoothstep function: Returns 0.0 if x < edge0 and 1.0 if x > edge1.
        If edge0 < x < edge1, returns a value between 0.0 and 1.0 using a smooth cubic curve.
        """
        x = MathUtils.clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
        return x * x * (3.0 - 2.0 * x)

    @staticmethod
    def inv_lerp(a, b, v):
        """Inverse linear interpolation: returns t such that lerp(a, b, t) = v."""
        if a == b: return 0.0
        return MathUtils.clamp((v - a) / (b - a), 0.0, 1.0)

    @staticmethod
    def deg_to_rad(degrees):
        """Converts degrees to radians."""
        return degrees * (math.pi / 180.0)

    @staticmethod
    def rad_to_deg(radians):
        """Converts radians to degrees."""
        return radians * (180.0 / math.pi)

    @staticmethod
    def distance(p1, p2):
        """Calculates the Euclidean distance between two points (tuples or lists)."""
        if len(p1) != len(p2):
            raise ValueError("Points must have the same dimension.")
        
        sum_sq = sum([(p1[i] - p2[i]) ** 2 for i in range(len(p1))])
        return math.sqrt(sum_sq)

    # --- Perlin Noise Implementation (Simplified Classic Perlin) ---

    # Permutation array (p) and constant gradient vectors (g)
    _PERLIN_P = [random.randint(0, 255) for _ in range(256)] * 2
    
    # Gradient vectors for 3D (simplified to 12 vectors)
    _PERLIN_G = [
        Vector3(1, 1, 0), Vector3(-1, 1, 0), Vector3(1, -1, 0), Vector3(-1, -1, 0),
        Vector3(1, 0, 1), Vector3(-1, 0, 1), Vector3(1, 0, -1), Vector3(-1, 0, -1),
        Vector3(0, 1, 1), Vector3(0, -1, 1), Vector3(0, 1, -1), Vector3(0, -1, -1)
    ]
    
    @staticmethod
    def _fade(t):
        """Fade function 6t^5 - 15t^4 + 10t^3."""
        return t * t * t * (t * (t * 6 - 15) + 10)

    @staticmethod
    def _grad(hash_val: int, x: float, y: float, z: float) -> float:
        """Calculates the dot product of a random gradient vector with the distance vector."""
        h = hash_val & 15
        # The classic Perlin gradient setup uses 8-16 vectors.
        # We use a direct dot product with a pre-defined gradient vector for simplicity.
        
        # Map h to 12 gradient vectors (simplified)
        g_vec = MathUtils._PERLIN_G[h % 12]
        
        # Distance vector
        d_vec = Vector3(x, y, z)
        
        return g_vec.dot(d_vec)

    @staticmethod
    def perlin_noise_3d(x: float, y: float, z: float) -> float:
        """
        Generates 3D Perlin Noise value for coordinates (x, y, z).
        Returns a value in the range of approximately -1.0 to 1.0.
        """
        # Unit cube coordinates
        X = int(math.floor(x)) & 255
        Y = int(math.floor(y)) & 255
        Z = int(math.floor(z)) & 255

        # Relative coordinates in the unit cube
        x -= math.floor(x)
        y -= math.floor(y)
        z -= math.floor(z)
        
        # Fade curves for interpolation
        u = MathUtils._fade(x)
        v = MathUtils._fade(y)
        w = MathUtils._fade(z)
        
        # Hash coordinates of the 8 cube corners
        A = MathUtils._PERLIN_P[X] + Y
        AA = MathUtils._PERLIN_P[A] + Z
        AB = MathUtils._PERLIN_P[A + 1] + Z
        B = MathUtils._PERLIN_P[X + 1] + Y
        BA = MathUtils._PERLIN_P[B] + Z
        BB = MathUtils._PERLIN_P[B + 1] + Z
        
        # Interpolate along the 12 edges
        # The result is the final interpolated value, scaled from -1 to 1
        
        # Interpolate Z
        L1 = MathUtils.lerp(
            MathUtils._grad(MathUtils._PERLIN_P[AA], x, y, z),
            MathUtils._grad(MathUtils._PERLIN_P[BA], x - 1, y, z),
            u
        )
        L2 = MathUtils.lerp(
            MathUtils._grad(MathUtils._PERLIN_P[AB], x, y - 1, z),
            MathUtils._grad(MathUtils._PERLIN_P[BB], x - 1, y - 1, z),
            u
        )
        L3 = MathUtils.lerp(
            MathUtils._grad(MathUtils._PERLIN_P[AA + 1], x, y, z - 1),
            MathUtils._grad(MathUtils._PERLIN_P[BA + 1], x - 1, y, z - 1),
            u
        )
        L4 = MathUtils.lerp(
            MathUtils._grad(MathUtils._PERLIN_P[AB + 1], x, y - 1, z - 1),
            MathUtils._grad(MathUtils._PERLIN_P[BB + 1], x - 1, y - 1, z - 1),
            u
        )

        # Interpolate Y
        M1 = MathUtils.lerp(L1, L2, v)
        M2 = MathUtils.lerp(L3, L4, v)

        # Interpolate X (Final result)
        return MathUtils.lerp(M1, M2, w)