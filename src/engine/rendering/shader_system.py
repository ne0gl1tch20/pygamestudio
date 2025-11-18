# engine/rendering/shader_system.py
import os
import sys
import json
import pygame

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.rendering.material import Material
    from engine.rendering.renderer3d import HAS_PYGAME3D # Check for 3D support
except ImportError as e:
    print(f"[ShaderSystem Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[SS-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[SS-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def read_text(path): return f"// Mock Shader: {os.path.basename(path)}"
    class Material: 
        def __init__(self, name=""): self.name = name; self.shader_name = "default_lit"
    HAS_PYGAME3D = False


# --- Shader Program (Mock/Wrapper) ---

class ShaderProgram:
    """
    Represents a loaded and compiled shader program. 
    In a real Pygame3D/OpenGL context, this would hold the GL program ID.
    """
    
    def __init__(self, name: str, vertex_source: str, fragment_source: str):
        self.name = name
        self.vertex_source = vertex_source
        self.fragment_source = fragment_source
        self.is_compiled = False
        self.program_id = 0 # Mock GL ID

        if HAS_PYGAME3D:
            self._compile_gl_program()
        else:
            self.is_compiled = True # Mock success
            
    def _compile_gl_program(self):
        """Mocks the compilation of the OpenGL shader program."""
        try:
            # NOTE: Actual Pygame3D/OpenGL compilation code would go here.
            # E.g., self.program_id = p3d.compile_shader(self.vertex_source, self.fragment_source)
            self.is_compiled = True
            FileUtils.log_message(f"Shader '{self.name}' compiled successfully (Mock GL).")
        except Exception as e:
            self.is_compiled = False
            FileUtils.log_error(f"Failed to compile shader '{self.name}': {e}")

    def use(self):
        """Mocks activating this shader program for rendering."""
        if not self.is_compiled:
            return
        # E.g., p3d.glUseProgram(self.program_id)

    def set_uniform(self, name: str, value):
        """Mocks setting a uniform variable (e.g., MVP matrix, light color)."""
        if not self.is_compiled:
            return
        # E.g., p3d.glUniform(self.program_id, name, value)

    def is_valid(self):
        return self.is_compiled


# --- Shader System Manager ---

class ShaderSystem:
    """
    Manages loading, caching, and usage of shader programs (GLSL/Pygame3D shaders).
    Also provides utility for the Editor's Shader Graph/Material Editor.
    """

    def __init__(self, state: EngineState):
        self.state = state
        self.shader_cache = {} # {shader_name: ShaderProgram}
        
        # Paths to search for shaders (relative to 'assets/shaders')
        self.shader_directories = ["shaders"]
        self._load_default_shaders()

    def _load_default_shaders(self):
        """Loads essential default shaders (lit, unlit, wireframe)."""
        
        # 1. Generate/Mock source code for default shaders
        
        # Default Lit Shader Source (Vertex/Fragment)
        default_lit_vs = """
#version 330 core
// Minimal Vertex Shader Mock
layout (location = 0) in vec3 aPos;
uniform mat4 u_mvp;
void main() {
    gl_Position = u_mvp * vec4(aPos, 1.0);
}
"""
        default_lit_fs = """
#version 330 core
// Minimal Fragment Shader Mock
out vec4 FragColor;
uniform vec3 u_albedo;
void main() {
    FragColor = vec4(u_albedo, 1.0); // Simple color rendering
}
"""
        # Default Unlit Shader Source
        default_unlit_vs = default_lit_vs # Same vertex for simplicity
        default_unlit_fs = """
#version 330 core
out vec4 FragColor;
uniform vec3 u_color;
void main() {
    FragColor = vec4(u_color, 1.0);
}
"""
        # 2. Compile and cache the programs
        
        # Load Lit
        self._load_shader_program("default_lit", default_lit_vs, default_lit_fs)
        
        # Load Unlit
        self._load_shader_program("default_unlit", default_unlit_vs, default_unlit_fs)
        
        FileUtils.log_message(f"Default shaders loaded. 3D Supported: {HAS_PYGAME3D}")

    def _load_shader_program(self, name: str, vs_source: str, fs_source: str):
        """Internal helper to create, compile, and cache a ShaderProgram."""
        shader = ShaderProgram(name, vs_source, fs_source)
        if shader.is_compiled:
            self.shader_cache[name] = shader
            return True
        return False
        
    def load_shader_from_files(self, name: str, vs_filename: str, fs_filename: str):
        """Loads a shader program from separate vertex and fragment files."""
        asset_loader = self.state.asset_loader
        if not asset_loader:
            FileUtils.log_error("AssetLoader not initialized. Cannot load shader files.")
            return False

        # Get paths (assuming they are in the 'shaders' asset subdirectory)
        vs_path = asset_loader.get_asset_path('shader', vs_filename)
        fs_path = asset_loader.get_asset_path('shader', fs_filename)
        
        if not os.path.exists(vs_path) or not os.path.exists(fs_path):
            FileUtils.log_error(f"Shader files not found: {vs_filename} or {fs_filename}")
            return False
            
        try:
            # Read source code from files
            vs_source = FileUtils.read_text(vs_path)
            fs_source = FileUtils.read_text(fs_path)
            
            return self._load_shader_program(name, vs_source, fs_source)
            
        except Exception as e:
            FileUtils.log_error(f"Error reading shader files for '{name}': {e}")
            return False

    def get_shader(self, name: str) -> ShaderProgram | None:
        """Retrieves a cached shader program by name."""
        return self.shader_cache.get(name)

    def use_material_shader(self, material: Material, camera_data: dict, lights_data: list):
        """
        Selects the correct shader for a material, activates it, and sets 
        common uniforms (MVP, PBR parameters).
        """
        if not HAS_PYGAME3D:
            return # Cannot use shaders without 3D support

        shader = self.get_shader(material.shader_name)
        if not shader or not shader.is_valid():
            shader = self.get_shader("default_lit") # Fallback
            if not shader or not shader.is_valid():
                return # Give up

        shader.use()
        
        # --- Set Common Uniforms (Mock implementation) ---
        
        # 1. Transformation Matrices (Mock)
        # shader.set_uniform("u_model", model_matrix)
        # shader.set_uniform("u_view", camera_data.get('view_matrix'))
        # shader.set_uniform("u_projection", camera_data.get('projection_matrix'))
        # shader.set_uniform("u_mvp", model_view_projection_matrix)
        
        # 2. Material Uniforms
        if material.shader_name == "default_lit":
            shader.set_uniform("u_albedo", material.color.to_rgb())
            shader.set_uniform("u_metallic", material.metallic)
            shader.set_uniform("u_roughness", material.roughness)
            
            # Mock texture binding:
            # if material.albedo_texture:
            #     texture_id = self.state.asset_loader.get_asset('texture', material.albedo_texture)
            #     # p3d.glActiveTexture(0)
            #     # p3d.glBindTexture(GL_TEXTURE_2D, texture_id)
            #     # shader.set_uniform("u_albedo_sampler", 0) # Set texture unit 0
                
        elif material.shader_name == "default_unlit":
            shader.set_uniform("u_color", material.color.to_rgb())

        # 3. Lighting Uniforms (Simplified)
        # if lights_data:
        #     # shader.set_uniform("u_light_pos", lights_data[0].position)
        #     pass

    # --- Shader Graph Editor Tools (Mock) ---
    
    def generate_shader_node_schema(self, shader_name: str) -> dict:
        """
        Generates a mock node graph schema (inputs/outputs) for a given shader,
        used by editor_shader_graph.py.
        """
        schema = {
            "name": shader_name,
            "inputs": [
                {"name": "Albedo Color", "type": "color", "default": [1, 1, 1]},
                {"name": "Roughness", "type": "float", "default": 0.8},
                {"name": "Metallic", "type": "float", "default": 0.0},
                {"name": "Normal Map", "type": "texture2d", "default": None}
            ],
            "outputs": [
                {"name": "Final Color", "type": "color"}
            ]
        }
        return schema