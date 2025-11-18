# engine/utils/file_utils.py
import os
import sys
import json
import datetime
import shutil
from typing import List, Dict, Any

# Define paths relative to the project root (where main.py is)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
LOG_FILE = os.path.join(LOGS_DIR, 'engine_log.txt')

# Ensure logging directory exists for immediate use
os.makedirs(LOGS_DIR, exist_ok=True)

# Try to import Pygame for image loading and sound utilities (mock if not present)
try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


class FileUtils:
    """
    Utility class for all file system and logging operations in the engine.
    This provides a unified, reliable interface for IO.
    """

    @staticmethod
    def get_engine_root_path():
        """Returns the absolute path to the root of the project."""
        return PROJECT_ROOT

    @staticmethod
    def get_log_file_path():
        """Returns the absolute path to the main log file."""
        return LOG_FILE
        
    @staticmethod
    def get_project_file_path(relative_path: str, project_root: str = None) -> str:
        """
        Resolves a project-relative path to an absolute path.
        If project_root is None, uses the current project path from EngineState 
        (if available), otherwise assumes project root is the engine root.
        """
        if project_root is None:
            # Try to get project path from global state (mocked or assumed)
            try:
                from engine.core.engine_state import EngineState
                if hasattr(EngineState, 'instance') and EngineState.instance.current_project_path:
                    project_root = EngineState.instance.current_project_path
            except ImportError:
                pass # Continue with PROJECT_ROOT fallback

            if project_root is None:
                project_root = PROJECT_ROOT

        return os.path.normpath(os.path.join(project_root, relative_path))
        
    @staticmethod
    def create_dirs_if_not_exist(path: str):
        """Creates a directory and its parents if they don't exist."""
        os.makedirs(path, exist_ok=True)

    # --- Logging ---

    @staticmethod
    def _write_log(log_entry: str):
        """Internal helper to write the log entry to both console and file."""
        # Print to console
        print(log_entry)
        
        # Write to log file
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"[FATAL LOG ERROR] Could not write to log file: {e}", file=sys.stderr)

    @staticmethod
    def log_message(message: str, level: str = "INFO"):
        """Logs a standard message."""
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_entry = f"{timestamp} [{level.upper():<5}] {message}"
        FileUtils._write_log(log_entry)

    @staticmethod
    def log_error(message: str):
        """Logs an error message."""
        FileUtils.log_message(message, level="ERROR")
        
    @staticmethod
    def log_warning(message: str):
        """Logs a warning message."""
        FileUtils.log_message(message, level="WARN")
        
    @staticmethod
    def read_last_log_lines(file_path: str, num_lines: int) -> List[str]:
        """Reads the last N lines of a file efficiently."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read file content
                content = f.read()
                # Split into lines and return the last N
                return content.splitlines()[-num_lines:]
        except Exception:
            return []


    # --- File IO (Text/JSON) ---

    @staticmethod
    def read_text(file_path: str) -> str:
        """Reads the entire content of a text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            FileUtils.log_error(f"File not found: {file_path}")
            return ""
        except Exception as e:
            FileUtils.log_error(f"Error reading file {file_path}: {e}")
            return ""

    @staticmethod
    def write_text(file_path: str, content: str):
        """Writes content to a text file, creating parent directories if needed."""
        try:
            FileUtils.create_dirs_if_not_exist(os.path.dirname(file_path))
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            FileUtils.log_error(f"Error writing file {file_path}: {e}")

    @staticmethod
    def read_json(file_path: str) -> Dict[str, Any]:
        """Reads and parses a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            FileUtils.log_error(f"JSON file not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            FileUtils.log_error(f"JSON decode error in {file_path}: {e}")
            return {}
        except Exception as e:
            FileUtils.log_error(f"Error reading JSON file {file_path}: {e}")
            return {}

    @staticmethod
    def write_json(file_path: str, data: Dict[str, Any]):
        """Writes a dictionary to a JSON file with pretty printing (indent=4)."""
        try:
            FileUtils.create_dirs_if_not_exist(os.path.dirname(file_path))
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            FileUtils.log_error(f"Error writing JSON file {file_path}: {e}")

    # --- Pygame Asset Wrappers ---

    @staticmethod
    def load_image(file_path: str) -> pygame.Surface | None:
        """Loads a Pygame image (Surface) with alpha transparency support."""
        if not HAS_PYGAME: return None
        try:
            image = pygame.image.load(file_path)
            # Convert based on alpha
            if image.get_alpha():
                return image.convert_alpha()
            else:
                return image.convert()
        except pygame.error as e:
            FileUtils.log_error(f"Pygame failed to load image {file_path}: {e}")
            return None
        except Exception as e:
            FileUtils.log_error(f"Error loading image {file_path}: {e}")
            return None

    @staticmethod
    def load_sound(file_path: str) -> pygame.mixer.Sound | None:
        """Loads a Pygame sound asset."""
        if not HAS_PYGAME: return None
        if not pygame.mixer.get_init():
            FileUtils.log_warning("Pygame Mixer not initialized. Cannot load sound.")
            return None
            
        try:
            return pygame.mixer.Sound(file_path)
        except pygame.error as e:
            FileUtils.log_error(f"Pygame failed to load sound {file_path}: {e}")
            return None
        except Exception as e:
            FileUtils.log_error(f"Error loading sound {file_path}: {e}")
            return None