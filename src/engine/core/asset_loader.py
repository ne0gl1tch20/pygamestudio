# engine/core/asset_loader.py
import pygame
import os
import sys
import json

# Attempt to import core dependencies, use minimal mocks if they fail
try:
    from engine.core.engine_state import EngineState
    from engine.utils.file_utils import FileUtils
    from engine.utils.color import Color
except ImportError as e:
    print(f"[AssetLoader Import Error] {e}. Using Internal Mocks.")
    class EngineState: pass
    class FileUtils:
        @staticmethod
        def log_message(msg): print(f"[AL-INFO] {msg}")
        @staticmethod
        def log_error(msg): print(f"[AL-ERROR] {msg}", file=sys.stderr)
        @staticmethod
        def load_image(path, colorkey=None): 
            # Mock image loading: return a simple red surface
            s = pygame.Surface((32, 32))
            s.fill((255, 0, 0)) 
            return s
        @staticmethod
        def load_sound(path):
            # Mock sound loading: return a dummy object
            class MockSound:
                def play(self, loops=0): FileUtils.log_message(f"Mock Sound Played: {path}")
                def get_length(self): return 1.0
            return MockSound()
        @staticmethod
        def get_engine_asset_path(path): return path

    class Color:
        @staticmethod
        def red(): return Color(255, 0, 0)
        
# Initialize Pygame Mixer for sound loading check
try:
    pygame.mixer.init()
except pygame.error as e:
    print(f"Pygame Mixer Initialization failed: {e}. Audio assets will be mocked.")


