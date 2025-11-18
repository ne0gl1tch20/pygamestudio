# engine/rendering/material.py
import json
import os
import sys

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.utils.color import Color
except ImportError as e:
    print(f"[Material Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[MAT-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[MAT-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def read_json(path): return {}
    class Color:
        def __init__(self, r=0, g=0, b=0, a=255): self.r, self.g, self.b, self.a = r, g, b, a
        def to_rgb(self): return (self.r, self.g, self.b)
        @classmethod
        def white(cls): return cls(255, 255, 255)
        @classmethod
        def gray(cls): return cls(128, 128, 128)

class Material:
    """
    Represents a material definition, controlling how a mesh or sprite 
    is rendered (color, texture references, shader to use, PBR properties).
    """
    
    def __init__(self, name="Default Material"):
        self.name = name
        
        # --- Common Properties (2D/3D) ---
        self.shader_name = "default_lit" # Name of the shader file/program to use
        self.transparent = False
        self.two_sided = False

        # --- Base Color / Albedo (2D Sprite Tint / 3D Base Color) ---
        self.color = Color.gray() # Solid color tint
        self.albedo_texture = None # Reference to texture asset name (e.g., "crate.png")
        self.albedo_tint = Color.white() # Tint applied over the texture

        # --- 3D / PBR Properties (only used by Renderer3D) ---
        self.metallic_texture = None
        self.roughness_texture = None
        self.normal_texture = None
        self.emissive_texture = None
        self.ao_texture = None
        
        self.metallic = 0.0 # Float 0.0 to 1.0
        self.roughness = 0.8 # Float 0.0 to 1.0
        self.specular = 0.5 # Float 0.0 to 1.0

    @classmethod
    def from_dict(cls, data: dict):
        """Creates a Material instance from a dictionary definition."""
        material = cls(data.get("name", "New Material"))
        
        material.shader_name = data.get("shader_name", material.shader_name)
        material.transparent = data.get("transparent", material.transparent)
        material.two_sided = data.get("two_sided", material.two_sided)
        
        # Color parsing (from list/tuple [r, g, b, a] or hex string)
        color_data = data.get("color")
        if color_data:
            if isinstance(color_data, str) and color_data.startswith('#'):
                try: material.color = Color.from_hex(color_data)
                except: pass
            elif isinstance(color_data, list) or isinstance(color_data, tuple):
                material.color = Color(*color_data)
                
        albedo_tint_data = data.get("albedo_tint")
        if albedo_tint_data:
            if isinstance(albedo_tint_data, str) and albedo_tint_data.startswith('#'):
                try: material.albedo_tint = Color.from_hex(albedo_tint_data)
                except: pass
            elif isinstance(albedo_tint_data, list) or isinstance(albedo_tint_data, tuple):
                material.albedo_tint = Color(*albedo_tint_data)

        material.albedo_texture = data.get("albedo_texture", material.albedo_texture)

        # 3D Properties
        material.metallic_texture = data.get("metallic_texture", material.metallic_texture)
        material.roughness_texture = data.get("roughness_texture", material.roughness_texture)
        material.normal_texture = data.get("normal_texture", material.normal_texture)
        material.emissive_texture = data.get("emissive_texture", material.emissive_texture)
        material.ao_texture = data.get("ao_texture", material.ao_texture)
        
        material.metallic = data.get("metallic", material.metallic)
        material.roughness = data.get("roughness", material.roughness)
        material.specular = data.get("specular", material.specular)

        return material

    def to_dict(self):
        """Converts the material instance to a serializable dictionary."""
        return {
            "name": self.name,
            "shader_name": self.shader_name,
            "transparent": self.transparent,
            "two_sided": self.two_sided,
            
            "color": self.color.to_rgba(), # Save as RGBA tuple
            "albedo_texture": self.albedo_texture,
            "albedo_tint": self.albedo_tint.to_rgba(),
            
            "metallic_texture": self.metallic_texture,
            "roughness_texture": self.roughness_texture,
            "normal_texture": self.normal_texture,
            "emissive_texture": self.emissive_texture,
            "ao_texture": self.ao_texture,
            
            "metallic": self.metallic,
            "roughness": self.roughness,
            "specular": self.specular
        }
        
class MaterialManager:
    """
    Manages loading and caching of Material assets, and provides access to 
    default materials. (Often implemented as part of AssetLoader, but separate here for clarity).
    """
    
    def __init__(self, state: EngineState):
        self.state = state
        self.cache = {} # {material_name: Material instance}
        self._create_default_materials()
        
    def _create_default_materials(self):
        """Creates and caches essential default materials."""
        # Default Lit Material
        lit_data = {
            "name": "Default_Lit", "shader_name": "default_lit", 
            "color": Color.gray().to_rgba(), "roughness": 0.8, "metallic": 0.0
        }
        self.cache["Default_Lit"] = Material.from_dict(lit_data)

        # Default Unlit Material (e.g., for UI, billboards)
        unlit_data = {
            "name": "Default_Unlit", "shader_name": "default_unlit", 
            "color": Color.white().to_rgba(), "roughness": 1.0
        }
        self.cache["Default_Unlit"] = Material.from_dict(unlit_data)

        FileUtils.log_message("Created default materials: Default_Lit, Default_Unlit.")

    def load_material(self, asset_name: str) -> Material | None:
        """Loads a material definition from the assets directory."""
        if asset_name in self.cache:
            return self.cache[asset_name]
            
        asset_loader = self.state.asset_loader
        if not asset_loader:
            return self.cache.get("Default_Lit") # Fallback to default if loader not ready

        # Get the path (assumes .json file in 'materials' subdir)
        file_path = asset_loader.get_asset_path('material', asset_name + '.json')
        
        if file_path and os.path.exists(file_path):
            try:
                data = FileUtils.read_json(file_path)
                if data:
                    material = Material.from_dict(data)
                    self.cache[asset_name] = material
                    FileUtils.log_message(f"Material '{asset_name}' loaded from file.")
                    return material
            except Exception as e:
                FileUtils.log_error(f"Failed to load material file {file_path}: {e}")

        # Fallback
        FileUtils.log_warning(f"Material '{asset_name}' not found. Using Default_Lit.")
        return self.cache.get("Default_Lit")

    def save_material(self, material: Material, asset_name: str = None):
        """Saves a material to a JSON file in the project assets directory."""
        save_name = asset_name if asset_name else material.name
        
        asset_loader = self.state.asset_loader
        if not asset_loader:
            FileUtils.log_error("AssetLoader not initialized. Cannot save material.")
            return False
            
        file_path = asset_loader.get_asset_path('material', save_name + '.json')
        
        try:
            data = material.to_dict()
            FileUtils.write_json(file_path, data)
            self.cache[save_name] = material # Update cache
            FileUtils.log_message(f"Material '{save_name}' saved to {file_path}")
            return True
        except Exception as e:
            FileUtils.log_error(f"Error saving material '{save_name}': {e}")
            return False