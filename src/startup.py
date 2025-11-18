# startup.py
import os
import sys
import json
import datetime

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

ENGINE_DIRS = {
    'PROJECTS_DIR': os.path.join(PROJECT_ROOT, 'projects'),
    'ASSETS_ROOT': os.path.join(PROJECT_ROOT, 'assets'),
    'PLUGINS_DIR': os.path.join(PROJECT_ROOT, 'plugins'),  # runtime plugin loading
    'LOGS_DIR': os.path.join(PROJECT_ROOT, 'logs'),
    'WORKSHOP_SERVER': os.path.join(PROJECT_ROOT, 'workshop_server'),  # mock workshop
    'TEMP_DIR': os.path.join(PROJECT_ROOT, 'temp'),
    'USER_CONFIG_DIR': os.path.join(PROJECT_ROOT, 'config')  # settings.json
}

ENGINE_ASSET_SUBDIRS = [
    'images', 'models', 'meshes', 'textures', 'materials',
    'sounds', 'music', 'icons', 'themes', 'shaders',
    'tilesets2d', 'tilesets3d'
]

CONFIG_FILE = os.path.join(ENGINE_DIRS['USER_CONFIG_DIR'], 'settings.json')
LOG_FILE = os.path.join(ENGINE_DIRS['LOGS_DIR'], 'engine_log.txt')


# --- Core Functions ---
def _setup_logging():
    """Setup engine logging to console + file."""
    os.makedirs(ENGINE_DIRS['LOGS_DIR'], exist_ok=True)

    def log(message, level="INFO"):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_entry = f"{timestamp} [{level.upper():<5}] {message}"
        print(log_entry)
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Failed writing log: {e}")
    return log


def _create_directories(log_func):
    """Create all engine directories and asset subfolders."""
    log_func("Setting up engine directories...")
    for name, path in ENGINE_DIRS.items():
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            log_func(f"ERROR creating {name}: {e}", level="ERROR")

    for subdir in ENGINE_ASSET_SUBDIRS:
        try:
            os.makedirs(os.path.join(ENGINE_DIRS['ASSETS_ROOT'], subdir), exist_ok=True)
        except Exception as e:
            log_func(f"ERROR creating asset subdir {subdir}: {e}", level="ERROR")

    _create_example_project(log_func)


def _get_default_config():
    """Default settings.json structure."""
    return {
        "engine_version": "V4.0.0",
        "editor_settings": {
            "screen_width": 1280,
            "screen_height": 720,
            "theme": "dark",
            "autosave_interval_minutes": 5,
            "default_project_path": ENGINE_DIRS['PROJECTS_DIR'],
            "last_opened_project": None
        },
        "project_settings": {
            "game_title": "New Pygame Godmode Project",
            "resolution_x": 800,
            "resolution_y": 600,
            "target_fps": 60,
            "network_port": 5555,
            "max_players": 4,
            "is_3d_mode": False
        },
        "network_settings": {
            "default_port": 5555,
            "default_host": "127.0.0.1"
        }
    }


def _load_or_create_config(log_func):
    """Load settings.json or create with defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                log_func(f"Loaded configuration from {CONFIG_FILE}")
                return config
        except json.JSONDecodeError as e:
            log_func(f"Corrupted settings.json ({e}). Using defaults.", level="ERROR")
            return _get_default_config()
    else:
        default_config = _get_default_config()
        os.makedirs(ENGINE_DIRS['USER_CONFIG_DIR'], exist_ok=True)
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            log_func(f"Created default config: {CONFIG_FILE}")
        except Exception as e:
            log_func(f"Failed to write config: {e}", level="ERROR")
        return default_config


def _create_example_project(log_func):
    """Create a simple example project if it doesn't exist."""
    example_path = os.path.join(ENGINE_DIRS['PROJECTS_DIR'], 'example_project')
    if os.path.exists(example_path):
        return

    log_func("Creating example_project structure...")
    os.makedirs(os.path.join(example_path, 'assets'), exist_ok=True)
    os.makedirs(os.path.join(example_path, 'scripts'), exist_ok=True)

    # project.json
    project_json = {
        "name": "Example Godmode Project",
        "main_scene": "main_scene.json",
        "is_3d": False,
        "assets_path": "assets/",
        "scripts_path": "scripts/",
        "startup_script": "main.py"
    }
    with open(os.path.join(example_path, 'project.json'), 'w') as f:
        json.dump(project_json, f, indent=4)

    # main.py
    main_py = """\
# Example project main.py
def start_game(game_manager):
    print("--- Example Project Started ---")
    return {"name": "Main Scene", "objects": [], "is_3d": False}

def update_game(game_manager, dt):
    pass
"""
    with open(os.path.join(example_path, 'main.py'), 'w') as f:
        f.write(main_py)

    # player_movement.py
    player_script = """\
# Example player movement script
def init(self):
    self.speed = 150
    self.is_jumping = False

def update(self, dt):
    input_manager = getattr(self.state, 'input_manager', None)
    if input_manager:
        velocity = getattr(self.state.utils, 'Vector2', lambda x, y: [0,0])(0,0)
        # WASD controls (mock)
        if input_manager.get_key('w'): velocity[1] -= 1
        if input_manager.get_key('s'): velocity[1] += 1
        if input_manager.get_key('a'): velocity[0] -= 1
        if input_manager.get_key('d'): velocity[0] += 1
"""
    with open(os.path.join(example_path, 'scripts', 'player_movement.py'), 'w') as f:
        f.write(player_script)


def init_engine_environment():
    """Initialize engine directories, logging, and default configs."""
    log = _setup_logging()
    log("--- Pygame Studio Engine V4 Startup ---")
    log(f"Project Root: {PROJECT_ROOT}")
    _create_directories(log)
    config = _load_or_create_config(log)
    log("Startup complete.")
    return config


if __name__ == "__main__":
    # Test startup
    init_engine_environment()