class AssetLoader:
    """
    Manages loading, caching, and retrieval of all project and engine assets
    (images, sounds, models, shaders, etc.).
    """
    
    ASSET_DIRS = {
        'image': 'images', 'model': 'models', 'mesh': 'meshes', 
        'texture': 'textures', 'material': 'materials', 'sound': 'sounds', 
        'music': 'music', 'icon': 'icons', 'theme': 'themes', 
        'shader': 'shaders', 'tileset2d': 'tilesets2d', 'tileset3d': 'tilesets3d'
    }
    
    def __init__(self, state: EngineState):
        self.state = state
        self.cache = {}  # {asset_type: {asset_name: loaded_asset_object}}
        self._root_paths = {}
        self._setup_paths()
        self.load_engine_icons() # Load essential UI icons on startup

    def _setup_paths(self):
        """Determines the root directories for engine and project assets."""
        PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
        
        # Engine asset root (e.g., /assets)
        engine_asset_root = os.path.join(PROJECT_ROOT, 'assets')
        self._root_paths['engine'] = engine_asset_root
        
        # Project asset root (relative to project path)
        self._root_paths['project'] = "assets" # This is a relative path assumed inside the project folder
        
        # Initialize cache structure
        for asset_type in self.ASSET_DIRS.keys():
            self.cache[asset_type] = {}

        FileUtils.log_message(f"AssetLoader initialized. Engine Asset Root: {engine_asset_root}")

    def get_asset_path(self, asset_type: str, asset_name: str, is_engine_asset: bool = False):
        """Constructs the full file path for an asset."""
        
        subdir = self.ASSET_DIRS.get(asset_type)
        if not subdir:
            FileUtils.log_error(f"Unknown asset type: {asset_type}")
            return None

        if is_engine_asset:
            # Engine assets are always relative to the engine's asset root
            base_path = self._root_paths['engine']
        else:
            # Project assets are relative to the current project path
            if not self.state.current_project_path:
                FileUtils.log_warning(f"No project loaded. Cannot find project asset: {asset_name} ({asset_type})")
                return None
            
            # The asset path is PROJECT_ROOT/project_assets_dir/subdir/asset_name
            project_assets_dir = self._root_paths['project'] # e.g. "assets"
            base_path = os.path.join(self.state.current_project_path, project_assets_dir)

        full_path = os.path.join(base_path, subdir, asset_name)
        return full_path

    def load_asset(self, asset_type: str, asset_name: str, is_engine_asset: bool = False, force_reload: bool = False):
        """
        Loads an asset from disk, caches it, and returns the loaded object.
        Supported types: 'image', 'sound', 'mesh', 'shader'.
        """
        
        if not force_reload and asset_name in self.cache.get(asset_type, {}):
            return self.cache[asset_type][asset_name] # Return cached asset

        full_path = self.get_asset_path(asset_type, asset_name, is_engine_asset)
        if not full_path or not os.path.exists(full_path):
            FileUtils.log_error(f"Asset not found: {asset_name} ({asset_type}) at {full_path}")
            # Return a simple procedural fallback
            return self._create_placeholder(asset_type, asset_name)

        loaded_asset = None
        try:
            if asset_type in ['image', 'icon', 'texture']:
                # Pygame image loading
                loaded_asset = FileUtils.load_image(full_path)
                
            elif asset_type in ['sound', 'music']:
                # Pygame sound loading
                loaded_asset = FileUtils.load_sound(full_path)
                
            elif asset_type in ['model', 'mesh']:
                # 3D mesh loading (e.g., OBJ, using mesh_loader/pygame3d concepts)
                # We defer to a separate MeshLoader module, which is part of rendering/
                if self.state.renderer_3d:
                    # Mock call to a future MeshLoader
                    loaded_asset = self.state.renderer_3d.load_mesh(full_path) 
                else:
                    FileUtils.log_warning(f"3D functionality not initialized. Mocking mesh: {asset_name}")
                    loaded_asset = self._create_placeholder('mesh', asset_name)

            elif asset_type in ['shader', 'material', 'tileset2d', 'tileset3d']:
                # Load configuration/definition files (JSON, text)
                loaded_asset = FileUtils.read_text(full_path) 

            else:
                FileUtils.log_error(f"Asset type '{asset_type}' not supported by loader.")
                return None
                
            self.cache[asset_type][asset_name] = loaded_asset
            FileUtils.log_message(f"Loaded asset: {asset_name} ({asset_type})")
            return loaded_asset

        except Exception as e:
            FileUtils.log_error(f"Failed to load asset {asset_name} ({asset_type}): {e}")
            return self._create_placeholder(asset_type, asset_name)
            
    def _create_placeholder(self, asset_type: str, name: str):
        """Generates a simple, visible placeholder for a missing asset."""
        if asset_type in ['image', 'icon', 'texture']:
            size = 32 if asset_type == 'icon' else 64
            surface = pygame.Surface((size, size))
            surface.fill(Color.magenta().to_rgb()) # Classic missing texture color
            font = pygame.font.Font(None, 12)
            text = font.render("MISSING", True, Color.black().to_rgb())
            surface.blit(text, (2, size // 2 - 6))
            return surface
            
        elif asset_type in ['sound', 'music']:
            # Return a silent mock sound object
            class SilentMockSound:
                def play(self, loops=0): pass
                def get_length(self): return 0.5
            return SilentMockSound()
            
        elif asset_type in ['mesh', 'model']:
             # Return a minimal mock mesh data structure
             return {"vertices": [[-1, -1, 0], [1, -1, 0], [0, 1, 0]], "faces": [[0, 1, 2]]}
             
        return None

    def load_engine_icons(self):
        """
        Loads the essential editor icons/emojis as small surfaces.
        Since we cannot rely on actual files yet, we will generate them
        procedurally from emoji characters using pygame.font.
        """
        
        # NOTE: Pygame font rendering of Emojis is OS/Font dependent. 
        # We rely on the system having a font that supports them.
        
        emoji_map = {
            "save": "💾", "load": "📂", "settings": "⚙️", "help": "❓", "export": "🚀", 
            "play": "▶️", "stop": "⏹️", "multiplayer": "🌐", "workshop": "🛠️", 
            "plugins": "🔌", "theme": "🎨", "move": "↔️", "scale": "⤢", "rotate": "🔃", 
            "undo": "↩️", "redo": "↪️", "delete": "🗑️", "lock": "🔒", "unlock": "🔓",
            "search": "🔍", "folder": "📁", "plus": "➕", "minus": "➖"
        }
        
        try:
            # Use a system font (e.g., Arial) or fallback if available
            font = pygame.font.SysFont("segoeuisymbol", 24) 
            if font is None:
                font = pygame.font.Font(None, 24) # Fallback to default
                
            for name, emoji in emoji_map.items():
                # Render emoji as white text on a clear background
                text_surface = font.render(emoji, True, Color.white().to_rgb())
                
                # Create a small, square, transparent surface (32x32)
                icon_surface = pygame.Surface((32, 32), pygame.SRCALPHA)
                
                # Center the rendered text on the icon surface
                rect = text_surface.get_rect(center=(16, 16))
                icon_surface.blit(text_surface, rect)
                
                self.cache['icon'][name] = icon_surface
            
            FileUtils.log_message("Engine UI Icons (Emojis) generated.")
            
        except Exception as e:
            FileUtils.log_error(f"Failed to generate emoji icons: {e}")
            # Create simple colored squares as ultimate fallback
            self.cache['icon']['save'] = self._create_placeholder('icon', 'save').copy()
            self.cache['icon']['play'] = self._create_placeholder('icon', 'play').copy()
            # ... and so on for other critical icons
            
    def get_icon(self, name: str):
        """Retrieves a cached UI icon by name."""
        return self.cache.get('icon', {}).get(name, self._create_placeholder('icon', name))

    def get_asset(self, asset_type: str, asset_name: str):
        """Retrieves a cached asset or loads it if not present."""
        if asset_name not in self.cache.get(asset_type, {}):
            return self.load_asset(asset_type, asset_name)
        return self.cache[asset_type][asset_name]