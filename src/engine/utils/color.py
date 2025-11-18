# engine/utils/color.py

class Color:
    """
    Represents an RGB color with optional Alpha (RGBA). 
    Values are stored as integers 0-255.
    """
    
    def __init__(self, r=0, g=0, b=0, a=255):
        # Ensure values are ints clamped to 0-255
        self.r = self._clamp(r)
        self.g = self._clamp(g)
        self.b = self._clamp(b)
        self.a = self._clamp(a)

    def _clamp(self, val):
        """Helper to clamp color component values."""
        try:
            val = int(val)
        except:
            val = 0
        return max(0, min(255, val))

    def __str__(self):
        return f"Color({self.r}, {self.g}, {self.b}, {self.a})"

    def __repr__(self):
        return self.__str__()
        
    def to_rgb(self):
        """Returns the color as a (R, G, B) tuple."""
        return (self.r, self.g, self.b)

    def to_rgba(self):
        """Returns the color as a (R, G, B, A) tuple."""
        return (self.r, self.g, self.b, self.a)
        
    def to_hex(self):
        """Returns the color as a hex string #RRGGBB or #RRGGBBAA."""
        if self.a == 255:
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
        else:
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}{self.a:02x}"
            
    def lerp(self, other, t):
        """Linearly interpolate to another color."""
        # Use MathUtils.clamp if available, otherwise manual clamp
        t = max(0.0, min(1.0, t))
        
        return Color(
            int(self.r + (other.r - self.r) * t),
            int(self.g + (other.g - self.g) * t),
            int(self.b + (other.b - self.b) * t),
            int(self.a + (other.a - self.a) * t)
        )
        
    @classmethod
    def from_hex(cls, hex_str: str):
        """Creates a Color from a hex string (#RRGGBB or #RRGGBBAA)."""
        hex_str = hex_str.lstrip('#')
        if len(hex_str) == 6:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return cls(r, g, b)
        elif len(hex_str) == 8:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            a = int(hex_str[6:8], 16)
            return cls(r, g, b, a)
        raise ValueError(f"Invalid hex color string format: {hex_str}")

    # --- Predefined Colors (Standard) ---
    @classmethod
    def black(cls): return cls(0, 0, 0)
    @classmethod
    def white(cls): return cls(255, 255, 255)
    @classmethod
    def red(cls): return cls(255, 0, 0)
    @classmethod
    def green(cls): return cls(0, 255, 0)
    @classmethod
    def blue(cls): return cls(0, 0, 255)
    @classmethod
    def yellow(cls): return cls(255, 255, 0)
    @classmethod
    def cyan(cls): return cls(0, 255, 255)
    @classmethod
    def magenta(cls): return cls(255, 0, 255)
    @classmethod
    def gray(cls): return cls(128, 128, 128)
    @classmethod
    def clear(cls): return cls(0, 0, 0, 0)
    @classmethod
    def orange(cls): return cls(255, 165, 0)
    
# NOTE: Lerp relies on MathUtils.clamp. We must provide a mock if it's not imported.
try:
    from engine.utils.math_utils import MathUtils
except ImportError:
    # Minimal mock for MathUtils used in lerp
    class MockMathUtils:
        @staticmethod
        def clamp(val, min_v, max_v): return max(min_v, min(max_v, val))
    MathUtils = MockMathUtils